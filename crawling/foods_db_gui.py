# Update /mnt/data/foods_db_gui.py to:
# - Reintroduce pageNo (optional) field in GUI and request
# - Set numOfRows default to 100
# - Reflow the Options layout so the "추가 키워드" sits on its own row
# - Widen the default window to avoid clipping
from pathlib import Path

#updated = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FoodNtrCpntDbInfo02 API GUI 수집기 (serviceKey만 필수)
- Endpoint: https://apis.data.go.kr/1471000/FoodNtrCpntDbInfo02/getFoodNtrCpntDbInq02
- 필수: serviceKey (settings.py 기본값 자동 삽입)
- 선택: FOOD_NM_KR, MAKER_NM, FOOD_CAT1_NM, pageNo, numOfRows
- 요청에서 제외: RESEARCH_YMD, UPDATE_DATE, ITEM_REPORT_NO (단, 응답의 UPDATE_DATE는 중복제거 판단에 사용)
- DB_CLASS_NM = '상용제품' 고정
- 응답 type은 json 고정
- 미리보기/CSV 기본 컬럼: NUM, MAKER_NM, FOOD_NM_KR, FOOD_CAT1_NM, SERVING_SIZE, NUTRI_AMOUNT_SERVING, Z10500
- CSV 저장: 기존 파일이 있으면 'NUM' 기준으로 중복 스킵, 새로운 NUM만 이어쓰기
- 고급 중복 제거: 같은 이름(공백 제거) & AMT_NUM* 구성이 완전히 동일하면 UPDATE_DATE 최신만 남김(동률이면 최초 등장)
"""

import os
import sys
import csv
import time
import threading
import re
from typing import Dict, Any, List, Iterable, Tuple

import requests
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# 프로젝트 루트에서 settings.serviceKey 로드
ROOT_DIR = os.path.dirname(os.path.dirname(__file__))  # zero_side_effect/
sys.path.append(ROOT_DIR)
try:
    import settings  # settings.serviceKey = "..."
except Exception:
    settings = None

ENDPOINT = "http://apis.data.go.kr/1471000/FoodNtrCpntDbInfo02/getFoodNtrCpntDbInq02"
REQUEST_TIMEOUT = 15
RETRY = 3
RETRY_SLEEP = 1.0

ZERO_PATTERNS = [
    "제로", "zero", "sugar free", "sugar-free", "no sugar",
    "무설탕", "무가당", "무당", "제로슈거", "zero sugar", "0 sugar", "0g sugar"
]


# ------------------- 유틸 -------------------

def normalize_items(items):
    """items가 dict/list 어느 형태든 item 리스트로 정규화."""
    if not items:
        return []
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    if isinstance(items, dict):
        it = items.get("item")
        if isinstance(it, list):
            return [x for x in it if isinstance(x, dict)]
        if isinstance(it, dict):
            return [it]
        return [items]  # 이미 단일 레코드 dict 형태
    return []


def extract_items_from_response(data) -> List[Dict[str, Any]]:
    """API 응답이 dict/list 어떤 형태든 items 리스트로 정규화"""
    if isinstance(data, dict):
        body = data.get("body")
        if isinstance(body, dict):
            return normalize_items(body.get("items"))
        if isinstance(data.get("items"), (list, dict)):
            return normalize_items(data.get("items"))
        if "item" in data:
            return normalize_items({"item": data.get("item")})
        return normalize_items(data)
    elif isinstance(data, list):
        return normalize_items(data)
    return []


def matches_zero(name: str) -> bool:
    if not name:
        return False
    n = name.lower()
    return any(p in n for p in ZERO_PATTERNS)


def build_query(p: Dict[str, str], num_rows: int | None, page_no: int | None) -> Dict[str, Any]:
    """serviceKey만 필수. DB_CLASS_NM='상용제품' 고정. numOfRows 기본 100."""
    q = {"serviceKey": p["serviceKey"], "type": "json", "DB_CLASS_NM": "상용제품"}
    # numOfRows: 기본 100
    q["numOfRows"] = num_rows if num_rows is not None else 100
    if page_no is not None:
        q["pageNo"] = page_no
    if p.get("FOOD_NM_KR"):
        q["FOOD_NM_KR"] = p["FOOD_NM_KR"]
    if p.get("MAKER_NM"):
        q["MAKER_NM"] = p["MAKER_NM"]
    if p.get("FOOD_CAT1_NM"):
        q["FOOD_CAT1_NM"] = p["FOOD_CAT1_NM"]
    return q


def request_json(params: Dict[str, Any]) -> Dict[str, Any]:
    last = None
    for _ in range(RETRY):
        try:
            r = requests.get(ENDPOINT, params=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            last = e
            time.sleep(RETRY_SLEEP)
    raise last


def filter_record(rec: Dict[str, Any], only_zero: bool, extra_keyword: str) -> Tuple[bool, bool]:
    """추가 키워드(제품명/업체명 포함) + only-zero 적용"""
    name = (rec.get("FOOD_NM_KR") or "").strip()
    maker = (rec.get("MAKER_NM") or "").strip()
    ok = True
    if extra_keyword:
        k = extra_keyword.lower()
        ok = (k in name.lower()) or (k in maker.lower())
    is_zero = matches_zero(name)
    if only_zero and not is_zero:
        return False, is_zero
    return ok, is_zero


def dedupe(records: Iterable[Dict[str, Any]], keys: List[str]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for r in records:
        key = tuple((r.get(k) or "").strip() for k in keys)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


# -------- 이름+AMT_NUM 완전중복 제거 --------

def _norm_name(name: str) -> str:
    # 공백 제거 + 소문자
    return re.sub(r"\s+", "", (name or "")).lower()


def _amt_keys_all(records: List[Dict[str, Any]]) -> List[str]:
    keys = set()
    for r in records:
        for k in r.keys():
            if k.startswith("AMT_NUM"):
                keys.add(k)
    def amt_key(k: str):
        m = re.search(r"AMT_NUM(\d+)", k)
        return int(m.group(1)) if m else 0
    return sorted(keys, key=amt_key)


def _date_int(s: str) -> int:
    # "2025-01-23" -> 20250123, "20250123"도 처리, 그 외는 0
    if not s:
        return 0
    digits = re.sub(r"\D", "", s)
    if len(digits) >= 8:
        return int(digits[:8])
    return 0


def dedupe_by_name_and_amt(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    1) 이름의 공백을 제거한 키로 그룹
    2) 그룹 내에서 AMT_NUM* 값 벡터가 완전히 동일한 것들끼리 묶음
    3) 각 묶음에서 UPDATE_DATE 최신 우선, 같으면 최초 등장 순서 우선으로 1개만 남김
    """
    if not records:
        return []
    amt_keys = _amt_keys_all(records)

    # 이름으로 그룹핑
    groups: Dict[str, List[Tuple[int, Dict[str, Any]]]] = {}
    for idx, r in enumerate(records):
        nk = _norm_name(r.get("FOOD_NM_KR"))
        groups.setdefault(nk, []).append((idx, r))

    out: List[Dict[str, Any]] = []
    for _, items in groups.items():
        if len(items) == 1:
            out.append(items[0][1])
            continue

        # AMT 시그니처로 하위 그룹
        clusters: Dict[Tuple[str, ...], List[Tuple[int, Dict[str, Any]]]] = {}
        for pos, r in items:
            sig = tuple((r.get(k, "") or "").strip() for k in amt_keys)
            clusters.setdefault(sig, []).append((pos, r))

        for bucket in clusters.values():
            if len(bucket) == 1:
                out.append(bucket[0][1])
                continue
            # UPDATE_DATE 최신, 같으면 최초 등장(pos 작을수록 우선)
            best_pos = None
            best_date = -1
            best_rec = None
            for pos, r in bucket:
                di = _date_int((r.get("UPDATE_DATE") or "").strip())
                if best_rec is None or di > best_date or (di == best_date and pos < best_pos):
                    best_rec = r
                    best_date = di
                    best_pos = pos
            out.append(best_rec)

    return out


