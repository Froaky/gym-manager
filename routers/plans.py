from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import Plan

from routers.auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/plans", tags=["plans"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def list_plans(
    request: Request, 
    session: SessionDep,
    current_user_id: Optional[str] = Depends(get_current_user)
):
    if not current_user_id:
        return RedirectResponse(url="/auth/login", status_code=303)
    plans = session.exec(select(Plan)).all()
    return templates.TemplateResponse(
        request=request, 
        name="plans/list.html", 
        context={"plans": plans}
    )

@router.get("/new", response_class=HTMLResponse)
async def new_plan_form(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="plans/form.html", 
        context={}
    )

@router.post("/new")
async def create_plan(
    session: SessionDep,
    name: str = Form(...),
    price: float = Form(...),
    duration_days: int = Form(...),
    description: str = Form(None)
):
    plan = Plan(name=name, price=price, duration_days=duration_days, description=description)
    session.add(plan)
    session.commit()
    return RedirectResponse(url="/plans", status_code=303)

@router.post("/delete/{plan_id}")
async def delete_plan(
    plan_id: int,
    session: SessionDep
):
    plan = session.get(Plan, plan_id)
    if plan:
        session.delete(plan)
        session.commit()
    return RedirectResponse(url="/plans", status_code=303)
