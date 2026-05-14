from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.content_draft import ContentDraft
from app.models.content_task import ContentTask
from app.schemas.product_content_profile import (
    ProductContentProfileGenerate,
    ProductContentProfileRead,
    ProductContentProfileUpdate,
)
from app.services.product_content_profiles import (
    approve_product_content_profile,
    generate_product_content_profile,
    get_product_content_profile,
    update_product_content_profile,
)
from app.services.products import get_product

router = APIRouter(prefix="/api/products", tags=["product content profiles"])


@router.get("/{product_id}/content-profile", response_model=ProductContentProfileRead)
def get_product_content_profile_endpoint(product_id: str, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    profile = get_product_content_profile(db, product_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product content profile not found",
        )
    return profile


@router.post("/{product_id}/content-profile/generate", response_model=ProductContentProfileRead)
def generate_product_content_profile_endpoint(
    product_id: str,
    payload: ProductContentProfileGenerate,
    db: Session = Depends(get_db),
):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    _validate_sources(db, payload)
    return generate_product_content_profile(
        db,
        product,
        source_task_id=payload.source_task_id,
        source_draft_id=payload.source_draft_id,
        language=payload.language,
    )


@router.patch("/{product_id}/content-profile", response_model=ProductContentProfileRead)
def update_product_content_profile_endpoint(
    product_id: str,
    payload: ProductContentProfileUpdate,
    db: Session = Depends(get_db),
):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    profile = get_product_content_profile(db, product_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product content profile not found",
        )
    return update_product_content_profile(db, profile, payload)


@router.post("/{product_id}/content-profile/approve", response_model=ProductContentProfileRead)
def approve_product_content_profile_endpoint(product_id: str, db: Session = Depends(get_db)):
    product = get_product(db, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    profile = get_product_content_profile(db, product_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product content profile not found",
        )
    return approve_product_content_profile(db, profile)


def _validate_sources(db: Session, payload: ProductContentProfileGenerate) -> None:
    if payload.source_task_id and db.get(ContentTask, payload.source_task_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source task not found")
    if not payload.source_draft_id:
        return
    draft = db.get(ContentDraft, payload.source_draft_id)
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source draft not found")
    if payload.source_task_id and draft.task_id != payload.source_task_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Source draft does not belong to source task",
        )
