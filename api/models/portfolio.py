from datetime import datetime
import json
import os
from posixpath import splitext
from typing import Annotated, List, Optional
import uuid
from fastapi import Form, UploadFile
from pydantic import TypeAdapter
from sqlalchemy import UUID, Column, ForeignKey, func
from sqlmodel import Field, SQLModel, Session, select
from api.config import get_config
from api.core.error import APIError
from api.models.quiz.model import WorkUnit
from api.models.utils import Image, ImageBase
from api.utils.faky import Faky


class PortfolioImage(Image, table=True):
    __tablename__ = "external_portfolio_images"

    portfolio_project_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("external_portfolio_projects.id", initially="DEFERRED", deferrable=True),
            nullable=False,
        )
    )

    @staticmethod
    def get_many(pid: uuid.UUID, db: Session):
        query = select(PortfolioImage).where(PortfolioImage.id == pid)
        images = db.exec(query).all()
        return images

    @staticmethod
    def upload_dir():
        upload_dir = "img/portfolio"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        return upload_dir

    @staticmethod
    def store(pid: uuid.UUID, files, captions: List[str], db: Session):
        imgs: list[PortfolioImage] = []
        upload_dir = PortfolioImage.upload_dir()
        for idx, file in enumerate(files):
            ptf_img_id = uuid.uuid4()
            img_extension = splitext(file.filename)[1]
            ptf_img_id = str(ptf_img_id).replace("-", "")
            img_path = os.path.join(upload_dir, f"{ptf_img_id}{img_extension}")
            with open(img_path, "wb") as img_file:
                img_file.write(file.file.read())
            imgs.append(
                PortfolioImage(
                    id=ptf_img_id,
                    created_at=datetime.utcnow(),
                    portfolio_project_id=pid,
                    caption=captions[idx],
                    uri=f"{get_config().ROOT_PATH}/{img_path}",  # change this to not include img_extension
                )
            )
        db.add_all(imgs)


class PortfolioProjectTask(SQLModel, table=True):
    __tablename__ = "external_portfolio_project_units"
    work_unit_id: int = Field(foreign_key="work_units.id", primary_key=True)
    portfolio_project_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("external_portfolio_projects.id", initially="DEFERRED", deferrable=True),
            primary_key=True,
        )
    )


class PortfolioProjectCreate(SQLModel):
    title: str
    zipcode: str
    captions: List[str]
    description: str
    units: List[int]

    @staticmethod
    def from_form(
        portfolio: Annotated[str, Form()],
    ):
        try:
            json_raw = json.loads(portfolio)
            title = json_raw.get("title", None)
            zipcode = json_raw.get("zipcode", None)
            description = json_raw.get("description", None)
            captions = json_raw.get("captions", [])
            units = json_raw.get("units", [])
            return PortfolioProjectCreate(
                title=title,
                zipcode=zipcode,
                captions=captions,
                units=units,
                description=description,
            )
        except Exception as e:
            raise APIError.PortfolioValidationException(e)

    @staticmethod
    def mock(faky: Faky, unit_count: int, caption_count: int):
        units = faky.unit_sample(unit_count)
        captions = [faky.fake.word() for _ in range(caption_count)]
        return PortfolioProjectCreate(
            title=faky.fake.word(),
            zipcode=faky.fake.postcode(),
            units=units,
            captions=captions,
            description=faky.fake.word(),
        )


class ExternalPortfolioProject(SQLModel, table=True):
    __tablename__ = "external_portfolio_projects"

    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    contractor_id: uuid.UUID = Field(foreign_key="contractors.id")
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    title: str = Field(nullable=False)
    description: str = Field(nullable=True)
    zipcode: str = Field(nullable=True)

    @staticmethod
    def create(
        portfolio: PortfolioProjectCreate,
        cid: uuid.UUID,
        files: list[UploadFile],
        db: Session,
    ):
        model = ExternalPortfolioProject(
            contractor_id=cid,
            title=portfolio.title,
            zipcode=portfolio.zipcode,
            description=portfolio.description,
        )
        db.add(model)
        PortfolioImage.store(model.id, files, portfolio.captions, db)
        units = [
            PortfolioProjectTask(work_unit_id=unit, portfolio_project_id=model.id)
            for unit in portfolio.units
        ]
        db.add_all(units)
        return len(files)

    @staticmethod
    def by_cid_and_bid(cid: uuid.UUID, bid: uuid.UUID, db: Session):
        query = (
            select(
                ExternalPortfolioProject,
                func.json_agg(
                    func.json_build_object("work_unit_id", PortfolioProjectTask.work_unit_id)
                ),
                func.json_agg(
                    func.json_build_object(
                        "uri",
                        PortfolioImage.uri,
                        "caption",
                        PortfolioImage.caption,
                        "timestamp",
                        PortfolioImage.created_at,
                    )
                ),
            )
            .where(
                ExternalPortfolioProject.contractor_id == cid,
                ExternalPortfolioProject.id == bid,
            )
            .outerjoin(
                PortfolioProjectTask,
                ExternalPortfolioProject.id == PortfolioProjectTask.portfolio_project_id,
            )
            .outerjoin(
                PortfolioImage,
                ExternalPortfolioProject.id == PortfolioImage.portfolio_project_id,
            )
            .group_by(ExternalPortfolioProject.id, PortfolioImage.uri)
        )
        projects = db.exec(query).first()
        return projects

    @staticmethod
    def by_cid(cid: uuid.UUID, db: Session):
        query = select(
            ExternalPortfolioProject.id,
            ExternalPortfolioProject.title,
            ExternalPortfolioProject.created_at,
        ).where(ExternalPortfolioProject.contractor_id == cid)
        models = db.execute(query).all()
        return models


class PortfolioExternalProjectView(SQLModel):
    id: Optional[uuid.UUID]
    title: str
    units: List[str] | None = None
    images: List[ImageBase] | None = None

    @staticmethod
    def create(
        ptf: ExternalPortfolioProject,
        units,
        images,
        db: Session,
    ):
        if images:
            ta = TypeAdapter(list[ImageBase])
            imgs = ta.validate_python(images)
        if units:
            work_units = WorkUnit.by_ids(
                list(map(lambda unit: unit.get("work_unit_id", None), units)), db
            )
            work_units = [unit[0].concat() for unit in work_units]
        return PortfolioExternalProjectView(
            id=ptf.id, title=ptf.title, images=imgs, units=work_units
        )
