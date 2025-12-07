from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base

# 테이블 정의
class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)

    products = relationship("Product", back_populates="category")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    volume = Column(String(255))
    image_url = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    category = relationship("Category", back_populates="products")
    sweeteners = relationship("ProductSweetener", back_populates="product")
    nutrition = relationship("NutritionFacts", back_populates="product", uselist=False)


class Sweetener(Base):
    __tablename__ = "sweeteners"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    kcal_per_g = Column(Float)
    description = Column(String(1000))

    products = relationship("ProductSweetener", back_populates="sweetener")


class ProductSweetener(Base):
    __tablename__ = "product_sweeteners"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    sweetener_id = Column(Integer, ForeignKey("sweeteners.id"), nullable=False)

    amount_per_serving_mg = Column(Float)
    amount_per_100ml_mg = Column(Float)

    product = relationship("Product", back_populates="sweeteners")
    sweetener = relationship("Sweetener", back_populates="products")


class NutritionFacts(Base):
    __tablename__ = "nutrition_facts"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True)

    kcal = Column(Float)
    carbohydrate_g = Column(Float)
    sugar_g = Column(Float)
    fat_g = Column(Float)
    saturated_fat_g = Column(Float)
    trans_fat_g = Column(Float)
    protein_g = Column(Float)
    sodium_mg = Column(Float)

    product = relationship("Product", back_populates="nutrition")
