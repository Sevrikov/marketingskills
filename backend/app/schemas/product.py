from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    sku: str | None = None
    gtin: str | None = None
    mpn: str | None = None
    price: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    availability: str | None = None
    cms_product_id: str | None = None
    source_url: str | None = None
    raw_description: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    brand: str | None = None
    model: str | None = None
    category: str | None = None
    sku: str | None = None
    gtin: str | None = None
    mpn: str | None = None
    price: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    availability: str | None = None
    cms_product_id: str | None = None
    source_url: str | None = None
    raw_description: str | None = None


class ProductRead(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
