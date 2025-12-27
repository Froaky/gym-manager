from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from database import create_db_and_tables, engine
from sqlmodel import Session
from routers import auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    with Session(engine) as session:
        auth.create_initial_admin(session)
    yield

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

from routers import users
app.include_router(users.router)
from routers import attendance
app.include_router(attendance.router)
from routers import payments
app.include_router(payments.router)
from routers import plans
app.include_router(plans.router)
from routers import routines
app.include_router(routines.router)
app.include_router(auth.router)

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from typing import Optional
from database import SessionDep
from models import User, Payment, Attendance
from routers import auth

@app.get("/", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    session: SessionDep,
    current_user: Optional[User] = Depends(auth.get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)
        
    user = session.get(User, current_user.id)
    if not user:
        return RedirectResponse(url="/auth/login", status_code=303)
        
    # Client View
    if user.role == "client":
        return templates.TemplateResponse(
            request=request, 
            name="client_dashboard.html", 
            context={"user": user, "now": datetime.utcnow()}
        )
        
    # Admin/Staff View (Calculate Stats)
    from sqlmodel import select, func

    # 1. Active Users (clients with an active subscription)
    # For now, let's just count all clients as a simple baseline
    active_users = len(session.exec(select(User).where(User.role == "client")).all()) 

    # 2. Monthly Revenue
    try:
        first_day_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        revenue_query = select(func.sum(Payment.amount)).where(Payment.date >= first_day_month)
        revenue = session.exec(revenue_query).one() or 0
    except Exception as e:
        print(f"Error calculating revenue: {e}")
        revenue = 0
    
    # 3. Today's Attendance
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        attendance_query = select(func.count(Attendance.id)).where(Attendance.check_in_time >= today_start)
        attendance = session.exec(attendance_query).one() or 0
    except Exception as e:
        print(f"Error calculating attendance: {e}")
        attendance = 0

    # Calculate Trends
    # Active Users Growth
    try:
        # Simple approximation: Compare with total users created before this month
        # In a real app with history, we'd query active subscriptions at a point in time
        first_day_current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        users_this_month = session.exec(select(func.count(User.id)).where(User.created_at >= first_day_current_month)).one() or 0
        total_users_prev_month = active_users - users_this_month
        
        if total_users_prev_month > 0:
            active_users_growth = int((users_this_month / total_users_prev_month) * 100)
        else:
            active_users_growth = 100 if users_this_month > 0 else 0
    except:
        active_users_growth = 0

    # Revenue Growth
    try:
        current_month_revenue = revenue
        
        # Last Month Revenue
        last_month = first_day_current_month - timedelta(days=1)
        first_day_last_month = last_month.replace(day=1)
        
        prev_rev_query = select(func.sum(Payment.amount)).where(
            Payment.date >= first_day_last_month, 
            Payment.date < first_day_current_month
        )
        prev_revenue = session.exec(prev_rev_query).one() or 0
        
        if prev_revenue > 0:
            revenue_growth = int(((current_month_revenue - prev_revenue) / prev_revenue) * 100)
        else:
            revenue_growth = 100 if current_month_revenue > 0 else 0
    except Exception as e:
        print(f"Error calculating revenue growth: {e}")
        revenue_growth = 0
    
    # 4. Last 7 Days Revenue (for Chart)
    days = []
    daily_revenue = []
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    for i in range(6, -1, -1):
        day_date = today - timedelta(days=i)
        next_day = day_date + timedelta(days=1)
        
        day_label = day_date.strftime('%a') # Mon, Tue...
        rev_query = select(func.sum(Payment.amount)).where(Payment.date >= day_date, Payment.date < next_day)
        rev = session.exec(rev_query).one() or 0
        
        days.append(day_label)
        daily_revenue.append(float(rev))

    return templates.TemplateResponse(
        request=request, 
        name="dashboard.html", 
        context={
            "user": user,
            "active_users_count": active_users,
            "monthly_revenue": float(revenue),
            "today_attendance": attendance,
            "chart_labels": days,
            "chart_data": daily_revenue,
            "active_users_growth": active_users_growth,
            "revenue_growth": revenue_growth
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
