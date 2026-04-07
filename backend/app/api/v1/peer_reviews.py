import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, get_db
from app.models.peer_review import PeerReview
from app.schemas.scores import PeerReviewCreate, PeerReviewRead

router = APIRouter(prefix="/peer-reviews", tags=["peer-reviews"])


@router.get("/", response_model=list[PeerReviewRead])
async def list_peer_reviews(
    reviewee_id: uuid.UUID | None = None,
    reviewer_id: uuid.UUID | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(PeerReview)
    if reviewee_id:
        query = query.where(PeerReview.reviewee_id == reviewee_id)
    if reviewer_id:
        query = query.where(PeerReview.reviewer_id == reviewer_id)
    query = query.order_by(PeerReview.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.post("/", response_model=PeerReviewRead, status_code=status.HTTP_201_CREATED)
async def create_peer_review(
    data: PeerReviewCreate,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    review = PeerReview(
        id=uuid.uuid4(),
        tenant_id=uuid.UUID(current_user["tenant_id"]),
        reviewer_id=uuid.UUID(current_user["sub"]),
        **data.model_dump(),
    )
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


@router.get("/{review_id}", response_model=PeerReviewRead)
async def get_peer_review(
    review_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await session.execute(select(PeerReview).where(PeerReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return review
