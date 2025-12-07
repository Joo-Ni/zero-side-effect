# Zero Side Effect

제로슈가 제품에 어떤 대체당이 들어있는지 확인할 수 있는 서비스입니다.  
제품을 직접 선택해서 보거나, 사진을 업로드하여 비슷한 제품을 찾아 확인할 수 있습니다.

---

## 기능

- 제품 목록 / 상세 정보 보기
- 포함된 대체당 확인
- 이미지 업로드 → 카테고리별 모델로 예측
- 카테고리 / 대체당 기준 필터링

---

## 폴더 구조

```text
zero_side_effect/
├── backend/                  # FastAPI 서버
│   ├── main.py               # 엔트리포인트
│   ├── database.py           # DB 연결
│   ├── config.py             # .env 불러오기
│   ├── crud.py               # 기본 DB 조회 함수
│   ├── models.py             # SQLAlchemy 모델 정의
│   ├── schemas.py            # Pydantic 스키마
│   ├── update_images.py      # 썸네일 경로 업데이트 스크립트
│   ├── routers/              # API 라우터
│   │   ├── products.py       # 제품 목록/상세
│   │   ├── categories.py     # 카테고리 API
│   │   ├── sweeteners.py     # 대체당 API
│   │   └── predict.py        # 이미지 예측
│   ├── static/               # 정적 파일
│   └── .env                  # 환경 변수
│
├── frontend/                 # 정적 페이지
│   ├── index.html
│   ├── detail.html
│   ├── category.html
│   ├── sweetener.html
│   ├── css/
│   └── js/
│
├── models/
│   ├── filter_by_thumbnail.py            # 이미지 전처리 스크립트
│   ├── train_multi_category_filtered.py  # 모델 학습 스크립트
│   ├── 음료/
│   ├── 과자 및 스낵/
│   └── 기타 카테고리 폴더들
│
├── requirements.txt
└── README.md

```
