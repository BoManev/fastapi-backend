import enum
from typing import Optional
import uuid
from sqlmodel import SQLModel, Field, CheckConstraint, Session, select
from pydantic import EmailStr, BaseModel, SecretStr
from api.core.utils import HashedPassword


class UserRole(str, enum.Enum):
    Contractor = "contractor"
    Homeowner = "homeowner"


class UserBase(SQLModel):
    email: EmailStr = Field(primary_key=True)
    phone_number: str = Field(
        sa_column_args=(
            CheckConstraint(
                "/^\s*(?:\+?(\d{1,3}))?[-. (]*(\d{3})[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$/",
                "invalid_phone_number",
            )
        ),
        nullable=False,
        unique=True,
    )


class UserCreate(UserBase):
    password: SecretStr


class UserCreateView(SQLModel):
    id: uuid.UUID


class User(UserBase, table=True):
    __tablename__ = "users"
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, unique=True)
    password: HashedPassword = Field(nullable=False)
    admin: Optional[bool] = Field(default=False)
    role: UserRole = Field(nullable=False)

    @staticmethod
    def by_id(id: uuid.UUID, db: Session):
        query = select(User).where(User.id == id)
        user = db.exec(query).first()
        return user

    @staticmethod
    def by_email(email: str, db: Session):
        query = select(User).where(User.email == email)
        user = db.exec(query).first()
        return user

    @staticmethod
    def create(user: UserCreate, db: Session):
        password = user.password.get_secret_value()
        usr = user.model_dump()
        usr.pop("password")
        db.add(User(password=password, **usr))
        return usr


class UserPasswordPatch(BaseModel):
    old_password: str
    new_password: str
