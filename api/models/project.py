from datetime import datetime
import os
from posixpath import splitext
from typing import List, Optional
import uuid
from pydantic import TypeAdapter
from sqlalchemy import (
    UUID,
    ForeignKey,
    and_,
    func,
)
from sqlmodel import SQLModel, Field, Column, Session, select
from api.config import get_config
from api.models.booking import (
    BookingDetail,
    BookingDetailViewBase,
    BookingImage,
    BookingUnitView,
    HomeownerBookingItem,
    BookingUnit,
)
from api.models.contractor import (
    Contractor,
    ContractorPublicView,
)
from api.models.homeowner import Homeowner, HomeownerPublicView
from api.models.quiz.model import WorkUnit
from api.models.utils import Image, ImageBase


class ProjectBase(SQLModel):
    booking_id: uuid.UUID = Field(
        foreign_key="bookings.id", nullable=False, primary_key=True
    )
    contractor_id: uuid.UUID = Field(foreign_key="contractors.id", nullable=False)


class ProjectCreate(ProjectBase):
    pass


class ProjectImage(Image, table=True):
    __tablename__ = "project_images"

    booking_id: uuid.UUID = Field(
        sa_column=Column(
            UUID(as_uuid=True),
            ForeignKey("projects.booking_id", initially="DEFERRED", deferrable=True),
            nullable=False,
        )
    )

    @staticmethod
    def get_many(pid: uuid.UUID, db: Session):
        query = select(ProjectImage).where(ProjectImage.booking_id == pid)
        images = db.exec(query).all()
        return images

    @staticmethod
    def upload_dir():
        upload_dir = "img/project"
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
        return upload_dir

    @staticmethod
    def store(pid: uuid.UUID, files, captions: List[str], db: Session):
        imgs: list[ProjectImage] = []
        upload_dir = ProjectImage.upload_dir()
        for idx, file in enumerate(files):
            ptf_img_id = uuid.uuid4()
            img_extension = splitext(file.filename)[1]
            ptf_img_id = str(ptf_img_id).replace("-", "")
            img_path = os.path.join(upload_dir, f"{ptf_img_id}{img_extension}")
            with open(img_path, "wb") as img_file:
                img_file.write(file.file.read())
            imgs.append(
                ProjectImage(
                    id=ptf_img_id,
                    booking_id=pid,
                    caption=captions[idx],
                    uri=f"{get_config().ROOT_PATH}/{img_path}",  # change this to not include img_extension
                )
            )
        db.add_all(imgs)


