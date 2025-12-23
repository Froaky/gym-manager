from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import Payment, Subscription, Plan, User
from datetime import datetime, timedelta

router = APIRouter(prefix="/payments", tags=["payments"])
templates = Jinja2Templates(directory="templates")

@router.get("/select-plan/{user_id}", response_class=HTMLResponse)
async def select_plan_page(user_id: int, request: Request, session: SessionDep):
    user = session.get(User, user_id)
    plans = session.exec(select(Plan)).all()
    return templates.TemplateResponse(
        request=request, 
        name="payments/select_plan.html", 
        context={"user": user, "plans": plans}
    )

@router.post("/process")
async def process_payment(
    session: SessionDep,
    user_id: int = Form(...),
    plan_id: int = Form(...),
    amount: float = Form(...)
):
    # Get Plan details for duration
    plan = session.get(Plan, plan_id)
    
    # Create Payment Record
    payment = Payment(
        user_id=user_id,
        amount=amount,
        method="mock_stripe",
        status="completed"
    )
    session.add(payment)
    
    # Create/Update Subscription
    sub = Subscription(
        user_id=user_id,
        plan_id=plan_id,
        active=True,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=plan.duration_days)
    )
    session.add(sub)
    
    session.commit()
    
    return RedirectResponse(url="/users", status_code=303)
