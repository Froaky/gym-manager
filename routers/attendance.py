from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import User, Attendance
from datetime import datetime

router = APIRouter(tags=["attendance"])
templates = Jinja2Templates(directory="templates")

@router.get("/scan", response_class=HTMLResponse)
async def scan_page(request: Request):
    return templates.TemplateResponse(
        request=request, 
        name="scan.html", 
        context={}
    )

@router.post("/attendance/checkin")
async def checkin(
    session: SessionDep,
    qr_code: str = Form(...)
):
    # Find user by QR code
    statement = select(User).where(User.qr_code_data == qr_code)
    user = session.exec(statement).first()
    
    if not user:
        return JSONResponse(
            status_code=404, 
            content={"status": "error", "message": "Usuario no encontrado"}
        )

    # Record attendance
    attendance = Attendance(user_id=user.id)
    session.add(attendance)
    session.commit()
    
    return JSONResponse(
        content={
            "status": "success", 
            "message": f"Bienvenido, {user.name}!",
            "time": datetime.now().strftime("%H:%M")
        }
    )
