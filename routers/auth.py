from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import User
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from typing import Optional

# Setup Security
SECRET_KEY = "super-secret-key-change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 300

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Dependency to populate user in Request (Middleware-like)
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        return user_id
    except jwt.PyJWTError:
        return None

# Routes
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth/login.html", context={})

@router.post("/login")
async def login(
    request: Request,
    session: SessionDep,
    email: str = Form(...),
    password: str = Form(...)
):
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    
    if not user or not user.hashed_password or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request, 
            name="auth/login.html", 
            context={"error": "Credenciales inválidas"}
        )
    
    # Create Token
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    
    # Redirect based on must_change_password
    if user.must_change_password:
        response = RedirectResponse(url="/auth/change-password", status_code=303)
    else:
        response = RedirectResponse(url="/", status_code=303)
        
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@router.get("/change-password", response_class=HTMLResponse)
async def change_password_page(request: Request):
    return templates.TemplateResponse(request=request, name="auth/change_password.html", context={})

@router.post("/change-password")
async def change_password(
    request: Request,
    session: SessionDep,
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    current_user_id: Optional[str] = Depends(get_current_user)
):
    if not current_user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
        
    if new_password != confirm_password:
        return templates.TemplateResponse(
            request=request, 
            name="auth/change_password.html", 
            context={"error": "Las contraseñas no coinciden"}
        )
        
    user = session.get(User, current_user_id)
    user.hashed_password = get_password_hash(new_password)
    user.must_change_password = False
    session.add(user)
    session.commit()
    
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response

# Helper to inject initial admin
def create_initial_admin(session: Session):
    user = session.exec(select(User).where(User.email == "admin@gym.com")).first()
    if not user:
        admin = User(
            name="Super Admin",
            email="admin@gym.com",
            role="admin",
            hashed_password=get_password_hash("admin123"), # Default password
            qr_code_data="admin-qr"
        )
        session.add(admin)
        session.commit()
