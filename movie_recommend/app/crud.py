from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, and_, or_, distinct
from typing import List, Optional, Set
from . import models

# Canonical genre catalog — the single source of truth
CANONICAL_GENRES = [
    "动作", "喜剧", "剧情", "科幻", "爱情", "犯罪",
    "悬疑", "动画", "奇幻", "冒险", "战争", "历史",
    "音乐", "灾难", "家庭", "恐怖",
]

GENRE_ALIASES = {
    "科幻片": "科幻", "动作片": "动作", "喜剧片": "喜剧", "爱情片": "爱情",
    "恐怖片": "恐怖", "动画片": "动画", "歌舞": "音乐", "魔幻": "奇幻",
    "惊悚": "悬疑", "犯罪片": "犯罪", "剧情片": "剧情", "战争片": "战争",
}


def _normalize_genre(raw: str) -> str:
    g = raw.strip()
    return GENRE_ALIASES.get(g, g)


def _split_genres(genre_str: str) -> List[str]:
    return [_normalize_genre(g) for g in genre_str.split(",") if g.strip()]


# ── Genre helpers ──────────────────────────────────────────────

def _get_genre_ids_by_names(db: Session, names: List[str]) -> Set[int]:
    """Resolve canonical genre names → PK ids (indexed lookup on genres.name)."""
    normalized = {_normalize_genre(n) for n in names}
    rows = db.query(models.Genre.id).filter(models.Genre.name.in_(normalized)).all()
    return {r[0] for r in rows}


def _build_genre_display(db: Session, movie_id: int) -> str:
    """Return comma-separated genre string for display column."""
    rows = (
        db.query(models.Genre.name)
        .join(models.MovieGenre, models.MovieGenre.genre_id == models.Genre.id)
        .filter(models.MovieGenre.movie_id == movie_id)
        .order_by(models.Genre.id)
        .all()
    )
    return ",".join(r[0] for r in rows)


def seed_genres(db: Session):
    """Idempotent: insert canonical genres if the table is empty."""
    if db.query(models.Genre).count() == 0:
        for name in CANONICAL_GENRES:
            db.add(models.Genre(name=name))
        db.commit()


# ── User CRUD ──────────────────────────────────────────────────

