from fastapi import APIRouter, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import User
from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

# Setup Security
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key-change-me")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 300))
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@gym.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

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

# Dependency to get the current authenticated user object
async def get_current_user(request: Request, session: SessionDep):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            return None
        return session.get(User, user_id)
    except Exception:
        return None

# Combined dependency for admin access
async def admin_required(user: Optional[User] = Depends(get_current_user)):
    if not user or user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return user

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
    current_user: Optional[User] = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
        
    if new_password != confirm_password:
        return templates.TemplateResponse(
            request=request, 
            name="auth/change_password.html", 
            context={"error": "Las contraseñas no coinciden"}
        )
        
    current_user.hashed_password = get_password_hash(new_password)
    current_user.must_change_password = False
    session.add(current_user)
    session.commit()
    
    return RedirectResponse(url="/", status_code=303)

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response

# Helper to inject initial admin
def create_initial_admin(session: Session):
    user = session.exec(select(User).where(User.email == ADMIN_EMAIL)).first()
    if not user:
        admin = User(
            name="Super Admin",
            email=ADMIN_EMAIL,
            role="admin",
            hashed_password=get_password_hash(ADMIN_PASSWORD), 
            qr_code_data="admin-qr"
        )
        session.add(admin)
        session.commit()
