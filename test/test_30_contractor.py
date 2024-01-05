from collections import Counter
import json

from sqlmodel import Session
from api import models
from fastapi import status
from api.core.error import APIError
import api.models as models
from test.utils import (
    TESTPASS,
    TestApp,
    test_app,  # noqa: F401
)


def test_upload_portfolio_with_image(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    img = models.ImageBase.mocks(app.faky, 1)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=1, caption_count=1)
    app.create_contractor_portfolio(access_token, prf, img)


def test_upload_portfolio_with_images(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    imgs = models.ImageBase.mocks(app.faky, 2)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=2, caption_count=2)
    app.create_contractor_portfolio(access_token, prf, imgs)


def test_upload_portfolio_with_no_enough_captions(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    imgs = models.ImageBase.mocks(app.faky, 2)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=2, caption_count=1)
    data = json.dumps(prf.model_dump())
    data = {"portfolio": data}
    response = app.api.post(
        "contractor/portfolio/external/project",
        headers={
            "Authorization": f"Bearer {access_token}",
        },
        files=imgs,
        data=data,
    )
    assert response.status_code == APIError.ImageUploadException.status_code
    assert response.json()["detail"] == APIError.ImageUploadException.detail


def test_upload_portfolios(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    imgs = models.ImageBase.mocks(app.faky, 1)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=1, caption_count=1)
    app.create_contractor_portfolio(access_token, prf, imgs)
    imgs = models.ImageBase.mocks(app.faky, 2)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=2, caption_count=2)
    app.create_contractor_portfolio(access_token, prf, imgs)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=1, caption_count=0)
    app.create_contractor_portfolio(access_token, prf, [])


def test_get_external_portfolios(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    imgs = models.ImageBase.mocks(app.faky, 2)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=2, caption_count=2)
    app.create_contractor_portfolio(access_token, prf, imgs)
    app.get_external_portfio_project_ids(cnt.id, access_token)


def test_contractor_create_preference(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    area = models.ContractorAreaPreference.mock(app.faky, cnt.id)
    unit = models.ContractorUnitPreference.mock(app.faky, cnt.id)
    with Session(app.db.engine) as db:
        preference = models.ContractorPreferencesCreate.from_units([area], [unit], db)
    app.create_contractor_preference(access_token, preference)


def test_contractor_create_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 3)
    units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 3)
    with Session(app.db.engine) as db:
        preferences = models.ContractorPreferencesCreate.from_units(areas, units, db)
    app.create_contractor_preference(access_token, preferences)


def test_contractor_update_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 3)
    units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 3)
    with Session(app.db.engine) as db:
        preferences = models.ContractorPreferencesCreate.from_units(areas, units, db)
    app.create_contractor_preference(access_token, preferences)
    areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 3)
    units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 3)
    with Session(app.db.engine) as db:
        preferences = models.ContractorPreferencesCreate.from_units(areas, units, db)
    app.create_contractor_preference(access_token, preferences)


def test_contractor_create_no_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    with Session(app.db.engine) as db:
        preferences = models.ContractorPreferencesCreate.from_units([], [], db)
    app.create_contractor_preference(access_token, preferences)


def test_contractor_get_no_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    app.get_contractor_preferences(cnt.id, access_token)


def test_contractor_get_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 3)
    units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 3)
    with Session(app.db.engine) as db:
        preferences_create = models.ContractorPreferencesCreate.from_units(areas, units, db)
    preferences_create = app.create_contractor_preference(access_token, preferences_create)
    preferences = app.get_contractor_preferences(cnt.id, access_token)
    assert len(preferences.areas) == len(preferences_create.areas)
    assert Counter(preferences.areas) == Counter(preferences_create.areas)
    assert len(preferences.professions) == len(preferences_create.professions)
    assert Counter(preferences.professions) == Counter(preferences_create.professions)


def test_contractor_delete_all_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 3)
    units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 3)
    with Session(app.db.engine) as db:
        preferences = models.ContractorPreferencesCreate.from_units(areas, units, db)
    app.create_contractor_preference(access_token, preferences)
    with Session(app.db.engine) as db:
        preferences = models.ContractorPreferencesCreate.from_units([], [], db)
    app.create_contractor_preference(access_token, preferences)


def test_contractor_preferences_schema(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    response = app.api.get(
        "professions",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_contractor_get_public_view_with_empty_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    response = app.api.get(
        f"contractor/{cnt.id}/public",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_contractor_get_public_view_with_preferences(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, user, access_token = app.create_contractor_with_token(cnt)
    areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 3)
    units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 3)
    with Session(app.db.engine) as db:
        preferences_create = models.ContractorPreferencesCreate.from_units(areas, units, db)
    preferences_create = app.create_contractor_preference(access_token, preferences_create)
    _preferences = app.get_contractor_preferences(cnt.id, access_token)
    response = app.api.get(
        f"contractor/{cnt.id}/public",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


# def test_contractor_get_private_view_with_empty_preferences(test_app: TestApp):
#     app: TestApp = test_app
#     cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
#     cnt, user, access_token = app.create_contractor_with_token(cnt)
#     response = app.api.get(
#         "contractor/private",
#         headers={"Authorization": f"Bearer {access_token}"},
#     )
#     assert response.status_code == status.HTTP_200_OK


# def test_contractor_get_private_view_with_preferences(test_app: TestApp):
#     app: TestApp = test_app
#     cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
#     cnt, user, access_token = app.create_contractor_with_token(cnt)
#     areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 3)
#     units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 3)
#     with Session(app.db.engine) as db:
#         preferences_create = models.ContractorPreferencesCreate.from_units(areas, units, db)
#     preferences_create = app.create_contractor_preference(access_token, preferences_create)
#     _preferences = app.get_contractor_preferences(cnt.id, access_token)
#     response = app.api.get(
#         "contractor/private",
#         headers={"Authorization": f"Bearer {access_token}"},
#     )
#     assert response.status_code == status.HTTP_200_OK
