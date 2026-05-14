from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


def create_product(db: Session, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def list_products(db: Session, limit: int = 50, offset: int = 0) -> list[Product]:
    stmt = select(Product).order_by(Product.created_at.desc()).limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_product(db: Session, product_id: str) -> Product | None:
    return db.get(Product, product_id)


def update_product(db: Session, product: Product, data: ProductUpdate) -> Product:
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(product, key, value)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product
