from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# ---------- Auth ----------
class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=6)
    preferred_genres: List[str] = Field(default_factory=list)


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


# ---------- User ----------
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    preferred_genres: str
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    preferred_genres: List[str] = Field(default_factory=list)


class AdminUserAction(BaseModel):
    user_id: int
    action: str  # 'ban' or 'unban'


# ---------- Movie ----------
class MovieOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    genre: str
    cover_url: Optional[str] = None
    release_year: Optional[int] = None
    avg_rating: float
    rating_count: int

    class Config:
        from_attributes = True


class MovieListOut(BaseModel):
    movies: List[MovieOut]
    total: int
    page: int
    page_size: int


# ---------- Rating ----------
class RatingCreate(BaseModel):
    movie_id: int
    rating: int = Field(..., ge=1, le=10)


class RatingOut(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Comment ----------
class CommentCreate(BaseModel):
    movie_id: int
    content: str = Field(..., max_length=500)


class CommentOut(BaseModel):
    id: int
    user_id: int
    movie_id: int
    username: Optional[str] = None
    content: str
    sentiment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Recommendation ----------
class RecommendationOut(BaseModel):
    movie: MovieOut
    reason: str


# ---------- AI ----------
class AIRecommendRequest(BaseModel):
    query: str


class AIRecommendResponse(BaseModel):
    recommendations: list


class AIMovieQARequest(BaseModel):
    movie_id: int
    question: str


class AIMovieQAResponse(BaseModel):
    answer: str


class AISentimentRequest(BaseModel):
    comment_text: str


class AISentimentResponse(BaseModel):
    sentiment: str
    label: str


# ---------- Unified AI Chat ----------
class AIChatRequest(BaseModel):
    message: str


class AIChatResponse(BaseModel):
    reply: str
    source: str = "local"
