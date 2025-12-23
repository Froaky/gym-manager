from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import User
import uuid

from routers.auth import get_current_user, get_password_hash
from typing import Optional

router = APIRouter(prefix="/users", tags=["users"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def list_users(
    request: Request, 
    session: SessionDep,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    if not current_user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    users = session.exec(select(User)).all()
    from datetime import datetime
    return templates.TemplateResponse(
        request=request, 
        name="users/list.html", 
        context={"users": users, "now": datetime.utcnow()}
    )

@router.get("/new", response_class=HTMLResponse)
async def new_user_form(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="users/form.html", 
        context={}
    )

@router.post("/new")
async def create_user(
    session: SessionDep,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    current_user_id: Optional[str] = Depends(get_current_user)
):
    if not current_user_id:
       return RedirectResponse(url="/auth/login", status_code=303)
    
    # Generate a unique QR code identifier for the user
    qr_code = str(uuid.uuid4())
    hashed_pwd = get_password_hash(password)
    
    user = User(name=name, email=email, qr_code_data=qr_code, hashed_password=hashed_pwd, must_change_password=True)
    session.add(user)
    session.commit()
    session.refresh(user)
    return RedirectResponse(url="/users", status_code=303)

@router.get("/{user_id}", response_class=HTMLResponse)
async def user_detail(
    request: Request,
    user_id: int,
    session: SessionDep,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    if not current_user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
        
    user = session.get(User, user_id)
    if not user:
        return RedirectResponse(url="/users", status_code=303)
    
    from datetime import datetime
    return templates.TemplateResponse(
        request=request,
        name="users/profile.html",
        context={"user": user, "now": datetime.utcnow()}
    )
