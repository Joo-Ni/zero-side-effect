from typing import List, Optional
from pydantic import BaseModel

# pydantic 모델들, 프론트


class Category(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class Sweetener(BaseModel):
    id: int
    name: str
    kcal_per_g: Optional[float] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True


class NutritionFacts(BaseModel):
    kcal: Optional[float]
    carbohydrate_g: Optional[float]
    sugar_g: Optional[float]
    fat_g: Optional[float]
    saturated_fat_g: Optional[float]
    trans_fat_g: Optional[float]
    protein_g: Optional[float]
    sodium_mg: Optional[float]

    class Config:
        orm_mode = True


class ProductListItem(BaseModel):
    id: int
    name: str
    category_id: int
    sweeteners: List[str]
    image_url: Optional[str] = None

    class Config:
        orm_mode = True


class ProductSweetenerItem(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True


class ProductDetail(BaseModel):
    id: int
    name: str
    brand: Optional[str] = None
    volume: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[Category] = None
    sweeteners: List[ProductSweetenerItem] = []
    nutrition: Optional[NutritionFacts] = None

    class Config:
        orm_mode = True
