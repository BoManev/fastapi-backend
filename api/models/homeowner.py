from datetime import datetime
import os
from posixpath import splitext
import uuid
from typing import Annotated, List, Optional, Tuple
from fastapi import Form
from pydantic import EmailStr, SecretStr
import requests
from sqlalchemy import UUID, CheckConstraint
from sqlmodel import Field, SQLModel, Column, ForeignKey, Session, select
from api.config import get_config
from api.models.user import User, UserCreate, UserRole
from api.utils.faky import Faky


class HomeownerBase(SQLModel):
    first_name: str = Field(nullable=False)
    last_name: str = Field(nullable=False)


class HomeownerCreate(UserCreate, HomeownerBase):
    @staticmethod
    def from_form(
        first_name: Annotated[str, Form()],
        last_name: Annotated[str, Form()],
        phone_number: Annotated[str, Form()],
        password: Annotated[SecretStr, Form()],
        email: Annotated[EmailStr, Form()],
    ):
        return HomeownerCreate(
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            password=password,
            email=email,
        )

    @staticmethod
    def mock(faky: Faky, password: str):
        return HomeownerCreate(
            first_name=faky.fake.first_name(),
            last_name=faky.fake.last_name(),
            email=faky.fake.email(),
            phone_number=faky.fake.phone_number(),
            password=SecretStr(password),
        )


class Homeowner(HomeownerBase, table=True):
    __tablename__ = "homeowners"

    id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("users.id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )
    avatar_uri: Optional[str] = Field(nullable=True, default=None)
    rating: int = Field(
        nullable=False,
        default=0,
        sa_column_args=(
            CheckConstraint(
                "quality_rating >= 0 AND quality_rating <= 5",
                name="quality_rating_out_of_range",
            )
        ),
    )

    @staticmethod
    def by_hid(hid: uuid.UUID, db: Session):
        query = select(Homeowner).where(Homeowner.id == hid)
        homeowner = db.exec(query).first()
        return homeowner

    @staticmethod
    def by_email(email: str, db: Session):
        query = (
            select(Homeowner)
            .join(User, User.id == Homeowner.id)
            .where(User.email == email)
        )
        homeowner = db.exec(query).first()
        return homeowner

    @staticmethod
    def create(homeowner: HomeownerCreate, db: Session, avatar=None):
        id = uuid.uuid4()
        user = User(
            id=id,
            phone_number=homeowner.phone_number,
            email=homeowner.email,
            password=homeowner.password.get_secret_value(),
            role=UserRole.Homeowner,
        )
        upload_folder = "img/homeowner/"
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        if avatar:
            img_extension = splitext(avatar.filename)[1]
            avatar_img_id = str(id).replace("-", "")
            img_path = os.path.join(upload_folder, f"{avatar_img_id}{img_extension}")
            with open(img_path, "wb") as img_file:
                img_file.write(avatar.file.read())
            avatar_uri = f"{get_config().ROOT_PATH}/{img_path}"
        else:
            try:
                external_api_url = f"https://ui-avatars.com/api/?background=7D8790&color=ffffff&name={homeowner.first_name[0]}+{homeowner.last_name[0]}"
                response = requests.get(external_api_url)
                response.raise_for_status()
                img_extension = ".png"
                avatar_img_id = str(id).replace("-", "")
                img_path = os.path.join(
                    upload_folder, f"{avatar_img_id}{img_extension}"
                )
                with open(img_path, "wb") as img_file:
                    img_file.write(response.content)
                avatar_uri = f"{get_config().ROOT_PATH}/{img_path}"
            except:
                avatar_uri = None
        db.add(user)
        hw = Homeowner(
            id=user.id,
            first_name=homeowner.first_name,
            last_name=homeowner.last_name,
            avatar_uri=avatar_uri,
        )
        db.add(hw)
        return hw, user


class HomeownerPublicView(HomeownerBase):
    id: uuid.UUID
    avatar_uri: str | None = None
    rating: int

    @staticmethod
    def create(homeowner: Homeowner):
        return HomeownerPublicView(**homeowner.model_dump())


class HomeownerPrivateView(HomeownerBase):
    """
    field (past_projects):
    - Array<(project_id, title, created_at)>
    """

    id: uuid.UUID
    email: EmailStr
    phone_number: str
    avatar_uri: str | None = None
    rating: int
    past_projects: List[Tuple[uuid.UUID, str, datetime]]
