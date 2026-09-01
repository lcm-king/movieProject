from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, crud, auth, models

router = APIRouter(prefix="/api/ratings", tags=["ratings"])


@router.post("/", response_model=schemas.RatingOut)
def rate_movie(
    data: schemas.RatingCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    movie = crud.get_movie_by_id(db, data.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")
    rating = crud.upsert_rating(db, current_user.id, data.movie_id, data.rating)
    return rating


@router.get("/my/{movie_id}")
def get_my_rating(
    movie_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    rating = crud.get_user_rating(db, current_user.id, movie_id)
    if rating:
        return {"rating": rating.rating}
    return {"rating": None}
