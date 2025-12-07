# 카테고리 관련

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import crud, schemas

router = APIRouter(prefix="/categories", tags=["categories"])

@router.get("", response_model=List[schemas.Category])
def list_categories(db: Session = Depends(get_db)):
    # 전체 카테고리
    return crud.get_categories(db)