def to_csv(records: List[Dict[str, Any]], out_path: str, include_amt_nums: bool) -> Dict[str, Any]:
    """
    기존 CSV가 있으면:
      - 헤더(열 순서) 유지
      - 'NUM' 중복은 스킵, 새로운 NUM만 append
    없으면:
      - base_cols(+옵션 AMT_NUM*) 헤더 생성 후 기록(실행 내 중복 NUM 제거)
    """
    base_cols = ["NUM","MAKER_NM","FOOD_NM_KR","FOOD_CAT1_NM","SERVING_SIZE","NUTRI_AMOUNT_SERVING","Z10500"]
    # AMT_NUM* 수집 및 정렬
    amt_cols_set = set()
    if include_amt_nums:
        for r in records:
            for k in r.keys():
                if k.startswith("AMT_NUM"):
                    amt_cols_set.add(k)
    def amt_key(k: str):
        m = re.search(r"AMT_NUM(\d+)", k)
        return int(m.group(1)) if m else 0
    amt_cols = sorted(amt_cols_set, key=amt_key)

    if os.path.exists(out_path):
        # 이어쓰기
        with open(out_path, "r", newline="", encoding="utf-8-sig") as rf:
            reader = csv.DictReader(rf)
            cols = reader.fieldnames or []
            if "NUM" not in cols:
                raise RuntimeError("기존 CSV에 'NUM' 컬럼이 없어 이어쓰기를 할 수 없습니다.")
            existing_nums = set()
            for row in reader:
                existing_nums.add(str(row.get("NUM","")).strip())

        appended = skipped = 0
        with open(out_path, "a", newline="", encoding="utf-8-sig") as af:
            writer = csv.DictWriter(af, fieldnames=cols, extrasaction="ignore")
            for r in records:
                num_val = str(r.get("NUM","")).strip()
                if not num_val or num_val in existing_nums:
                    skipped += 1; continue
                writer.writerow({c: r.get(c,"") for c in cols})
                existing_nums.add(num_val); appended += 1
        return {"mode":"append","appended":appended,"skipped":skipped,"columns_used":cols,"total_existing":len(existing_nums)}
    else:
        # 신규 작성
        cols = base_cols + (amt_cols if include_amt_nums else [])
        appended = skipped = 0
        seen = set()
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w", newline="", encoding="utf-8-sig") as wf:
            writer = csv.DictWriter(wf, fieldnames=cols, extrasaction="ignore")
            writer.writeheader()
            for r in records:
                num_val = str(r.get("NUM","")).strip()
                if not num_val or num_val in seen:
                    skipped += 1; continue
                writer.writerow({c: r.get(c,"") for c in cols})
                seen.add(num_val); appended += 1
        return {"mode":"write","appended":appended,"skipped":skipped,"columns_used":cols,"total_existing":0}


