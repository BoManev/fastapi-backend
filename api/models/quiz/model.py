from typing import List, Optional
from sqlalchemy import Column, Engine, Text, text
from sqlmodel import Field, SQLModel, Session, select


class WorkUnitCreate(SQLModel):
    area: str
    location: str
    category: str
    subcategory: str
    action: str
    quantity: str
    profession: str

    @staticmethod
    def from_line(line: str) -> List["WorkUnitCreate"]:
        """{area}-{location}:{category}/{subcategory}_[{action.quantity.profession},{action.quantity.profession}]"""
        if not isinstance(line, str):
            return None

        geo, rest = line.split(":")
        area, location = geo.split("-")
        categories, pairs = rest.split("_")
        category, subcategory = categories.split("/")
        actions = list(map(lambda pair: tuple(pair.split(".")), pairs[1:-1].split(",")))
        return [
            WorkUnitCreate(
                area=area,
                location=location,
                category=category,
                subcategory=subcategory,
                action=action[0],
                quantity=action[1],
                profession=action[2],
            )
            for action in actions
        ]


class WorkUnit(SQLModel, table=True):
    __tablename__ = "work_units"
    id: Optional[int] = Field(default=None, primary_key=True)
    area: str = Field(nullable=False)
    location: str = Field(nullable=False)
    category: str = Field(nullable=False)
    subcategory: str = Field(nullable=False)
    action: str = Field(nullable=False)
    quantity: str = Field(nullable=False)
    profession: str = Field(nullable=False)

    class QuizView(SQLModel):
        quiz: str

    @staticmethod
    def init_table(engine: Engine):
        column = Column(
            "digest",
            Text,
            info={
                "generate": "GENERATED ALWAYS AS (MD5(area||location||category||subcategory||action||quantity||profession)) STORED"
            },
            unique=True,
        )
        column_name = column.compile(dialect=engine.dialect)
        column_type = column.type.compile(engine.dialect)
        with engine.connect() as db:
            db.execute(
                text(
                    "ALTER TABLE {} ADD COLUMN {} {} {}, ADD CONSTRAINT ensure_unique_work_unit UNIQUE ({})".format(
                        WorkUnit.__tablename__,
                        column_name,
                        column_type,
                        column.info["generate"],
                        column_name,
                    )
                )
            )
            db.commit()

    @staticmethod
    def all(db: Session):
        query = select(WorkUnit)
        return db.execute(query).all()

    @staticmethod
    def all_professions(db: Session):
        query = select(WorkUnit.profession).distinct(WorkUnit.profession)
        return db.execute(query).all()

    @staticmethod
    def by_ids(ids: List[int], db: Session):
        query = select(WorkUnit).where(WorkUnit.id.in_(ids))
        return db.execute(query).all()

    @staticmethod
    def by_actions(actions: List[str], db: Session):
        query = select(WorkUnit).where(WorkUnit.action.in_(actions))
        return db.execute(query).all()

    @staticmethod
    def by_professions(professions: List[str], db: Session):
        query = select(WorkUnit).where(WorkUnit.profession.in_(professions))
        return db.execute(query).all()

    @staticmethod
    def professions_to_ids(professions: List[str], db: Session):
        query = select(WorkUnit.id).where(WorkUnit.profession.in_(professions))
        return db.execute(query).all()

    @staticmethod
    def ids_to_professions(ids: List[int], db: Session):
        query = select(WorkUnit.profession).where(WorkUnit.id.in_(ids)).distinct()
        model = db.execute(query).all()
        return model

    def concat(self):
        return f"{self.area}:{self.location}:{self.category}:{self.subcategory}:{self.action}"


class WorkUnitView(SQLModel):
    # TODO custom pydantic class

    @staticmethod
    def to_json(db: Session):
        raw_units = WorkUnit.all(db)
        view = {}
        for raw_unit in raw_units:
            unit: WorkUnit = raw_unit[0]

            if unit.area not in view:
                view[unit.area] = {}

            if unit.location not in view[unit.area]:
                view[unit.area][unit.location] = {}

            if unit.category not in view[unit.area][unit.location]:
                view[unit.area][unit.location][unit.category] = {}

            if unit.subcategory not in view[unit.area][unit.location][unit.category]:
                view[unit.area][unit.location][unit.category][unit.subcategory] = []

            view[unit.area][unit.location][unit.category][unit.subcategory].append(
                {
                    unit.id: {
                        "quantity": unit.quantity,
                        "action": unit.action,
                        "profession": unit.profession,
                    }
                }
            )

        return view


