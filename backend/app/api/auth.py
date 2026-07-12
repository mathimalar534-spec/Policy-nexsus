from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.repositories.repositories import UserRepository
from app.schemas.schemas import Token, UserResponse, UserCreate
from app.middleware.auth import verify_password, get_password_hash, create_access_token, get_current_user
from app.models.models import User, Role

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = UserRepository.get_by_username(db, user_in.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    existing_email = UserRepository.get_by_email(db, user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Resolve role or create
    role = UserRepository.create_role_if_not_exists(db, user_in.role_name)

    user_data = {
        "username": user_in.username,
        "email": user_in.email,
        "hashed_password": get_password_hash(user_in.password),
        "role_id": role.id,
        "is_active": True
    }
    user = UserRepository.create(db, user_data)
    
    # Format response
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role_name=role.name,
        is_active=user.is_active,
        created_at=user.created_at
    )

@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = UserRepository.get_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    role = UserRepository.get_role_by_id(db, user.role_id)
    role_name = role.name if role else "Viewer"

    access_token = create_access_token(
        data={"sub": user.username, "role": role_name}
    )
    return Token(access_token=access_token, token_type="bearer")

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = UserRepository.get_role_by_id(db, current_user.role_id)
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role_name=role.name if role else "Viewer",
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )
