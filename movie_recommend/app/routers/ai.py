from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, crud, auth, models
from ..dify_client import call_dify_workflow, unified_chat

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/movie-recommend")
async def ai_movie_recommend(
    data: schemas.AIRecommendRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    movies = crud.get_movies_for_ai(db, limit=50)
    movies_info = "\n".join(
        f"- {m.title} ({m.release_year}) | 类型: {m.genre} | 评分: {m.avg_rating} | 简介: {m.description[:100] if m.description else ''}"
        for m in movies
    )

    result = await call_dify_workflow("movie_recommend", {
        "query": data.query,
        "movies_info": movies_info,
    })
    return result


@router.post("/movie-qa")
async def ai_movie_qa(
    data: schemas.AIMovieQARequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    movie = crud.get_movie_by_id(db, data.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    movie_info = f"标题: {movie.title}\n类型: {movie.genre}\n年份: {movie.release_year}\n评分: {movie.avg_rating}\n简介: {movie.description}"

    result = await call_dify_workflow("movie_qa", {
        "movie_info": movie_info,
        "question": data.question,
    })
    return result


@router.post("/sentiment")
async def ai_sentiment_analysis(
    data: schemas.AISentimentRequest,
    current_user: models.User = Depends(auth.get_current_user),
):
    result = await call_dify_workflow("sentiment_analysis", {
        "comment_text": data.comment_text,
    })
    return result


@router.post("/chat", response_model=schemas.AIChatResponse)
async def ai_chat(
    data: schemas.AIChatRequest,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    movies = crud.get_movies_for_ai(db, limit=50)
    movies_data = [
        {
            "title": m.title,
            "year": m.release_year,
            "genre": m.genre,
            "rating": m.avg_rating,
            "description": m.description[:200] if m.description else "",
        }
        for m in movies
    ]
    return await unified_chat(data.message, movies_data)
