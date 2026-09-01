from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, Boolean, ForeignKey, Index,
    UniqueConstraint, func
)
from sqlalchemy.orm import relationship
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    preferred_genres = Column(String(500), default="")
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    ratings = relationship("Rating", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")


class Genre(Base):
    """Canonical genre table — fixed set, indexed for fast filtering."""
    __tablename__ = "genres"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)

    movies = relationship("MovieGenre", back_populates="genre", cascade="all, delete-orphan")


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        Index("ix_movies_release_year", "release_year"),
        Index("ix_movies_avg_rating", "avg_rating"),
        Index("ix_movies_title_search", "title"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    genre = Column(String(200), nullable=False, default="")   # cached display string
    cover_url = Column(String(500), nullable=True)
    release_year = Column(Integer, nullable=True)
    avg_rating = Column(Float, default=0.0)
    rating_count = Column(Integer, default=0)

    # Many-to-many → Genre (for indexed queries)
    movie_genres = relationship("MovieGenre", back_populates="movie", cascade="all, delete-orphan")

    ratings = relationship("Rating", back_populates="movie", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="movie", cascade="all, delete-orphan")


class MovieGenre(Base):
    """Junction table — composite PK + individual FK indexes."""
    __tablename__ = "movie_genres"
    __table_args__ = (
        Index("ix_mg_movie", "movie_id"),
        Index("ix_mg_genre", "genre_id"),
    )

    movie_id = Column(Integer, ForeignKey("movies.id"), primary_key=True)
    genre_id = Column(Integer, ForeignKey("genres.id"), primary_key=True)

    movie = relationship("Movie", back_populates="movie_genres")
    genre = relationship("Genre", back_populates="movies")


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        UniqueConstraint("user_id", "movie_id", name="uq_user_movie_rating"),
        Index("ix_ratings_user", "user_id"),
        Index("ix_ratings_movie", "movie_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="ratings")
    movie = relationship("Movie", back_populates="ratings")


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (
        Index("ix_comments_movie", "movie_id"),
        Index("ix_comments_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    content = Column(Text, nullable=False)
    sentiment = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="comments")
    movie = relationship("Movie", back_populates="comments")
