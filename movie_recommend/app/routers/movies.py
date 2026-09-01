from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from ..database import get_db
from .. import schemas, crud

router = APIRouter(prefix="/api/movies", tags=["movies"])


@router.get("/", response_model=schemas.MovieListOut)
def get_movies(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    genres: Optional[str] = Query(None),
    rating_min: Optional[float] = Query(None),
    rating_max: Optional[float] = Query(None),
    year_from: Optional[int] = Query(None),
    year_to: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    genre_list = genres.split(",") if genres else None
    movies, total = crud.get_movies(
        db=db,
        page=page,
        page_size=page_size,
        genres=genre_list,
        rating_min=rating_min,
        rating_max=rating_max,
        year_from=year_from,
        year_to=year_to,
        search=search,
    )
    return schemas.MovieListOut(movies=movies, total=total, page=page, page_size=page_size)


@router.get("/{movie_id}", response_model=schemas.MovieOut)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = crud.get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")
    return movie


@router.get("/{movie_id}/rating-distribution")
def get_rating_distribution(movie_id: int, db: Session = Depends(get_db)):
    movie = crud.get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")
    return crud.get_rating_distribution(db, movie_id)
