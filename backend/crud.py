from typing import List, Optional
from sqlalchemy.orm import Session
from backend import models


def get_categories(db: Session) -> List[models.Category]:
    return db.query(models.Category).order_by(models.Category.id).all()


def get_sweeteners(db: Session) -> List[models.Sweetener]:
    return db.query(models.Sweetener).order_by(models.Sweetener.id).all()


def get_products(db: Session) -> List[models.Product]:
    return db.query(models.Product).order_by(models.Product.name).all()


def get_product_by_id(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).filter(models.Product.id == product_id).first()