# ------------------- 수집 스레드 -------------------

class CollectorThread(threading.Thread):
    def __init__(self, ui_ref):
        super().__init__(daemon=True)
        self.ui = ui_ref

    def run(self):
        try:
            self.ui.on_collect_start()

            # UI → 요청변수 dict
            params_ui = self.ui.read_request_params()

            # serviceKey 보장
            if not params_ui.get("serviceKey"):
                if settings and getattr(settings, "serviceKey", None):
                    params_ui["serviceKey"] = settings.serviceKey.strip()
                else:
                    raise RuntimeError("serviceKey가 비어 있습니다. settings.py 또는 입력칸에 키를 넣어주세요.")

            only_zero   = self.ui.var_only_zero.get()
            extra_kw    = self.ui.ent_extra_keyword.get().strip()
            no_dedupe   = self.ui.var_no_dedupe.get()
            dedupe_keys = [k.strip() for k in self.ui.ent_dedupe_key.get().split(",") if k.strip()]
            include_amt = self.ui.var_all_columns.get()  # CSV에 AMT_NUM 포함 여부
            num_rows_str = self.ui.var_num_rows.get().strip()
            num_rows = int(num_rows_str) if num_rows_str else None
            page_no_str = self.ui.var_page_no.get().strip()
            page_no = int(page_no_str) if page_no_str else None

            # 단일 호출
            q = build_query(params_ui, num_rows=num_rows, page_no=page_no)
            data = request_json(q)
            items = extract_items_from_response(data)

            # 필터링
            collected: List[Dict[str, Any]] = []
            for rec in items:
                ok, is_zero = filter_record(rec, only_zero, extra_kw)
                if not ok:
                    continue
                collected.append(rec)

            # 고급 중복 제거: 이름(공백제거) + AMT_NUM 완전 동일 → UPDATE_DATE 최신만 유지
            before = len(collected)
            records = dedupe_by_name_and_amt(collected)
            after = len(records)
            self.ui.log(f"동일이름+AMT_NUM 완전중복 제거: {before} → {after}")

            # 화면용 중복 제거(선택): 추가 dedupe의 키는 사용자가 지정
            if not no_dedupe and dedupe_keys:
                records = dedupe(records, dedupe_keys)

            self.ui.on_collect_done(records, include_amt)
            self.ui.set_status(f"완료: {len(records)}건", "green")
            self.ui.update_progress(100 if records else 0)

        except Exception as e:
            self.ui.set_status(f"오류: {e}", "red")
            self.ui.enable_controls(True)


