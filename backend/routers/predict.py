# 이미지 예측

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models

from pathlib import Path
from io import BytesIO
from PIL import Image
import numpy as np
import tensorflow as tf
import json
from tensorflow.keras.applications.efficientnet import preprocess_input as eff_pp

router = APIRouter(prefix="/predict", tags=["predict"])

BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BASE_DIR.parent
MODELS_DIR = PROJECT_ROOT / "models"

# 캐시(모델/라벨)
_model_cache = {}
_label_cache = {}


def _load_model_and_labels(category_name: str):
    # 모델 + 라벨 로드
    if category_name in _model_cache:
        return _model_cache[category_name], _label_cache[category_name]

    dir_ = MODELS_DIR / category_name
    model_file = dir_ / "best.keras"
    label_file = dir_ / "label_map.json"

    if not model_file.exists() or not label_file.exists():
        raise FileNotFoundError("model or label missing")

    model = tf.keras.models.load_model(model_file)

    with open(label_file, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if isinstance(raw, dict):
        labels = [raw[str(i)] for i in range(len(raw))]
    else:
        labels = raw

    _model_cache[category_name] = model
    _label_cache[category_name] = labels
    return model, labels


def _preprocess_image(image_bytes: bytes, size=(224, 224)):
    img = Image.open(BytesIO(image_bytes)).convert("RGB")
    img = img.resize(size)
    arr = np.array(img).astype("float32")
    arr = eff_pp(arr)
    return np.expand_dims(arr, axis=0)


@router.post("")
async def predict_product(
    category_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # 카테고리 확인
    cat = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not cat:
        raise HTTPException(400, "invalid category_id")

    # 이미지 확인
    if file.content_type is None or not file.content_type.startswith("image/"):
        raise HTTPException(400, "image only")

    img_bytes = await file.read()

    # 모델 준비
    try:
        model, labels = _load_model_and_labels(cat.name)
    except Exception as e:
        raise HTTPException(500, str(e))

    # 예측
    try:
        x = _preprocess_image(img_bytes)
        preds = model.predict(x)[0]
    except Exception as e:
        raise HTTPException(500, f"predict error: {e}")

    # topk
    k = min(5, preds.shape[0])
    idxs = np.argsort(preds)[::-1][:k]

    results = []
    for rank, idx in enumerate(idxs, start=1):
        label = labels[idx]
        product = (
            db.query(models.Product)
            .filter(models.Product.name == label, models.Product.category_id == category_id)
            .first()
        )

        results.append({
            "rank": rank,
            "name": label,
            "product_id": product.id if product else None
        })

    if not results:
        raise HTTPException(500, "no prediction")

    return {"results": results}