def create_user(db: Session, username: str, email: str, hashed_password: str, preferred_genres: str, role: str = "user") -> models.User:
    user = models.User(
        username=username, email=email,
        hashed_password=hashed_password, preferred_genres=preferred_genres,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def update_user_genres(db: Session, user: models.User, genres_str: str) -> models.User:
    user.preferred_genres = genres_str
    db.commit()
    db.refresh(user)
    return user


def get_all_users(db: Session) -> List[models.User]:
    return db.query(models.User).all()


def set_user_active(db: Session, user: models.User, is_active: bool):
    user.is_active = is_active
    db.commit()
    db.refresh(user)


# ── Movie CRUD (JOIN-based, indexed) ───────────────────────────

def get_movies(
    db: Session,
    page: int = 1,
    page_size: int = 12,
    genres: Optional[List[str]] = None,
    rating_min: Optional[float] = None,
    rating_max: Optional[float] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    search: Optional[str] = None,
):
    query = db.query(models.Movie)

    if genres:
        normalized = [_normalize_genre(g) for g in genres]
        genre_ids = _get_genre_ids_by_names(db, normalized)
        if not genre_ids:
            return [], 0  # no such genre → empty result

        # AND-mode: movie must link to ALL requested genres
        # Strategy: JOIN → WHERE genre_id IN (...) → GROUP BY movie → HAVING COUNT = N
        sub = (
            db.query(models.MovieGenre.movie_id)
            .filter(models.MovieGenre.genre_id.in_(genre_ids))
            .group_by(models.MovieGenre.movie_id)
            .having(func.count(distinct(models.MovieGenre.genre_id)) == len(genre_ids))
            .subquery()
        )
        query = query.join(sub, models.Movie.id == sub.c.movie_id)

    if rating_min is not None:
        query = query.filter(models.Movie.avg_rating >= rating_min)
    if rating_max is not None:
        query = query.filter(models.Movie.avg_rating <= rating_max)
    if year_from is not None:
        query = query.filter(models.Movie.release_year >= year_from)
    if year_to is not None:
        query = query.filter(models.Movie.release_year <= year_to)
    if search:
        query = query.filter(models.Movie.title.contains(search))

    total = query.count()
    movies = query.order_by(models.Movie.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return movies, total


def get_movie_by_id(db: Session, movie_id: int) -> Optional[models.Movie]:
    return db.query(models.Movie).filter(models.Movie.id == movie_id).first()


def get_top_movies_by_genre(db: Session, genre: str, limit: int = 10) -> List[models.Movie]:
    """Top-rated movies in a given canonical genre (indexed JOIN)."""
    normalized = _normalize_genre(genre)
    return (
        db.query(models.Movie)
        .join(models.MovieGenre, models.MovieGenre.movie_id == models.Movie.id)
        .join(models.Genre, models.Genre.id == models.MovieGenre.genre_id)
        .filter(models.Genre.name == normalized)
        .order_by(models.Movie.avg_rating.desc())
        .limit(limit)
        .all()
    )


def get_movies_for_ai(db: Session, limit: int = 50) -> List[models.Movie]:
    return db.query(models.Movie).order_by(models.Movie.avg_rating.desc()).limit(limit).all()


def get_movie_genre_names(db: Session, movie_id: int) -> List[str]:
    return [
        r[0] for r in
        db.query(models.Genre.name)
        .join(models.MovieGenre, models.MovieGenre.genre_id == models.Genre.id)
        .filter(models.MovieGenre.movie_id == movie_id)
        .all()
    ]


# ── Rating CRUD ────────────────────────────────────────────────

def upsert_rating(db: Session, user_id: int, movie_id: int, rating_value: int) -> models.Rating:
    existing = (
        db.query(models.Rating)
        .filter(models.Rating.user_id == user_id, models.Rating.movie_id == movie_id)
        .first()
    )
    if existing:
        existing.rating = rating_value
        db.commit()
        db.refresh(existing)
        _update_movie_avg_rating(db, movie_id)
        return existing
    rating = models.Rating(user_id=user_id, movie_id=movie_id, rating=rating_value)
    db.add(rating)
    db.commit()
    db.refresh(rating)
    _update_movie_avg_rating(db, movie_id)
    return rating


def get_user_rating(db: Session, user_id: int, movie_id: int) -> Optional[models.Rating]:
    return (
        db.query(models.Rating)
        .filter(models.Rating.user_id == user_id, models.Rating.movie_id == movie_id)
        .first()
    )


def get_user_ratings(db: Session, user_id: int) -> List[models.Rating]:
    return db.query(models.Rating).filter(models.Rating.user_id == user_id).all()


def get_rating_distribution(db: Session, movie_id: int) -> dict:
    rows = (
        db.query(models.Rating.rating, func.count(models.Rating.id))
        .filter(models.Rating.movie_id == movie_id)
        .group_by(models.Rating.rating)
        .all()
    )
    dist = {str(i): 0 for i in range(1, 11)}
    for rating, count in rows:
        dist[str(rating)] = count
    return dist


def _update_movie_avg_rating(db: Session, movie_id: int):
    movie = db.query(models.Movie).filter(models.Movie.id == movie_id).first()
    if movie:
        result = (
            db.query(func.avg(models.Rating.rating), func.count(models.Rating.id))
            .filter(models.Rating.movie_id == movie_id)
            .first()
        )
        movie.avg_rating = round(float(result[0]), 1) if result[0] else 0.0
        movie.rating_count = result[1] if result[1] else 0
        db.commit()


# ── Comment CRUD ───────────────────────────────────────────────

def create_comment(db: Session, user_id: int, movie_id: int, content: str, sentiment: Optional[str] = None) -> models.Comment:
    comment = models.Comment(user_id=user_id, movie_id=movie_id, content=content, sentiment=sentiment)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def get_movie_comments(db: Session, movie_id: int) -> List[models.Comment]:
    return (
        db.query(models.Comment)
        .filter(models.Comment.movie_id == movie_id)
        .order_by(models.Comment.created_at.desc())
        .all()
    )


def get_all_comments(db: Session) -> List[models.Comment]:
    return db.query(models.Comment).order_by(models.Comment.created_at.desc()).all()


def delete_comment(db: Session, comment_id: int):
    comment = db.query(models.Comment).filter(models.Comment.id == comment_id).first()
    if comment:
        db.delete(comment)
        db.commit()
        return True
    return False


def get_comment_by_id(db: Session, comment_id: int) -> Optional[models.Comment]:
    return db.query(models.Comment).filter(models.Comment.id == comment_id).first()
