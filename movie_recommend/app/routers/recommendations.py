from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from collections import Counter
from ..database import get_db
from .. import crud, auth, models

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/")
def get_recommendations(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    user_ratings = crud.get_user_ratings(db, current_user.id)
    rated_movie_ids = {r.movie_id for r in user_ratings}
    recommendations = []

    if user_ratings:
        # Build user genre profile from actual rating data
        genre_profile = {}
        for r in user_ratings:
            if r.rating < 5:  # skip low-rated — user doesn't like this type
                continue
            genre_names = crud.get_movie_genre_names(db, r.movie_id)
            for g in genre_names:
                if g not in genre_profile:
                    genre_profile[g] = {"sum": 0.0, "count": 0}
                genre_profile[g]["sum"] += r.rating
                genre_profile[g]["count"] += 1

        # Score each genre: confidence = avg_rating × sqrt(count)
        scored_genres = []
        for g, d in genre_profile.items():
            avg = d["sum"] / d["count"]
            confidence = avg * (d["count"] ** 0.5)
            scored_genres.append((g, avg, confidence, d["count"]))

        scored_genres.sort(key=lambda x: x[2], reverse=True)

        # Collect candidates from top genres, weighted by affinity
        candidates = []
        for genre, avg_rating, confidence, count in scored_genres[:5]:
            movies = crud.get_top_movies_by_genre(db, genre, limit=10)
            for movie in movies:
                if movie.id in rated_movie_ids:
                    continue
                overlap = len(set(crud.get_movie_genre_names(db, movie.id)) & set(genre_profile.keys()))
                score = movie.avg_rating * confidence * (1 + 0.3 * overlap)
                candidates.append({
                    "movie": movie,
                    "score": score,
                    "primary_genre": genre,
                    "reason": f"因为你给{genre}类电影打过高分（平均{avg_rating:.1f}分/{count}部）",
                })

        candidates.sort(key=lambda x: x["score"], reverse=True)

        # Pick top 10 with diversity (max 3 per primary genre)
        used = Counter()
        for c in candidates:
            if len(recommendations) >= 10:
                break
            if used[c["primary_genre"]] < 3:
                recommendations.append({"movie": c["movie"], "reason": c["reason"]})
                used[c["primary_genre"]] += 1

    if not recommendations:
        # New user: use registration preferences
        pref = crud._split_genres(current_user.preferred_genres) if current_user.preferred_genres else []
        seen = set()
        for g in pref:
            if not g:
                continue
            for movie in crud.get_top_movies_by_genre(db, g, limit=8):
                if movie.id not in seen and movie.id not in rated_movie_ids and len(recommendations) < 10:
                    recommendations.append({
                        "movie": movie,
                        "reason": f"根据你偏好的{g}类型推荐热门高分影片",
                    })
                    seen.add(movie.id)

    # Ultimate fallback
    if not recommendations:
        all_movies, _ = crud.get_movies(db, page=1, page_size=50)
        for movie in all_movies:
            if movie.id not in rated_movie_ids and len(recommendations) < 10:
                recommendations.append({"movie": movie, "reason": "为你推荐热门高分电影"})

    return recommendations[:10]
