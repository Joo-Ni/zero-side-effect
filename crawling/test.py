# -*- coding: utf-8 -*-
"""
네이버 이미지 크롤링 (입력 CSV는 읽기 전용, 진행 기록은 별도 로그 CSV에 upsert)
- 입력 CSV 필수 컬럼: FOOD_NM_KR(제품명), FOOD_CAT1_NM(카테고리)
- 로그 CSV 컬럼: FOOD_NM_KR, FOOD_CAT1_NM, image_count, timestamp, directory
- 인코딩 기본: utf-8-sig (cp949면 --encoding cp949 로 지정)
- 콘솔은 ASCII만 출력(한글/이모지로 인한 UnicodeEncodeError 차단)
"""

import os
import sys
import locale
import time
import argparse
import unicodedata
import mimetypes
from datetime import datetime
from io import BytesIO

import pandas as pd
import requests
from PIL import Image, ImageFile

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

# ─────────────────────────────────────────────
# 안전 로그(ASCII만): print()로 인한 'latin-1' 에러 차단
# ─────────────────────────────────────────────
def log(*args, sep=" ", end="\n"):
    msg = sep.join(str(a) for a in args)
    # ASCII만 내보내기: 비ASCII는 ? 로 대체
    safe = msg.encode("ascii", errors="replace").decode("ascii", errors="replace")
    try:
        sys.stdout.write(safe + end)
    except Exception:
        # 최후 폴백
        try:
            sys.stdout.buffer.write((safe + end).encode("ascii", "replace"))
        except Exception:
            pass

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ─────────────────────────────────────────────
# 기본 설정
# ─────────────────────────────────────────────
DEFAULT_INPUT_CSV = "무설탕.csv"
DEFAULT_LOG_CSV = "crawl_log.csv"
DEFAULT_BASE_SAVE_DIR = "dataset_naver"
LOG_COLUMNS = ["FOOD_NM_KR", "FOOD_CAT1_NM", "image_count", "timestamp", "directory"]

ImageFile.LOAD_TRUNCATED_IMAGES = True

# ─────────────────────────────────────────────
# 경로/이름 유틸
# ─────────────────────────────────────────────
def ensure_log_file(log_csv: str, encoding: str = "utf-8-sig"):
    """crawl_log.csv가 없거나 비어 있으면 헤더만 있는 파일을 생성."""
    # 폴더가 없으면 먼저 생성
    os.makedirs(os.path.dirname(log_csv) or ".", exist_ok=True)

    if not os.path.exists(log_csv) or os.path.getsize(log_csv) == 0:
        df = pd.DataFrame(columns=LOG_COLUMNS)
        df.to_csv(log_csv, index=False, encoding=encoding)
        try:
            print(f"[INIT] created empty log file: {log_csv} (encoding={encoding})")
        except Exception:
            pass

def sanitize(text: str, max_len: int = 80) -> str:
    t = unicodedata.normalize("NFKC", str(text).strip())
    for ch in '<>:"/\\|?*':
        t = t.replace(ch, "_")
    t = t.replace("\n", "_").replace("\r", "_").replace("\t", "_")
    return t[:max_len]

def get_save_path(base_dir: str, category: str, product_name: str) -> str:
    folder_name = sanitize(product_name).replace(" ", "_")
    cat = sanitize(category)
    save_path = os.path.join(base_dir, cat, folder_name)
    os.makedirs(save_path, exist_ok=True)
    return save_path

# ─────────────────────────────────────────────
# Selenium
# ─────────────────────────────────────────────
def setup_driver(headless: bool = True, window_size: str = "1920,1080"):
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"--window-size={window_size}")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=opts)

def scroll_to_load(driver, scroll_pause: float = 1.0, max_scrolls: int = 15):
    last_height = driver.execute_script("return document.body.scrollHeight")
    for i in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_pause)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            log("[STOP] scroll end (no more content)")
            break
        last_height = new_height
        log("[SCROLL]", f"{i+1}/{max_scrolls}")

