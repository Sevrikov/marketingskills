from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate
from app.services.products import create_product, get_product, list_products, update_product

router = APIRouter(prefix="/api/products", tags=["products"])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product_endpoint(payload: ProductCreate, db: Session = Depends(get_db)):
    return create_product(db, payload)


@router.get("", response_model=list[ProductRead])
def list_products_endpoint(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    return list_products(db, limit=limit, offset=offset)


@router.get("/{product_id}", response_model=ProductRead)
def get_product_endpoint(product_id: str, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductRead)
def update_product_endpoint(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return update_product(db, product, payload)
