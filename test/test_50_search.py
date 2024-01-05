import time
from sqlmodel import Session
from fastapi import status
from api import models
from test.utils import (
    TESTPASS,
    TestApp,
    test_app,  # noqa: F401
)


def test_booking_can_parse_json_from_form_data(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=20)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        for _ in range(5):
            cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
            cnt, user, access_token = app.create_contractor_with_token(cnt)
            areas = models.ContractorAreaPreference.mocks(app.faky, cnt.id, 1)
            units = models.ContractorUnitPreference.mocks(app.faky, cnt.id, 1)
            preferences = models.ContractorPreferencesCreate.from_units(
                areas, units, db
            )
            app.create_contractor_preference(access_token, preferences)

        for _ in range(5):
            cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
            cnt, user, access_token = app.create_contractor_with_token(cnt)
            preferences = booking.to_preferences(cnt.id, db)
            app.create_contractor_preference(access_token, preferences)

    response = app.api.get(
        f"contractor/{booking_view.id}/search",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )

    assert response.status_code == status.HTTP_200_OK


def test_search_by_filter_no_matches(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    response = app.api.get(
        "professions", headers={"Authorization": f"Bearer {hmw_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    professions = list(response.json())
    target_profession = professions[0]
    target_zipcode = app.faky.fake.zipcode()

    for idx in range(1, len(target_profession)):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=[professions[idx]]
        )
        app.create_contractor_preference(access_token, preferences)

    filter = models.Filter(
        professions=[target_profession], zipcode=target_zipcode, units=None
    )
    response = app.api.post(
        "contractor/search",
        json=filter.model_dump(),
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_search_by_filter_with_matches(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    response = app.api.get(
        "professions", headers={"Authorization": f"Bearer {hmw_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    professions = list(response.json())
    target_profession = professions[0]
    target_zipcode = app.faky.fake.zipcode()

    # non matches
    for idx in range(1, len(target_profession)):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[str(int(target_zipcode) + 1)], professions=[professions[idx]]
        )
        app.create_contractor_preference(access_token, preferences)

    # matching zipcode : non matching professions
    for idx in range(1, len(target_profession)):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=[professions[idx]]
        )
        app.create_contractor_preference(access_token, preferences)

    # mathcing zipcode: partial unit matche
    with Session(app.db.engine) as db:
        units = models.WorkUnit.professions_to_ids([target_profession], db)
        units.pop()
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        units = [
            models.ContractorUnitPreference(work_unit_id=unit[0], contractor_id=cnt.id)
            for unit in units
        ]
        db.add_all(units)
        area = models.ContractorAreaPreference(
            area=target_zipcode, contractor_id=cnt.id
        )
        db.add(area)

    # non matching zip : matching professions
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[str(int(target_zipcode) + 1)], professions=[target_profession]
        )
        app.create_contractor_preference(access_token, preferences)

    #  non matching zip : ALL PROFESSIONS
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, cnt_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[str(int(target_zipcode) + 1)], professions=professions
        )
        app.create_contractor_preference(cnt_token, preferences)

    # empty preferences
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, cnt_token = app.create_contractor_with_token(cnt)

    matches = []
    # exact matches
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, access_token = app.create_contractor_with_token(cnt)
        matches.append(cnt.id)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=[target_profession]
        )
        app.create_contractor_preference(access_token, preferences)

    # matching zip : ALL PROFESSIONS
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, cnt_token = app.create_contractor_with_token(cnt)
        matches.append(cnt.id)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=professions
        )
        app.create_contractor_preference(cnt_token, preferences)

    filter = models.Filter(
        professions=[target_profession], zipcode=target_zipcode, units=None
    )
    response = app.api.post(
        "contractor/search",
        json=filter.model_dump(),
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = models.SearchContractorList.model_validate_json(response.text)
    assert len(response.contractors) == len(matches)
    assert set([contractor.id for contractor in response.contractors]) == set(matches)

def test_search_by_booking_no_matches(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    response = app.api.get(
        "professions", headers={"Authorization": f"Bearer {hmw_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    professions = list(response.json())
    target_profession = professions[0]
    target_zipcode = app.faky.fake.zipcode()

    with Session(app.db.engine) as db:
    # NON-MATCHING BOOKING
        units = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids([professions[1]], db)
        ]
        booking = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=app.faky.fake.postcode(),
            units=units,
            captions=[],
            address=app.faky.fake.address(),
        )

    booking_view_not_matching = app.create_homeowner_booking(hmw_token, booking)

    for idx in range(1, len(target_profession)):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=[professions[idx]]
        )
        app.create_contractor_preference(access_token, preferences)
    
    response = app.api.get(
        f"contractor/{booking_view_not_matching.id}/search",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT

def test_search_by_booking_with_matches(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    response = app.api.get(
        "professions", headers={"Authorization": f"Bearer {hmw_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    professions = list(response.json())
    target_profession = professions[0]
    target_zipcode = app.faky.fake.zipcode()

    with Session(app.db.engine) as db:
    # MATCHING BOOKING
        units = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids([professions[0]], db)
        ]
        booking = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=target_zipcode,
            units=units,
            captions=[],
            address=app.faky.fake.address(),
        )

    booking_view_matching = app.create_homeowner_booking(hmw_token, booking)

    # non matching zipcode
    for idx in range(1, len(target_profession)):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[str(int(target_zipcode) + 1)], professions=[professions[idx]]
        )
        app.create_contractor_preference(access_token, preferences)

    # matching zipcode : non matching professions
    for idx in range(1, len(target_profession)):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=[professions[idx]]
        )
        app.create_contractor_preference(access_token, preferences)

    # matching zipcode: partial unit match
    with Session(app.db.engine) as db:
        units = models.WorkUnit.professions_to_ids([target_profession], db)
        units.pop()
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, user, access_token = app.create_contractor_with_token(cnt)
        units = [
            models.ContractorUnitPreference(work_unit_id=unit[0], contractor_id=cnt.id)
            for unit in units
        ]
        db.add_all(units)
        area = models.ContractorAreaPreference(
            area=target_zipcode, contractor_id=cnt.id
        )
        db.add(area)

    # non matching zip : matching professions
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, access_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[str(int(target_zipcode) + 1)], professions=[target_profession]
        )
        app.create_contractor_preference(access_token, preferences)

    #  non matching zip : ALL PROFESSIONS
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, cnt_token = app.create_contractor_with_token(cnt)
        preferences = models.ContractorPreferencesCreate(
            areas=[str(int(target_zipcode) + 1)], professions=professions
        )
        app.create_contractor_preference(cnt_token, preferences)

    # empty preferences
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, cnt_token = app.create_contractor_with_token(cnt)

    matches = []
    # exact matches
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, access_token = app.create_contractor_with_token(cnt)
        matches.append(cnt.id)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=[target_profession]
        )
        app.create_contractor_preference(access_token, preferences)

    # matching zip : ALL PROFESSIONS
    for _ in range(3):
        cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
        cnt, _, cnt_token = app.create_contractor_with_token(cnt)
        matches.append(cnt.id)
        preferences = models.ContractorPreferencesCreate(
            areas=[target_zipcode], professions=professions
        )
        app.create_contractor_preference(cnt_token, preferences)

    response = app.api.get(
        f"contractor/{booking_view_matching.id}/search",
        headers={"Authorization": f"Bearer {hmw_token}"},
    ) 
    assert response.status_code == status.HTTP_200_OK
    response = models.SearchContractorList.model_validate_json(response.text)
    assert len(response.contractors) == len(matches)
    assert set([contractor.id for contractor in response.contractors]) == set(matches)