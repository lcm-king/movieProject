"""Admin endpoints: full CRUD for movies, users, comments, ratings."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, crud, auth, models
from ..models import Movie, MovieGenre, Genre

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(current_user: models.User = Depends(auth.get_admin_user)):
    return current_user


# ── Movie CRUD ─────────────────────────────────────────────────

@router.get("/movies")
def admin_list_movies(
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    movies, total = crud.get_movies(db, page=1, page_size=1000)
    return {"movies": movies, "total": total}


@router.post("/movies")
def admin_create_movie(
    data: dict,
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    title = data.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="电影名称不能为空")

    genres = data.get("genres", [])
    if isinstance(genres, str):
        genres = [g.strip() for g in genres.split(",") if g.strip()]

    movie = Movie(
        title=title,
        description=data.get("description", ""),
        genre=",".join(genres),
        cover_url=data.get("cover_url", ""),
        release_year=data.get("release_year"),
        avg_rating=0.0,
        rating_count=0,
    )
    db.add(movie)
    db.flush()

    # Link genres
    genre_map = {g.name: g.id for g in db.query(Genre).all()}
    for g_name in genres:
        g_name = crud._normalize_genre(g_name)
        g_id = genre_map.get(g_name)
        if g_id:
            db.add(MovieGenre(movie_id=movie.id, genre_id=g_id))

    db.commit()
    db.refresh(movie)
    return {"message": "电影已添加", "movie_id": movie.id}


@router.put("/movies/{movie_id}")
def admin_update_movie(
    movie_id: int,
    data: dict,
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    movie = crud.get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")

    if "title" in data:
        movie.title = data["title"].strip()
    if "description" in data:
        movie.description = data["description"]
    if "cover_url" in data:
        movie.cover_url = data["cover_url"]
    if "release_year" in data:
        movie.release_year = data["release_year"]

    if "genres" in data:
        genres = data["genres"]
        if isinstance(genres, str):
            genres = [g.strip() for g in genres.split(",") if g.strip()]
        movie.genre = ",".join(genres)

        # Replace genre links
        db.query(MovieGenre).filter(MovieGenre.movie_id == movie_id).delete()
        genre_map = {g.name: g.id for g in db.query(Genre).all()}
        for g_name in genres:
            g_name = crud._normalize_genre(g_name)
            g_id = genre_map.get(g_name)
            if g_id:
                db.add(MovieGenre(movie_id=movie_id, genre_id=g_id))

    db.commit()
    db.refresh(movie)
    return {"message": "电影已更新"}


@router.delete("/movies/{movie_id}")
def admin_delete_movie(
    movie_id: int,
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    movie = crud.get_movie_by_id(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")
    db.delete(movie)
    db.commit()
    return {"message": "电影已删除"}


# ── User management ────────────────────────────────────────────

@router.get("/users")
def admin_list_users(
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    return crud.get_all_users(db)


@router.post("/users/action")
def admin_user_action(
    data: schemas.AdminUserAction,
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    target = crud.get_user_by_id(db, data.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="不能操作自己")
    if data.action == "ban":
        crud.set_user_active(db, target, False)
        return {"message": f"用户 {target.username} 已被封禁"}
    elif data.action == "unban":
        crud.set_user_active(db, target, True)
        return {"message": f"用户 {target.username} 已解封"}
    elif data.action == "set_admin":
        target.role = "admin"
        db.commit()
        return {"message": f"用户 {target.username} 已设为管理员"}
    elif data.action == "unset_admin":
        target.role = "user"
        db.commit()
        return {"message": f"用户 {target.username} 已取消管理员"}
    raise HTTPException(status_code=400, detail="无效操作")


# ── Comment management ─────────────────────────────────────────

@router.get("/comments")
def admin_list_comments(
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    from ..routers.comments import _enrich_comment
    return [_enrich_comment(c) for c in crud.get_all_comments(db)]


@router.delete("/comments/{comment_id}")
def admin_delete_comment(
    comment_id: int,
    admin: models.User = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    if not crud.delete_comment(db, comment_id):
        raise HTTPException(status_code=404, detail="评论不存在")
    return {"message": "评论已删除"}
