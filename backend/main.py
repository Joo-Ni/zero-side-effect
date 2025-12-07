from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.routers import products, categories, sweeteners, predict

app = FastAPI(title="Zero Side Effect API", version="1.0.0")

# 정적파일
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# 프론트 연동
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(sweeteners.router)
app.include_router(predict.router)

@app.get("/")
def root():
    return {"msg": "api ok"}