# FORMAT
# {area}-{location}:{category}/{subcategory}_[{action.quantity.profession},{action.quantity.profession}]
WorkUnits: List[str] = [
    "Indoors-Living Room:Furniture/Couches_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist,Maintenance.Count.Upholsterer]",
    "Indoors-Living Room:Furniture/Chairs_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist,Maintenance.Count.Upholsterer]",
    "Indoors-Living Room:Furniture/Tables_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist]",
    "Indoors-Living Room:Furniture/Carpeting_[Installation.Square Feet.Carpet Installer,Repair.Square Feet.Carpet Installer,Clean.Square Feet.Carpet Cleaner,Remove.Square Feet.Carpet Installer]",
    "Indoors-Living Room:Electrical/TVs_[Installation.Count.Audio Visual Technician,Repair.Count.Audio Visual Technician,Replacement.Count.Audio Visual Technician]",
    "Indoors-Living Room:Electrical/Speakers_[Installation.Count.Audio Visual Technician,Repair.Count.Audio Visual Technician,Replacement.Count.Audio Visual Technician]",
    "Indoors-Living Room:Electrical/Wiring_[Installation.Length.Electrician,Repair.Length.Electrician,Replacement.Length.Electrician]",
    "Indoors-Living Room:Electrical/Lighting_[Installation.Count.Electrician,Repair.Count.Electrician,Replacement.Count.Electrician]",
    "Indoors-Living Room:Structure/Walls_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Plaster.Square Feet.Plasterer,Trim.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Living Room:Structure/Windows_[Installation.Count.Window Installer,Repair.Count.Window Installer,Seal.Count.Window Specialist,Tint.Count.Window Specialist]",
    "Indoors-Living Room:Structure/Ceiling_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Crown Mold.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Living Room:Structure/Flooring_[Installation.Square Feet.Flooring Installer,Repair.Square Feet.Flooring Installer,Sand.Square Feet.Flooring Refinisher,Sealing.Square Feet.Flooring Refinisher,Demolition.Square Feet.Flooring Installer]",
    "Indoors-Living Room:Structure/HVAC_[Installation.Count.HVAC Technician,Repair.Count.HVAC Technician,Maintenance.Count.HVAC Technician]",
    "Indoors-Dining Room:Furniture/Chairs_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist,Maintenance.Count.Upholsterer]",
    "Indoors-Dining Room:Furniture/Tables_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist]",
    "Indoors-Dining Room:Electrical/TVs_[Installation.Count.Audio Visual Technician,Repair.Count.Audio Visual Technician,Replacement.Count.Audio Visual Technician]",
    "Indoors-Dining Room:Electrical/Speakers_[Installation.Count.Audio Visual Technician,Repair.Count.Audio Visual Technician,Replacement.Count.Audio Visual Technician]",
    "Indoors-Dining Room:Electrical/Wiring_[Installation.Length.Electrician,Repair.Length.Electrician,Replacement.Length.Electrician]",
    "Indoors-Dining Room:Electrical/Lighting_[Installation.Count.Electrician,Repair.Count.Electrician,Replacement.Count.Electrician]",
    "Indoors-Dining Room:Structure/Walls_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Plaster.Square Feet.Plasterer,Trim.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Dining Room:Structure/Windows_[Installation.Count.Window Installer,Repair.Count.Window Installer,Seal.Count.Window Specialist,Tint.Count.Window Specialist]",
    "Indoors-Dining Room:Structure/Ceiling_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Crown Mold.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Dining Room:Structure/Flooring_[Installation.Square Feet.Flooring Installer,Repair.Square Feet.Flooring Installer,Sand.Square Feet.Flooring Refinisher,Sealing.Square Feet.Flooring Refinisher,Demolition.Square Feet.Flooring Installer]",
    "Indoors-Dining Room:Structure/HVAC_[Installation.Count.HVAC Technician,Repair.Count.HVAC Technician,Maintenance.Count.HVAC Technician]",
    "Indoors-Kitchen:Furniture/Chairs_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist,Maintenance.Count.Upholsterer]",
    "Indoors-Kitchen:Furniture/Cabinets_[Installation.Count.Cabinet Specialist,Repair.Count.Cabinet Specialist,Replacement.Count.Cabinet Specialist]",
    "Indoors-Kitchen:Furniture/Countertops_[Installation.Count.Countertop Specialist,Repair.Count.Countertop Specialist,Replacement.Count.Countertop Specialist]",
    "Indoors-Kitchen:Appliances/Stoves_[Installation.Count.Kitchen Appliance Technician,Repair.Count.Kitchen Appliance Technician,Replacement.Count.Kitchen Appliance Technician, Maintenance.Count.Kitchen Appliance Technician]",
    "Indoors-Kitchen:Appliances/Ovens_[Installation.Count.Kitchen Appliance Technician,Repair.Count.Kitchen Appliance Technician,Replacement.Count.Kitchen Appliance Technician, Maintenance.Count.Kitchen Appliance Technician]",
    "Indoors-Kitchen:Appliances/Refrigerators_[Installation.Count.Kitchen Appliance Technician,Repair.Count.Kitchen Appliance Technician,Replacement.Count.Kitchen Appliance Technician, Maintenance.Count.Kitchen Appliance Technician]",
    "Indoors-Kitchen:Appliances/Range Hoods_[Installation.Count.Kitchen Appliance Technician,Repair.Count.Kitchen Appliance Technician,Replacement.Count.Kitchen Appliance Technician, Maintenance.Count.Kitchen Appliance Technician]",
    "Indoors-Kitchen:Appliances/Microwaves_[Installation.Count.Kitchen Appliance Technician,Repair.Count.Kitchen Appliance Technician,Replacement.Count.Kitchen Appliance Technician, Maintenance.Count.Kitchen Appliance Technician]",
    "Indoors-Kitchen:Appliances/Sinks_[Installation.Count.Plumber,Repair.Count.Plumber,Replacement.Count.Plumber, Maintenance.Count.Plumber]",
    "Indoors-Kitchen:Electrical/Wiring_[Installation.Length.Electrician,Repair.Length.Electrician,Replacement.Length.Electrician]",
    "Indoors-Kitchen:Electrical/Lighting_[Installation.Count.Electrician,Repair.Count.Electrician,Replacement.Count.Electrician]",
    "Indoors-Kitchen:Structure/Walls_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Plaster.Square Feet.Plasterer,Trim.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Kitchen:Structure/Windows_[Installation.Count.Window Installer,Repair.Count.Window Installer,Seal.Count.Window Specialist,Tint.Count.Window Specialist]",
    "Indoors-Kitchen:Structure/Ceiling_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Crown Mold.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Kitchen:Structure/Flooring_[Installation.Square Feet.Flooring Installer,Repair.Square Feet.Flooring Installer,Sand.Square Feet.Flooring Refinisher,Sealing.Square Feet.Flooring Refinisher,Demolition.Square Feet.Flooring Installer]",
    "Indoors-Kitchen:Structure/HVAC_[Installation.Count.HVAC Technician,Repair.Count.HVAC Technician,Maintenance.Count.HVAC Technician]",
    "Indoors-Bedroom:Furniture/Beds_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist]",
    "Indoors-Bedroom:Furniture/Chairs_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist,Maintenance.Count.Upholsterer]",
    "Indoors-Bedroom:Furniture/Tables_[Repair.Count.Furniture Repair Specialist,Replacement.Count.Furniture Repair Specialist]",
    "Indoors-Bedroom:Furniture/Carpeting_[Installation.Square Feet.Carpet Installer,Repair.Square Feet.Carpet Installer,Clean.Square Feet.Carpet Cleaner,Remove.Square Feet.Carpet Installer]",
    "Indoors-Bedroom:Electrical/TVs_[Installation.Count.Audio Visual Technician,Repair.Count.Audio Visual Technician,Replacement.Count.Audio Visual Technician]",
    "Indoors-Bedroom:Electrical/Speakers_[Installation.Count.Audio Visual Technician,Repair.Count.Audio Visual Technician,Replacement.Count.Audio Visual Technician]",
    "Indoors-Bedroom:Electrical/Wiring_[Installation.Length.Electrician,Repair.Length.Electrician,Replacement.Length.Electrician]",
    "Indoors-Bedroom:Electrical/Lighting_[Installation.Count.Electrician,Repair.Count.Electrician,Replacement.Count.Electrician]",
    "Indoors-Bedroom:Structure/Walls_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Plaster.Square Feet.Plasterer,Trim.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Bedroom:Structure/Windows_[Installation.Count.Window Installer,Repair.Count.Window Installer,Seal.Count.Window Specialist,Tint.Count.Window Specialist]",
    "Indoors-Bedroom:Structure/Ceiling_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Crown Mold.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Bedroom:Structure/Flooring_[Installation.Square Feet.Flooring Installer,Repair.Square Feet.Flooring Installer,Sand.Square Feet.Flooring Refinisher,Sealing.Square Feet.Flooring Refinisher,Demolition.Square Feet.Flooring Installer]",
    "Indoors-Bedroom:Structure/HVAC_[Installation.Count.HVAC Technician,Repair.Count.HVAC Technician,Maintenance.Count.HVAC Technician]",
    "Indoors-Bathroom:Furniture/Cabinets_[Installation.Count.Cabinet Specialist,Repair.Count.Cabinet Specialist,Replacement.Count.Cabinet Specialist]",
    "Indoors-Bathroom:Furniture/Countertops_[Installation.Count.Countertop Specialist,Repair.Count.Countertop Specialist,Replacement.Count.Countertop Specialist]",
    "Indoors-Bathroom:Furniture/Mirrors_[Installation.Count.Mirror Specialist,Repair.Count.Mirror Specialist,Replacement.Count.Mirror Specialist]",
    "Indoors-Bathroom:Appliances/Toilets_[Installation.Count.Plumber,Repair.Count.Plumber,Replacement.Count.Plumber,Maintenance.Count.Plumber]",
    "Indoors-Bathroom:Appliances/Sinks_[Installation.Count.Plumber,Repair.Count.Plumber,Replacement.Count.Plumber, Maintenance.Count.Plumber]",
    "Indoors-Bathroom:Appliances/Showers_[Installation.Count.Plumber,Repair.Count.Plumber,Replacement.Count.Plumber,Maintenance.Count.Plumber]",
    "Indoors-Bathroom:Appliances/Bathtubs_[Installation.Count.Plumber,Repair.Count.Plumber,Replacement.Count.Plumber,Maintenance.Count.Plumber]",
    "Indoors-Bathroom:Appliances/Water Heating_[Installation.Count.Plumber,Repair.Count.Plumber,Maintenance.Count.Plumber]",
    "Indoors-Bathroom:Appliances/Water Cooling_[Installation.Count.Plumber,Repair.Count.Plumber,Maintenance.Count.Plumber]",
    "Indoors-Bathroom:Electrical/Wiring_[Installation.Length.Electrician,Repair.Length.Electrician,Replacement.Length.Electrician]",
    "Indoors-Bathroom:Electrical/Lighting_[Installation.Count.Electrician,Repair.Count.Electrician,Replacement.Count.Electrician]",
    "Indoors-Bathroom:Structure/Walls_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Plaster.Square Feet.Plasterer,Trim.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Bathroom:Structure/Windows_[Installation.Count.Window Installer,Repair.Count.Window Installer,Seal.Count.Window Specialist,Tint.Count.Window Specialist]",
    "Indoors-Bathroom:Structure/Ceiling_[Installation.Square Feet.Drywaller,Repair.Square Feet.Drywaller,Paint.Square Feet.Painter,Crown Mold.Square Feet.Carpenter,Demolition.Square Feet.Drywaller]",
    "Indoors-Bathroom:Structure/Flooring_[Installation.Square Feet.Flooring Installer,Repair.Square Feet.Flooring Installer,Sand.Square Feet.Flooring Refinisher,Sealing.Square Feet.Flooring Refinisher,Demolition.Square Feet.Flooring Installer]",
    "Indoors-Bathroom:Structure/HVAC_[Installation.Count.HVAC Technician,Repair.Count.HVAC Technician,Maintenance.Count.HVAC Technician]",
    "Indoors-Utility:Appliances/Washing Machines_[Installation.Count.Appliance Technician,Repair.Count.Appliance Technician,Replacement.Count.Appliance Technician,Maintenance.Count.Appliance Technician]",
    "Indoors-Utility:Appliances/Dryers_[Installation.Count.Appliance Technician,Repair.Count.Appliance Technician,Replacement.Count.Appliance Technician,Maintenance.Count.Appliance Technician]",
    "Indoors-Utility:Appliances/Water Heating_[Installation.Count.Plumber,Repair.Count.Plumber,Maintenance.Count.Plumber]",
    "Indoors-Utility:Appliances/Water Cooling_[Installation.Count.Plumber,Repair.Count.Plumber,Maintenance.Count.Plumber]",
    "Indoors-Utility:Appliances/Internet_[Installation.Count.Network Technician,Repair.Count.Network Technician,Maintenance.Count.Network Technician]",
    "Indoors-Utility:Miscellaneous/HVAC_[Installation.Count.HVAC Technician,Repair.Count.HVAC Technician,Maintenance.Count.HVAC Technician]",
]
