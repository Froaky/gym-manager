from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from database import SessionDep
from models import Routine, Exercise, User

from routers.auth import get_current_user, admin_required
from typing import Optional

router = APIRouter(prefix="/routines", tags=["routines"])
templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
async def list_routines(
    request: Request, 
    session: SessionDep,
    current_user: dict = Depends(admin_required)
):
    routines = session.exec(select(Routine)).all()
    return templates.TemplateResponse(
        request=request, 
        name="routines/list.html", 
        context={"routines": routines, "user": current_user}
    )

@router.get("/user/{user_id}", response_class=HTMLResponse)
async def list_user_routines(
    user_id: int, 
    request: Request, 
    session: SessionDep,
    current_user: dict = Depends(admin_required)
):
    user = session.get(User, user_id)
    all_routines = session.exec(select(Routine)).all()
    return templates.TemplateResponse(
        request=request, 
        name="routines/user_list.html", 
        context={"target_user": user, "routines": user.routines, "all_routines": all_routines, "user": current_user}
    )

@router.post("/new")
async def create_routine(
    session: SessionDep,
    name: str = Form(...),
    description: str = Form(None),
    current_user: dict = Depends(admin_required)
):
    routine = Routine(name=name, description=description)
    session.add(routine)
    session.commit()
    return RedirectResponse(url="/routines", status_code=303)

@router.post("/assign")
async def assign_routine(
    session: SessionDep,
    user_id: int = Form(...),
    routine_id: int = Form(...),
    current_user: dict = Depends(admin_required)
):
    from models import UserRoutine
    user_routine = UserRoutine(user_id=user_id, routine_id=routine_id)
    session.add(user_routine)
    session.commit()
    return RedirectResponse(url=f"/routines/user/{user_id}", status_code=303)

@router.post("/unassign")
async def unassign_routine(
    session: SessionDep,
    user_id: int = Form(...),
    routine_id: int = Form(...),
    current_user: dict = Depends(admin_required)
):
    from models import UserRoutine
    user_routine = session.get(UserRoutine, (user_id, routine_id))
    if user_routine:
        session.delete(user_routine)
        session.commit()
    return RedirectResponse(url=f"/routines/user/{user_id}", status_code=303)

@router.get("/{routine_id}", response_class=HTMLResponse)
async def view_routine(
    routine_id: int, 
    request: Request, 
    session: SessionDep,
    current_user: dict = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse(url="/auth/login", status_code=303)

    routine = session.get(Routine, routine_id)
    if not routine:
        return RedirectResponse(url="/routines", status_code=303)
    
    # Check permissions
    is_admin = current_user.role == "admin"
    is_owner = False
    
    # Check if user owns the routine (if not admin)
    if not is_admin:
        for r in current_user.routines:
            if r.id == routine.id:
                is_owner = True
                break
    
    if not is_admin and not is_owner:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request, 
        name="routines/detail.html", 
        context={"routine": routine, "user": current_user}
    )

@router.post("/{routine_id}/add-exercise")
async def add_exercise(
    session: SessionDep,
    routine_id: int,
    name: str = Form(...),
    sets: int = Form(...),
    reps: str = Form(...),
    weight: str = Form(None),
    notes: str = Form(None),
    current_user: dict = Depends(admin_required)
):
    exercise = Exercise(
        routine_id=routine_id,
        name=name,
        sets=sets,
        reps=reps,
        weight=weight,
        notes=notes
    )
    session.add(exercise)
    session.commit()
    return RedirectResponse(url=f"/routines/{routine_id}", status_code=303)

@router.post("/delete/{routine_id}")
async def delete_routine(
    routine_id: int,
    session: SessionDep,
    current_user: dict = Depends(admin_required)
):
    routine = session.get(Routine, routine_id)
    if routine:
        session.delete(routine)
        session.commit()
    return RedirectResponse(url="/routines", status_code=303)
