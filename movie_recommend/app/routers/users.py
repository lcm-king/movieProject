from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, crud, auth, models

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", response_model=schemas.Token)
def register(user_data: schemas.UserRegister, db: Session = Depends(get_db)):
    if crud.get_user_by_username(db, user_data.username):
        raise HTTPException(status_code=400, detail="用户名已存在")
    if crud.get_user_by_email(db, user_data.email):
        raise HTTPException(status_code=400, detail="邮箱已注册")

    # Auto-promote to admin if no admin exists in the system
    is_first_admin = db.query(models.User).filter(models.User.role == "admin").count() == 0
    role = "admin" if is_first_admin else "user"

    genres_str = ",".join(user_data.preferred_genres)
    hashed = auth.hash_password(user_data.password)
    user = crud.create_user(db, user_data.username, user_data.email, hashed, genres_str, role=role)

    token = auth.create_access_token({
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    })
    return schemas.Token(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.post("/login", response_model=schemas.Token)
def login(login_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.get_user_by_username(db, login_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not auth.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被封禁")

    token = auth.create_access_token({
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
    })
    return schemas.Token(
        access_token=token,
        user_id=user.id,
        username=user.username,
        role=user.role,
    )


@router.get("/me", response_model=schemas.UserOut)
def get_profile(current_user: models.User = Depends(auth.get_current_user)):
    return current_user


@router.put("/me/genres", response_model=schemas.UserOut)
def update_genres(
    data: schemas.UserProfileUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    genres_str = ",".join(data.preferred_genres)
    return crud.update_user_genres(db, current_user, genres_str)


@router.get("/", response_model=list[schemas.UserOut])
def list_users(
    current_user: models.User = Depends(auth.get_admin_user),
    db: Session = Depends(get_db),
):
    return crud.get_all_users(db)


@router.post("/claim-admin")
def claim_admin(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db),
):
    """Promote current user to admin if no admin exists in the system."""
    admin_exists = db.query(models.User).filter(models.User.role == "admin").count() > 0
    if admin_exists:
        raise HTTPException(status_code=400, detail="系统中已有管理员，无法自动提升")
    current_user.role = "admin"
    db.commit()
    # Issue a new token with updated role
    token = auth.create_access_token({
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role,
    })
    return schemas.Token(
        access_token=token,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
    )