class Project(ProjectBase, table=True):
    __tablename__ = "projects"
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    completed_at: datetime = Field(nullable=True)
    signal_completion: Optional[bool] = Field(default=False)
    is_public: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=True, nullable=False)

    @staticmethod
    def create(project: ProjectCreate, db: Session):
        model = Project(**project.model_dump())
        db.add(model)
        return model

    @staticmethod
    def list_by_hid(hid: uuid.UUID, db: Session):
        query = (
            select(
                BookingDetail.id,
                BookingDetail.title,
                Project.booking_id,
                Project.created_at,
                Contractor.avatar_uri,
                Contractor.first_name,
                Contractor.last_name,
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "work_unit_id",
                        BookingUnit.work_unit_id,
                        "description",
                        BookingUnit.description,
                        "quantity",
                        BookingUnit.quantity,
                        "work_unit",
                        func.concat(
                            WorkUnit.area,
                            ":",
                            WorkUnit.location,
                            ":",
                            WorkUnit.category,
                            ":",
                            WorkUnit.subcategory,
                            ":",
                            WorkUnit.action,
                        ),
                    ).distinct()
                ),
            )
            .where(
                and_(BookingDetail.is_booked == True, BookingDetail.homeowner_id == hid)
            )
            .join(
                Project,
                and_(
                    Project.booking_id == BookingDetail.id,
                    Project.is_active == True,
                ),
            )
            .join(Contractor, Contractor.id == Project.contractor_id)
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .group_by(BookingDetail, Project, Contractor)
        )
        models = db.execute(query).all()
        return models

    @staticmethod
    def past_projects_by_hid(hid: uuid.UUID, db: Session):
        query = (
            select(BookingDetail.title, BookingDetail.created_at, Project.booking_id)
            .where(
                and_(
                    BookingDetail.homeowner_id == hid, BookingDetail.is_active == False
                )
            )
            .join(
                Project,
                and_(
                    Project.booking_id == BookingDetail.id, Project.is_active == False
                ),
            )
        )
        models = db.execute(query).all()
        return models

    @staticmethod
    def list_by_cid(cid: uuid.UUID, db: Session):
        query = (
            select(
                Project.booking_id,
                Project.created_at,
                BookingDetail.title,
                Homeowner.avatar_uri,
                Homeowner.first_name,
                Homeowner.last_name,
                func.jsonb_agg(
                    func.jsonb_build_object(
                        "work_unit_id",
                        BookingUnit.work_unit_id,
                        "description",
                        BookingUnit.description,
                        "quantity",
                        BookingUnit.quantity,
                        "work_unit",
                        func.concat(
                            WorkUnit.area,
                            ":",
                            WorkUnit.location,
                            ":",
                            WorkUnit.category,
                            ":",
                            WorkUnit.subcategory,
                            ":",
                            WorkUnit.action,
                        ),
                    ).distinct()
                ),
            )
            .where(and_(Project.contractor_id == cid, Project.is_active == True))
            .join(BookingDetail, BookingDetail.id == Project.booking_id)
            .join(Homeowner, Homeowner.id == BookingDetail.homeowner_id)
            .join(BookingUnit, BookingUnit.booking_id == BookingDetail.id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .group_by(Project, BookingDetail, Homeowner)
        )
        models = db.execute(query).all()
        return models

    @staticmethod
    def by_id(bid: uuid.UUID, db: Session):
        query = select(Project).where(Project.booking_id == bid)
        project = db.exec(query).first()
        return project

    @staticmethod
    def by_cid(bid: uuid.UUID, cid: uuid.UUID, db: Session):
        query = (
            select(
                Project,
                func.json_build_object(
                    "id",
                    BookingDetail.id,
                    "title",
                    BookingDetail.title,
                    "zipcode",
                    BookingDetail.zipcode,
                    "address",
                    BookingDetail.address,
                    "units",
                    func.json_agg(
                        func.json_build_object(
                            "work_unit_id",
                            BookingUnit.work_unit_id,
                            "description",
                            BookingUnit.description,
                            "quantity",
                            BookingUnit.quantity,
                            "work_unit",
                            func.concat(
                                WorkUnit.area,
                                ":",
                                WorkUnit.location,
                                ":",
                                WorkUnit.category,
                                ":",
                                WorkUnit.subcategory,
                                ":",
                                WorkUnit.action,
                            ),
                        )
                    ),
                ),
                func.json_agg(
                    func.json_build_object(
                        "uri",
                        BookingImage.uri,
                        "caption",
                        BookingImage.caption,
                        "timestamp",
                        BookingImage.created_at,
                    ),
                )
                .filter(
                    BookingImage.uri.isnot(None),
                )
                .label("booking_images"),
                func.json_agg(
                    func.json_build_object(
                        "uri",
                        ProjectImage.uri,
                        "caption",
                        ProjectImage.caption,
                        "timestamp",
                        ProjectImage.created_at,
                    )
                )
                .filter(
                    ProjectImage.uri.isnot(None),
                )
                .label("project_images"),
                Homeowner,
            )
            .where(and_(Project.booking_id == bid, Project.contractor_id == cid))
            .outerjoin(BookingImage, BookingImage.booking_id == Project.booking_id)
            .outerjoin(ProjectImage, ProjectImage.booking_id == Project.booking_id)
            .join(BookingDetail, BookingDetail.id == Project.booking_id)
            .join(BookingUnit, BookingUnit.booking_id == Project.booking_id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .join(Homeowner, Homeowner.id == BookingDetail.homeowner_id)
            .group_by(Project, BookingDetail, ProjectImage, BookingImage, Homeowner)
        )
        model = db.exec(query).first()
        return model

    @staticmethod
    def by_hid(bid: uuid.UUID, hid: uuid.UUID, db: Session):
        query = (
            select(
                Project,
                func.json_build_object(
                    "id",
                    BookingDetail.id,
                    "title",
                    BookingDetail.title,
                    "zipcode",
                    BookingDetail.zipcode,
                    "address",
                    BookingDetail.address,
                    "units",
                    func.json_agg(
                        func.json_build_object(
                            "work_unit_id",
                            BookingUnit.work_unit_id,
                            "description",
                            BookingUnit.description,
                            "quantity",
                            BookingUnit.quantity,
                            "work_unit",
                            func.concat(
                                WorkUnit.area,
                                ":",
                                WorkUnit.location,
                                ":",
                                WorkUnit.category,
                                ":",
                                WorkUnit.subcategory,
                                ":",
                                WorkUnit.action,
                            ),
                        )
                    ),
                ),
                func.json_agg(
                    func.json_build_object(
                        "uri",
                        BookingImage.uri,
                        "caption",
                        BookingImage.caption,
                        "timestamp",
                        BookingImage.created_at,
                    ),
                )
                .filter(
                    BookingImage.uri.isnot(None),
                )
                .label("booking_images"),
                func.json_agg(
                    func.json_build_object(
                        "uri",
                        ProjectImage.uri,
                        "caption",
                        ProjectImage.caption,
                        "timestamp",
                        ProjectImage.created_at,
                    )
                )
                .filter(
                    ProjectImage.uri.isnot(None),
                )
                .label("project_images"),
                Contractor,
            )
            .where(Project.booking_id == bid)
            .outerjoin(BookingImage, BookingImage.booking_id == Project.booking_id)
            .outerjoin(ProjectImage, ProjectImage.booking_id == Project.booking_id)
            .join(
                BookingDetail,
                and_(
                    BookingDetail.id == Project.booking_id,
                    BookingDetail.homeowner_id == hid,
                ),
            )
            .join(BookingUnit, BookingUnit.booking_id == Project.booking_id)
            .join(WorkUnit, WorkUnit.id == BookingUnit.work_unit_id)
            .join(Contractor, Contractor.id == Project.contractor_id)
            .group_by(Project, BookingDetail, ProjectImage, BookingImage, Contractor)
        )
        model = db.exec(query).first()
        return model

    @staticmethod
    def public_by_cid(cid: uuid.UUID, bid: uuid.UUID, db: Session):
        query = (
            select(
                Project,
                func.json_build_object(
                    "title",
                    BookingDetail.title,
                    "zipcode",
                    BookingDetail.zipcode,
                ),
                func.json_agg(
                    func.json_build_object(
                        "work_unit_id",
                        BookingUnit.work_unit_id,
                        "description",
                        BookingUnit.description,
                        "quantity",
                        BookingUnit.quantity,
                        "work_unit",
                        func.concat(
                            WorkUnit.area,
                            ":",
                            WorkUnit.location,
                            ":",
                            WorkUnit.category,
                            ":",
                            WorkUnit.subcategory,
                            ":",
                            WorkUnit.action,
                        ),
                    )
                ),
                func.json_agg(
                    func.json_build_object(
                        "uri",
                        BookingImage.uri,
                        "caption",
                        BookingImage.caption,
                        "timestamp",
                        BookingImage.created_at,
                    )
                ).filter(
                    BookingImage.uri.isnot(None),
                ),
                func.json_agg(
                    func.json_build_object(
                        "uri",
                        ProjectImage.uri,
                        "caption",
                        ProjectImage.caption,
                        "timestamp",
                        ProjectImage.created_at,
                    )
                ).filter(
                    ProjectImage.uri.isnot(None),
                ),
            )
            .where(
                Project.contractor_id == cid,
                Project.booking_id == bid,
                Project.is_public == True,
                Project.is_active == False,
            )
            .join(BookingDetail, BookingDetail.id == Project.booking_id)
            .join(BookingUnit, BookingUnit.booking_id == Project.booking_id)
            .outerjoin(
                BookingImage,
                BookingImage.booking_id == Project.booking_id,
            )
            .outerjoin(ProjectImage, ProjectImage.booking_id == Project.booking_id)
            .group_by(
                Project.booking_id, BookingDetail, BookingImage.uri, ProjectImage.uri
            )
        )
        projects = db.exec(query).first()
        return projects


# TODO: we need to add a completion_signal
class HomeownerProjectView(SQLModel):
    booking: BookingDetailViewBase
    contractor: ContractorPublicView
    project_images: List[ImageBase] | None = None
    signal_completion: bool


class ContractorProjectView(SQLModel):
    booking: BookingDetailViewBase
    homeowner: HomeownerPublicView
    signal_completion: bool
    project_images: List[ImageBase] | None = None


class PortfolioPublicProjectView(SQLModel):
    id: Optional[uuid.UUID]
    title: str
    units: List[BookingUnitView]
    booking_images: List[ImageBase] | None = None
    project_images: List[ImageBase] | None = None

    @staticmethod
    def create(
        ptf: Project,
        booking,
        units,
        booking_images,
        project_images,
        db: Session,
    ):
        if booking_images:
            ta = TypeAdapter(list[ImageBase])
            booking_images = ta.validate_python(booking_images)
        if project_images:
            ta = TypeAdapter(list[ImageBase])
            project_images = ta.validate_python(project_images)


        return PortfolioPublicProjectView(
            id=ptf.booking_id,
            title=booking.get("title", None),
            booking_images=booking_images,
            project_images=project_images,
            units=[BookingUnitView(**unit) for unit in units],
        )


class ProjectItem(HomeownerBookingItem):
    avatar_uri: str
    first_name: str
    last_name: str


class ProjectList(SQLModel):
    projects: List[ProjectItem]