# ------------------- GUI -------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FoodNtrCpntDbInfo02 수집기 (상용제품 고정)")
        self.geometry("1200x760")  # 창 넓힘: 가로 여유를 늘려 추가 키워드 잘 보이게
        self.resizable(True, True)

        self.records: List[Dict[str, Any]] = []
        self.worker: CollectorThread | None = None

        # 필수값
        frm_req = ttk.LabelFrame(self, text="필수 입력")
        frm_req.pack(fill="x", padx=10, pady=8)
        self.ent_serviceKey = self._add_labeled_entry(frm_req, 0, 0, "serviceKey")
        if settings and getattr(settings, "serviceKey", None):
            self.ent_serviceKey.insert(0, settings.serviceKey.strip())

        # 선택 요청변수
        frm_sel = ttk.LabelFrame(self, text="선택 입력 (요청변수)")
        frm_sel.pack(fill="x", padx=10, pady=6)
        self.ent_FOOD_NM_KR   = self._add_labeled_entry(frm_sel, 0, 0, "FOOD_NM_KR (식품명)")
        self.ent_MAKER_NM     = self._add_labeled_entry(frm_sel, 0, 2, "MAKER_NM (업체명)")
        self.ent_FOOD_CAT1_NM = self._add_labeled_entry(frm_sel, 1, 0, "FOOD_CAT1_NM (대분류, 예: 음료류)")
        ttk.Label(frm_sel, text="DB_CLASS_NM=상용제품 (고정)").grid(row=1, column=2, sticky="w", padx=6, pady=4)

        # 옵션
        opt = ttk.LabelFrame(self, text="옵션")
        opt.pack(fill="x", padx=10, pady=6)
        for i in range(6):
            opt.columnconfigure(i, weight=1)

        # Row 0: pageNo + numOfRows(기본 100)
        ttk.Label(opt, text="pageNo(선택)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
        self.var_page_no = tk.StringVar(value="")
        ttk.Entry(opt, textvariable=self.var_page_no, width=10).grid(row=0, column=1, sticky="w", padx=4, pady=4)

        ttk.Label(opt, text="numOfRows(기본 100)").grid(row=0, column=2, sticky="e", padx=4, pady=4)
        self.var_num_rows = tk.StringVar(value="100")
        ttk.Entry(opt, textvariable=self.var_num_rows, width=10).grid(row=0, column=3, sticky="w", padx=4, pady=4)

        self.var_only_zero = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text="제품명에 제로/무설탕/zero 포함만 (only-zero)", variable=self.var_only_zero)\
            .grid(row=0, column=4, sticky="w", padx=6, pady=4)

        # Row 1: 추가 키워드 -> 한 줄 전용
        ttk.Label(opt, text="추가 키워드(제품명/업체명 포함 검색):").grid(row=1, column=0, sticky="e", padx=4, pady=4)
        self.ent_extra_keyword = ttk.Entry(opt, width=60)
        self.ent_extra_keyword.grid(row=1, column=1, columnspan=4, sticky="we", padx=4, pady=4)

        # Row 2: 나머지 옵션들
        self.var_no_dedupe = tk.BooleanVar(value=False)
        ttk.Checkbutton(opt, text="중복 제거 끄기(화면 미리보기)", variable=self.var_no_dedupe).grid(row=2, column=0, sticky="w", padx=6, pady=4)

        ttk.Label(opt, text="Dedupe Key (콤마구분, 화면 미리보기용):").grid(row=2, column=1, sticky="e", padx=4, pady=4)
        self.ent_dedupe_key = ttk.Entry(opt, width=32)
        self.ent_dedupe_key.insert(0, "FOOD_CD,FOOD_NM_KR")
        self.ent_dedupe_key.grid(row=2, column=2, sticky="w", padx=4, pady=4)

        self.var_all_columns = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, text="CSV에 AMT_NUM 포함", variable=self.var_all_columns)\
            .grid(row=2, column=3, sticky="w", padx=6, pady=4)

        # 실행/저장
        ctrl = ttk.Frame(self); ctrl.pack(fill="x", padx=10, pady=6)
        self.btn_fetch = ttk.Button(ctrl, text="가져오기", command=self.start_collect); self.btn_fetch.pack(side="left", padx=4)
        ttk.Button(ctrl, text="CSV로 저장", command=self.save_csv).pack(side="left", padx=4)

        # 상태/진행률
        self.pb = ttk.Progressbar(ctrl, mode="determinate", length=300); self.pb.pack(side="left", padx=10)
        self.lbl_status = ttk.Label(ctrl, text="대기"); self.lbl_status.pack(side="left", padx=6)

        # 로그
        self.txt_log = tk.Text(self, height=4); self.txt_log.pack(fill="x", padx=10, pady=4)
        self.log("type=json / DB_CLASS_NM='상용제품' 고정 / numOfRows 기본 100 / pageNo 옵션")

        # 미리보기 테이블
        table_frame = ttk.LabelFrame(self, text="미리보기 (상위 200행, 핵심 컬럼)")
        table_frame.pack(fill="both", expand=True, padx=10, pady=6)
        cols = ["NUM","MAKER_NM","FOOD_NM_KR","FOOD_CAT1_NM","SERVING_SIZE","NUTRI_AMOUNT_SERVING","Z10500"]
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=18)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160 if c in ("FOOD_NM_KR","MAKER_NM") else 140, anchor="w")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=sb.set)
        sb.pack(side="right", fill="y")

    # ---- UI helper ----
    def _add_labeled_entry(self, parent, r, c, label):
        ttk.Label(parent, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=4)
        e = ttk.Entry(parent, width=28)
        e.grid(row=r, column=c+1, sticky="w", padx=6, pady=4)
        return e

    def read_request_params(self) -> Dict[str, str]:
        return {
            "serviceKey": self.ent_serviceKey.get().strip(),
            "FOOD_NM_KR": self.ent_FOOD_NM_KR.get().strip(),
            "MAKER_NM": self.ent_MAKER_NM.get().strip(),
            "FOOD_CAT1_NM": self.ent_FOOD_CAT1_NM.get().strip(),
        }

    def on_collect_start(self):
        self.records = []
        self.update_table([])
        self.enable_controls(False)
        self.set_status("수집 시작", "blue")
        self.update_progress(0)

    def on_collect_done(self, records: List[Dict[str, Any]], include_amt_cols: bool):
        self.records = records
        self.update_table(records[:200])
        self.enable_controls(True)

    def update_table(self, rows: List[Dict[str, Any]]):
        for i in self.tree.get_children():
            self.tree.delete(i)
        cols = ["NUM","MAKER_NM","FOOD_NM_KR","FOOD_CAT1_NM","SERVING_SIZE","NUTRI_AMOUNT_SERVING","Z10500"]
        for r in rows:
            self.tree.insert("", "end", values=[r.get(k, "") for k in cols])

    def enable_controls(self, enabled: bool):
        self.btn_fetch.config(state=("normal" if enabled else "disabled"))

    def set_status(self, msg: str, color="black"):
        self.lbl_status.config(text=msg, foreground=color)
        self.log(msg)

    def log(self, msg: str):
        self.txt_log.insert("end", f"{msg}\n")
        self.txt_log.see("end")

    def update_progress(self, pct: int):
        self.pb["value"] = max(0, min(100, pct))
        self.pb.update_idletasks()

    # ---- 액션 ----
    def start_collect(self):
        # Validate ints if provided
        try:
            nr = self.var_num_rows.get().strip()
            if nr:
                int(nr)
            pn = self.var_page_no.get().strip()
            if pn:
                int(pn)
        except ValueError:
            messagebox.showerror("오류", "pageNo/numOfRows는 정수 또는 비워두세요.")
            return
        self.worker = CollectorThread(self)
        self.worker.start()

    def save_csv(self):
        if not self.records:
            messagebox.showinfo("알림","저장할 데이터가 없습니다. 먼저 [가져오기]를 실행하세요.")
            return
        path = filedialog.asksaveasfilename(
            title="CSV로 저장",
            defaultextension=".csv",
            filetypes=[("CSV 파일","*.csv"),("모든 파일","*.*")]
        )
        if not path:
            return
        try:
            res = to_csv(self.records, path, include_amt_nums=self.var_all_columns.get())
            mode = "이어쓰기" if res.get("mode") == "append" else "신규 작성"
            appended = res.get("appended", 0)
            skipped = res.get("skipped", 0)
            msg = f"{mode} 완료\n추가: {appended}건, 스킵: {skipped}건\n파일: {os.path.basename(path)}"
            messagebox.showinfo("완료", msg)
            self.log(msg)
        except Exception as e:
            messagebox.showerror("실패", str(e))


# ------------------- main -------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
# '''
# Path("/mnt/data/foods_db_gui.py").write_text(updated, encoding="utf-8")
# print("Updated GUI with pageNo field, numOfRows default 100, wider layout.")
