from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import Plan

from routers.auth import get_current_user, admin_required
from typing import Optional

router = APIRouter(prefix="/plans", tags=["plans"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def list_plans(
    request: Request, 
    session: SessionDep,
    current_user: dict = Depends(admin_required)
):
    plans = session.exec(select(Plan)).all()
    return templates.TemplateResponse(
        request=request, 
        name="plans/list.html", 
        context={"plans": plans, "user": current_user}
    )

@router.get("/new", response_class=HTMLResponse)
async def new_plan_form(
    request: Request,
    current_user: dict = Depends(admin_required)
):
    return templates.TemplateResponse(
        request=request, 
        name="plans/form.html", 
        context={"user": current_user}
    )

@router.post("/new")
async def create_plan(
    session: SessionDep,
    name: str = Form(...),
    price: float = Form(...),
    duration_days: int = Form(...),
    description: str = Form(None),
    current_user: dict = Depends(admin_required)
):
    plan = Plan(name=name, price=price, duration_days=duration_days, description=description)
    session.add(plan)
    session.commit()
    return RedirectResponse(url="/plans", status_code=303)

@router.post("/delete/{plan_id}")
async def delete_plan(
    plan_id: int,
    session: SessionDep,
    current_user: dict = Depends(admin_required)
):
    plan = session.get(Plan, plan_id)
    if plan:
        session.delete(plan)
        session.commit()
    return RedirectResponse(url="/plans", status_code=303)

@router.get("/edit/{plan_id}", response_class=HTMLResponse)
async def edit_plan_form(
    plan_id: int,
    request: Request,
    session: SessionDep,
    current_user: dict = Depends(admin_required)
):
    plan = session.get(Plan, plan_id)
    if not plan:
        return RedirectResponse(url="/plans", status_code=303)
    return templates.TemplateResponse(
        request=request,
        name="plans/edit.html",
        context={"plan": plan, "user": current_user}
    )

@router.post("/edit/{plan_id}")
async def update_plan(
    plan_id: int,
    session: SessionDep,
    name: str = Form(...),
    price: float = Form(...),
    duration_days: int = Form(...),
    description: str = Form(None),
    current_user: dict = Depends(admin_required)
):
    plan = session.get(Plan, plan_id)
    if plan:
        plan.name = name
        plan.price = price
        plan.duration_days = duration_days
        plan.description = description
        session.add(plan)
        session.commit()
    return RedirectResponse(url="/plans", status_code=303)
