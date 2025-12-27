from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class UserBase(SQLModel):
    name: str = Field(index=True)
    email: str = Field(unique=True, index=True)
    role: str = Field(default="client")  # client, admin, staff
    hashed_password: Optional[str] = None
    must_change_password: bool = Field(default=False)
    qr_code_data: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserRoutine(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    routine_id: int = Field(foreign_key="routine.id", primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subscriptions: List["Subscription"] = Relationship(back_populates="user")
    payments: List["Payment"] = Relationship(back_populates="user")
    attendances: List["Attendance"] = Relationship(back_populates="user")
    routines: List["Routine"] = Relationship(back_populates="users", link_model=UserRoutine)

class PlanBase(SQLModel):
    name: str
    price: float
    duration_days: int
    description: Optional[str] = None

class Plan(PlanBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    subscriptions: List["Subscription"] = Relationship(back_populates="plan")

class SubscriptionBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    plan_id: int = Field(foreign_key="plan.id")
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: datetime
    active: bool = True

class Subscription(SubscriptionBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user: User = Relationship(back_populates="subscriptions")
    plan: Plan = Relationship(back_populates="subscriptions")

class PaymentBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    amount: float
    date: datetime = Field(default_factory=datetime.utcnow)
    method: str  # stripe, mercadopago, cash
    status: str = "completed"

class Payment(PaymentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user: User = Relationship(back_populates="payments")

class AttendanceBase(SQLModel):
    user_id: int = Field(foreign_key="user.id")
    check_in_time: datetime = Field(default_factory=datetime.utcnow)

class Attendance(AttendanceBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user: User = Relationship(back_populates="attendances")


class RoutineBase(SQLModel):
    name: str  # e.g. "Hypertrophy Push/Pull"
    description: Optional[str] = None
    frequency: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Routine(RoutineBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    exercises: List["Exercise"] = Relationship(back_populates="routine")
    users: List["User"] = Relationship(back_populates="routines", link_model=UserRoutine)

class ExerciseBase(SQLModel):
    routine_id: int = Field(foreign_key="routine.id")
    name: str
    sets: int
    reps: str
    weight: Optional[str] = None
    notes: Optional[str] = None

class Exercise(ExerciseBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    routine: Routine = Relationship(back_populates="exercises")
