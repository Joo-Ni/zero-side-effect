# 제품 정보

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import crud, schemas, models

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=List[schemas.ProductListItem])
def list_products(db: Session = Depends(get_db)):
    # 기본 목록
    products = crud.get_products(db)
    result = []

    for p in products:
        sweet = [ps.sweetener.name for ps in p.sweeteners]

        result.append(
            schemas.ProductListItem(
                id=p.id,
                name=p.name,
                category_id=p.category_id,
                sweeteners=sweet,
                image_url=p.image_url
            )
        )

    return result


@router.get("/{product_id}/full", response_model=schemas.ProductDetail)
def get_product_detail(product_id: int, db: Session = Depends(get_db)):
    # 단일 제품
    p = crud.get_product_by_id(db, product_id)
    if not p:
        raise HTTPException(status_code=404, detail="Product not found")

    # 카테고리
    if p.category:
        category = {"id": p.category.id, "name": p.category.name}
    else:
        category = None

    # 대체당
    sweets = []
    for ps in p.sweeteners:
        if ps.sweetener:
            sweets.append({
                "id": ps.sweetener.id,
                "name": ps.sweetener.name
            })

    # 영양 성분
    if p.nutrition:
        nf = {
            "kcal": p.nutrition.kcal,
            "carbohydrate_g": p.nutrition.carbohydrate_g,
            "sugar_g": p.nutrition.sugar_g,
            "fat_g": p.nutrition.fat_g,
            "saturated_fat_g": p.nutrition.saturated_fat_g,
            "trans_fat_g": p.nutrition.trans_fat_g,
            "protein_g": p.nutrition.protein_g,
            "sodium_mg": p.nutrition.sodium_mg,
        }
    else:
        nf = None

    # 최종 데이터
    return {
        "id": p.id,
        "name": p.name,
        "brand": p.brand,
        "volume": str(p.volume) if p.volume is not None else None,
        "image_url": p.image_url,
        "category": category,
        "sweeteners": sweets,
        "nutrition": nf,
    }
