# 대체당 관련

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from backend.database import get_db
from backend import crud, schemas

router = APIRouter(prefix="/sweeteners", tags=["sweeteners"])

@router.get("", response_model=List[schemas.Sweetener])
def list_sweeteners(db: Session = Depends(get_db)):
    # 리스트 반환
    return crud.get_sweeteners(db)