# ─────────────────────────────────────────────
# 이미지 저장 유틸 (메타 제거 + PNG 기본)
# ─────────────────────────────────────────────
def guess_ext_from_headers(resp: requests.Response) -> str | None:
    ctype = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not ctype:
        return None
    if ctype == "image/jpg":
        return "jpg"
    ext = mimetypes.guess_extension(ctype)
    if ext and ext.startswith("."):
        ext = ext[1:]
    if ext == "jpe":
        ext = "jpg"
    return ext

def rasterize_image(img: Image.Image, mode: str = "RGB") -> Image.Image:
    try:
        src = img.convert(mode) if img.mode != mode else img
    except Exception:
        src = img.convert("RGB"); mode = "RGB"
    out = Image.new(mode, src.size)
    out.paste(src)
    return out  # info/exif/icc 제거된 래스터

def robust_save_image(resp: requests.Response, save_dir: str, index: int,
                      prefer_format: str = "png") -> str | None:
    try:
        img = Image.open(BytesIO(resp.content))
        img.load()
    except Exception:
        return None

    clean = rasterize_image(img, "RGB")

    fmt = (prefer_format or "png").lower()
    if fmt not in {"png", "jpg", "jpeg"}:
        fmt = "png"
    ext = "png" if fmt == "png" else "jpg"

    # BytesIO에 먼저 저장 → 파일로 기록 (경로 인코딩 이슈 회피)
    try:
        buf = BytesIO()
        if fmt == "png":
            clean.save(buf, format="PNG", optimize=True)
        else:
            clean.save(buf, format="JPEG", quality=92, optimize=True)
        data = buf.getvalue()
        path = os.path.join(save_dir, f"{index:03d}.{ext}")
        with open(path, "wb") as f:
            f.write(data)
        return path
    except Exception:
        # 최후 폴백: PNG로 강제 저장
        try:
            buf = BytesIO()
            clean.save(buf, format="PNG", optimize=True)
            data = buf.getvalue()
            path = os.path.join(save_dir, f"{index:03d}.png")
            with open(path, "wb") as f:
                f.write(data)
            return path
        except Exception:
            return None

# ─────────────────────────────────────────────
# 로그 CSV (upsert)
# ─────────────────────────────────────────────
def load_log_df(log_csv: str, encoding: str) -> pd.DataFrame:
    if os.path.exists(log_csv):
        df = pd.read_csv(log_csv, encoding=encoding)
        for col in LOG_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        return df[LOG_COLUMNS]
    else:
        return pd.DataFrame(columns=LOG_COLUMNS)

def upsert_log_row(df: pd.DataFrame, name: str, cat: str, count: int, directory: str) -> pd.DataFrame:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    mask = (df["FOOD_NM_KR"] == name) & (df["FOOD_CAT1_NM"] == cat)
    if mask.any():
        i = df[mask].index[0]
        df.at[i, "image_count"] = count
        df.at[i, "timestamp"] = ts
        df.at[i, "directory"] = directory
    else:
        df = pd.concat([df, pd.DataFrame([{
            "FOOD_NM_KR": name,
            "FOOD_CAT1_NM": cat,
            "image_count": count,
            "timestamp": ts,
            "directory": directory
        }])], ignore_index=True)
    return df

