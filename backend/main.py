# backend/main.py
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.routers import products, categories, sweeteners, predict

app = FastAPI(
    title="Zero Side Effect API",
    version="1.0.0",
)

# 프로젝트 루트 기준으로 frontend 폴더 위치
BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"

# 백엔드 static (필요하면 사용)
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# 프론트엔드 정적 파일
app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


# CORS (프론트에서 API 호출용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(sweeteners.router)
app.include_router(predict.router)


# 메인 페이지: index.html 반환
@app.get("/", include_in_schema=False)
def root():
    index_file = FRONTEND_DIR / "index.html"
    return FileResponse(index_file)
