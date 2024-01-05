from collections import Counter
import copy
import json
import shutil
import uuid

import httpx
from api.core.auth.utils import Token, TokenData
import api.models as models
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session
from api.config import Config, get_config
from api.core.db import DB, get_db
from api.utils.faky import Faky, create_faky
import pytest
from api.app import start

TESTPASS: str = "1234567"


class TestApp:
    api: TestClient
    db: DB
    faky: Faky
    config: Config

    @staticmethod
    def for_mocks(db: DB):
        testapp = TestApp()
        testapp.config = get_config()
        testapp.api = httpx.Client(
            base_url=f"http://localhost:80{testapp.config.ROOT_PATH}"
        )
        testapp.db = db

        with Session(db.engine) as session:
            testapp.faky = create_faky(session)
        return testapp

    @staticmethod
    def create(api: FastAPI, db: DB):
        testapp = TestApp()
        testapp.config = get_config()
        testapp.api = TestClient(
            api, base_url=f"http://testserver{testapp.config.ROOT_PATH}"
        )
        testapp.db = db
        with Session(db.engine) as session:
            testapp.faky = create_faky(session)
        return testapp

    def create_contractor(self, contractor: models.ContractorCreate):
        contractor.password = contractor.password.get_secret_value()
        response = self.api.post("contractor/signup", data=contractor.model_dump())
        assert response.status_code == status.HTTP_200_OK
        cnt = models.ContractorPublicView.model_validate_json(response.text)
        assert cnt.budget_rating == 0
        assert cnt.on_schedule_rating == 0
        assert cnt.quality_rating == 0
        assert cnt.first_name == contractor.first_name
        assert cnt.last_name == contractor.last_name
        assert cnt.bio == contractor.bio
        user = models.User(
            id=cnt.id,
            email=contractor.email,
            phone_number=contractor.phone_number,
            password=contractor.password,
        )
        return cnt, user

    def create_homeowner(self, homeowner: models.HomeownerCreate):
        homeowner.password = homeowner.password.get_secret_value()
        response = self.api.post("homeowner/signup", data=homeowner.model_dump())
        assert response.status_code == status.HTTP_200_OK
        hw = models.HomeownerPublicView.model_validate_json(response.text)
        assert hw.first_name == homeowner.first_name
        assert hw.last_name == homeowner.last_name
        user = models.User(
            id=hw.id,
            email=homeowner.email,
            phone_number=homeowner.phone_number,
            password=homeowner.password,
        )
        return hw, user

    def create_contractor_with_token(self, contractor: models.ContractorCreate):
        cnt, user = self.create_contractor(contractor)
        access_token = self.auth_user(user.email, models.UserRole.Contractor)
        return cnt, user, access_token

    def create_homeowner_with_token(self, homeowner: models.HomeownerCreate):
        hw, user = self.create_homeowner(homeowner)
        access_token = self.auth_user(user.email, models.UserRole.Homeowner)
        return hw, user, access_token

    def create_contractor_preference(
        self, access_token: str, preferences: models.ContractorPreferencesCreate
    ):
        response = self.api.post(
            "contractor/preferences",
            headers={"Authorization": f"Bearer {access_token}"},
            json=preferences.model_dump(),
        )
        assert response.status_code == status.HTTP_200_OK
        response = models.ContractorPreferencesView.model_validate_json(response.text)
        assert len(preferences.areas) == len(response.areas)
        assert Counter(preferences.areas) == Counter(response.areas)
        assert len(preferences.professions) == len(response.professions)
        assert Counter(preferences.professions) == Counter(response.professions)
        return response

    def get_contractor_preferences(self, cid: uuid.UUID, access_token: str):
        response = self.api.get(
            f"contractor/{cid}/preferences",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        preferences = models.ContractorPreferencesView.model_validate_json(
            response.text
        )
        return preferences

    def create_contractor_portfolio(
        self, access_token: str, portfolio: models.PortfolioProjectCreate, imgs
    ):
        data = json.dumps(portfolio.model_dump())
        data = {"portfolio": data}
        response = self.api.post(
            "contractor/portfolio/external/project",
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            files=imgs,
            data=data,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"img_uploaded": len(imgs)}

    def get_external_portfio_project_ids(self, cid: uuid.UUID, access_token: str):
        response = self.api.get(
            f"contractor/portfolio/{cid}/external/projects",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        external_project_list = (
            models.PortfolioExternalProjectsList.model_validate_json(response.text)
        )
        return external_project_list

    def get_public_portfio_project_ids(self, cid: uuid.UUID, access_token: str):
        response = self.api.get(
            f"contractor/portfolio/{cid}/public/projects",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        print(response.text)
        assert response.status_code == status.HTTP_200_OK
        public_project_list = models.PortfolioPublicProjectsList.model_validate_json(
            response.text
        )
        return public_project_list

    def create_homeowner_booking(
        self, access_token, booking: models.BookingDetailCreate, files=None
    ):
        data = json.dumps(booking.model_dump())
        data = {"booking": data}
        response = self.api.post(
            "homeowner/booking",
            headers={"Authorization": f"Bearer {access_token}"},
            data=data,
            files=files,
        )
        assert response.status_code == status.HTTP_200_OK
        booking_view = models.HomeownerBookingDetailView.model_validate_json(
            response.text
        )
        return booking_view

    def auth_user(self, email: str, role: models.UserRole):
        response = self.api.post(
            "token",
            data={
                "password": TESTPASS,
                "username": email,
                "scope": role.value,
            },
        )
        assert response.status_code == status.HTTP_200_OK
        token = Token.model_validate_json(response.text)
        assert token.token_type == f"bearer scope={role.value}"
        token_data = TokenData.decode(token.access_token)
        assert token_data.scopes[0] == role.value
        return token.access_token

    def cleanup(self):
        # time.sleep(10000)
        SQLModel.metadata.drop_all(self.db.engine)
        try:
            shutil.rmtree("img/")
        except OSError:
            pass


@pytest.fixture()
def test_app() -> TestApp:
    api = start()

    def get_test_config():
        config = get_config()
        config_copy = copy.deepcopy(config)
        config_copy.ENV = "dev"
        return config_copy

    api.dependency_overrides[get_config] = get_test_config
    db = get_db()
    db.init_db(force=True)
    app = TestApp.create(api, db)
    yield app
    app.cleanup()


@pytest.fixture()
def test_app_with_1_second_token():
    api = start()
    db = get_db()
    db.init_db()

    def get_test_config():
        config = get_config()
        config_copy = copy.deepcopy(config)
        config_copy.JWT_TOKEN_EXPIRE_SECONDS = 1
        return config_copy

    api.dependency_overrides[get_config] = get_test_config
    app = TestApp.create(api, db)
    yield app
    app.cleanup()
