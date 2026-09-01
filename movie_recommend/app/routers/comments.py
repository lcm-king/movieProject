from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, crud, auth, models

router = APIRouter(prefix="/api/comments", tags=["comments"])


@router.post("/", response_model=schemas.CommentOut)
def post_comment(
    data: schemas.CommentCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    movie = crud.get_movie_by_id(db, data.movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="电影不存在")
    comment = crud.create_comment(db, current_user.id, data.movie_id, data.content)
    return _enrich_comment(comment)


@router.get("/movie/{movie_id}", response_model=list[schemas.CommentOut])
def get_movie_comments(movie_id: int, db: Session = Depends(get_db)):
    comments = crud.get_movie_comments(db, movie_id)
    return [_enrich_comment(c) for c in comments]


@router.delete("/{comment_id}")
def delete_comment(
    comment_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    comment = crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="评论不存在")
    # 管理员可以删除任意评论，普通用户只能删除自己的
    if current_user.role != "admin" and comment.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限删除此评论")
    crud.delete_comment(db, comment_id)
    return {"message": "评论已删除"}


@router.get("/admin/all", response_model=list[schemas.CommentOut])
def admin_get_all_comments(
    current_user: models.User = Depends(auth.get_admin_user),
    db: Session = Depends(get_db),
):
    comments = crud.get_all_comments(db)
    return [_enrich_comment(c) for c in comments]


def _enrich_comment(comment: models.Comment) -> schemas.CommentOut:
    """Add username to comment output."""
    return schemas.CommentOut(
        id=comment.id,
        user_id=comment.user_id,
        movie_id=comment.movie_id,
        username=comment.user.username if comment.user else None,
        content=comment.content,
        sentiment=comment.sentiment,
        created_at=comment.created_at,
    )