# ─────────────────────────────────────────────
# 크롤링
# ─────────────────────────────────────────────
def crawl_naver_images(product_name: str, category: str,
                       base_dir: str, max_images: int,
                       extra_keywords: str | None,
                       request_timeout: float = 5.0) -> tuple[int, str]:
    save_path = get_save_path(base_dir, category, product_name)
    driver = setup_driver()

    q = product_name.strip()
    if extra_keywords:
        q = f"{q} {extra_keywords}".strip()

    url = f"https://search.naver.com/search.naver?where=image&query={q}"
    driver.get(url)
    time.sleep(2)
    scroll_to_load(driver)

    selector_candidates = [
        "img._fe_image_tab_content_thumbnail_image",
        "img._image",
        "img",
    ]
    imgs = []
    for css in selector_candidates:
        try:
            imgs = driver.find_elements(By.CSS_SELECTOR, css)
        except Exception:
            imgs = []
        if len(imgs) >= 30:
            break

    log("[FOUND]", f"q='{q}'", f"imgs={len(imgs)}")
    saved = 0

    for el in imgs:
        if saved >= max_images:
            break
        src = el.get_attribute("src") or el.get_attribute("data-src")
        if not src or not src.startswith("http"):
            continue

        try:
            resp = requests.get(src, timeout=request_timeout, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": url
            })
            if resp.status_code != 200 or not resp.content:
                continue

            saved_path = robust_save_image(resp, save_path, saved + 1, prefer_format="png")
            if saved_path:
                log("[OK]", f"{saved+1:03d}", "saved ->", saved_path)
                saved += 1
                time.sleep(0.1)
            else:
                log("[WARN] save skipped")
        except Exception as e:
            # 절대 한글/이모지 찍지 않음
            log("[ERR] save failed", str(e))

    driver.quit()
    log("[DONE]", product_name, "saved:", saved, "dir:", save_path)
    return saved, save_path.replace("\\", "/")

# ─────────────────────────────────────────────
# 메인
# ─────────────────────────────────────────────
def main():
    ensure_log_file(args.log_csv, encoding=args.encoding)
    log_df = load_log_df(args.log_csv, encoding=args.encoding)

    p = argparse.ArgumentParser(description="네이버 이미지 크롤링 (원본 CSV 읽기, 로그 CSV 기록)")
    p.add_argument("--input-csv", default=DEFAULT_INPUT_CSV, help="입력(원본) CSV 경로")
    p.add_argument("--log-csv", default=DEFAULT_LOG_CSV, help="진행 기록 로그 CSV 경로")
    p.add_argument("--base-save-dir", default=DEFAULT_BASE_SAVE_DIR, help="이미지 저장 루트 폴더")
    p.add_argument("--max-images", type=int, default=300, help="제품별 최대 저장 이미지 수")
    p.add_argument("--extra-keywords", default="", help="검색 품질 향상용 추가 키워드")
    p.add_argument("--force", action="store_true", help="로그 기록이 있어도 재수집")
    p.add_argument("--encoding", default="utf-8-sig", help="CSV 인코딩 (기본 utf-8-sig)")
    args = p.parse_args()

    if not os.path.exists(args.input_csv):
        raise FileNotFoundError(f"Input CSV not found: {args.input_csv}")

    src = pd.read_csv(args.input_csv, encoding=args.encoding)
    for col in ["FOOD_NM_KR", "FOOD_CAT1_NM"]:
        if col not in src.columns:
            raise ValueError(f"'{col}' column is required in input CSV.")

    log_df = load_log_df(args.log_csv, encoding=args.encoding)

    for _, row in src.iterrows():
        name = str(row["FOOD_NM_KR"]).strip()
        cat = str(row["FOOD_CAT1_NM"]).strip()

        if not args.force:
            mask = (log_df["FOOD_NM_KR"] == name) & (log_df["FOOD_CAT1_NM"] == cat)
            if mask.any():
                r = log_df[mask].iloc[0]
                if pd.notna(r.get("image_count")) and pd.notna(r.get("timestamp")):
                    log("[SKIP]", cat, name, "(already crawled)")
                    continue

        log("[START]", cat, name)
        cnt, directory = crawl_naver_images(
            product_name=name,
            category=cat,
            base_dir=args.base_save_dir,
            max_images=args.max_images,
            extra_keywords=(args.extra_keywords or "").strip() or None,
        )

        log_df = upsert_log_row(log_df, name, cat, cnt, directory)
        log_df.to_csv(args.log_csv, index=False, encoding=args.encoding)

    log("[ALL DONE]")

if __name__ == "__main__":
    main()
