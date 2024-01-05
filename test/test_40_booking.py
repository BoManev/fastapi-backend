import json
from sqlmodel import Session
from api import models
from fastapi import status
from api.core.error import APIError
from test.utils import (
    TESTPASS,
    TestApp,
    test_app,  # noqa: F401
)


def test_booking_can_parse_json_from_form_data(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, user, access_token = app.create_homeowner_with_token(hmw)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=1)
    app.create_homeowner_booking(access_token, booking)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2)
    app.create_homeowner_booking(access_token, booking)


def test_booking_reject_bad_encoding(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, user, access_token = app.create_homeowner_with_token(hmw)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=1)
    data = {"booking": booking}
    response = app.api.post(
        "homeowner/booking",
        headers={"Authorization": f"Bearer {access_token}"},
        data=data,
    )
    assert response.status_code == APIError.BookingValidationException.status_code
    assert (
        response.json()["detail"].split(":")[0]
        == APIError.BookingValidationException.detail
    )


def test_booking_reject_wrong_arguments(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, user, access_token = app.create_homeowner_with_token(hmw)
    data = {"wrong": "data"}
    data = json.dumps(data)
    data = {"booking": data}
    response = app.api.post(
        "homeowner/booking",
        headers={"Authorization": f"Bearer {access_token}"},
        data=data,
    )
    assert response.status_code == APIError.BookingValidationException.status_code
    assert (
        response.json()["detail"].split(":")[0]
        == APIError.BookingValidationException.detail
    )


def test_homeowner_books_contractor_no_matching_preferences(test_app: TestApp):
    # can fail randomly
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=20)
    booking_view = app.create_homeowner_booking(hmw_token, booking)

    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
    preferences.professions = [preferences.professions[0]]

    app.create_contractor_preference(cnt_token, preferences)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt.id)
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == APIError.NotMatchingPreferences.status_code
    assert response.json()["detail"] == APIError.NotMatchingPreferences.detail


def test_homeowner_books_contractor_matching_preferences(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt.id)
    book1 = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book1,
    )
    assert response.status_code == status.HTTP_200_OK


def test_contractor_accept_booking(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt.id)
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == status.HTTP_200_OK

    response = app.api.post(
        f"contractor/booking/{booking_view.id}/accept",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK

    response = app.api.post(
        f"contractor/booking/{booking_view.id}/accept",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == APIError.BookingInviteAlreadyAccepted.status_code
    assert response.json()["detail"] == APIError.BookingInviteAlreadyAccepted.detail


def test_contractors_accept_booking(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    cnt_1 = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt_1, _, cnt_token_1 = app.create_contractor_with_token(cnt_1)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
        preferences_1 = booking.to_preferences(cnt_1.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    app.create_contractor_preference(cnt_token_1, preferences_1)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt.id)
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == status.HTTP_200_OK
    book = models.BookingInviteCreate(
        booking_id=booking_view.id, contractor_id=cnt_1.id
    )
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.post(
        f"contractor/booking/{booking_view.id}/accept",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.post(
        f"contractor/booking/{booking_view.id}/accept",
        headers={"Authorization": f"Bearer {cnt_token_1}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_contractor_accept_booking_after_accepted_booking(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    cnt_1 = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt_1, _, cnt_token_1 = app.create_contractor_with_token(cnt_1)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
        preferences_1 = booking.to_preferences(cnt_1.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    app.create_contractor_preference(cnt_token_1, preferences_1)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt.id)
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == status.HTTP_200_OK
    book = models.BookingInviteCreate(
        booking_id=booking_view.id, contractor_id=cnt_1.id
    )
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.post(
        f"contractor/booking/{booking_view.id}/accept",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK

    with Session(app.db.engine) as db:
        quote = models.QuoteCreate.mock(app.faky, booking_view.id, cnt.id, db)

    response = app.api.post(
        f"contractor/booking/{booking_view.id}/quote",
        headers={"Authorization": f"Bearer {cnt_token}"},
        json=quote.model_dump(mode="json"),
    )
    assert response.status_code == status.HTTP_200_OK

    response = app.api.post(
        f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/accept",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK

    response = app.api.post(
        f"contractor/booking/{booking_view.id}/accept",
        headers={"Authorization": f"Bearer {cnt_token_1}"},
    )
    assert response.status_code == APIError.BookingDetailsNotFound.status_code
    assert response.json()["detail"] == APIError.BookingDetailsNotFound.detail


def test_contractor_and_homeowner_get_booking(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt.id)
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.post(
        f"contractor/booking/{booking_view.id}/accept",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        "contractor/bookings", headers={"Authorization": f"Bearer {cnt_token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    models.ContractorBookingList.model_validate_json(response.text)
    response = app.api.get(
        f"contractor/booking/{booking_view.id}/info",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        f"homeowner/booking/{booking_view.id}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        "homeowner/bookings",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    models.HomeownerBookingList.model_validate_json(response.text)


def test_contractor_get_booking_list_with_many_bookings():
    pass


def test_homeowner_get_booking_list_with_many_bookings():
    pass


def test_contractor_get_booking_list_with_no_bookings(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    response = app.api.get(
        "contractor/bookings",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_homeowner_get_booking_list_with_no_bookings(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    response = app.api.get(
        "homeowner/bookings",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_homeowner_create_booking_with_images(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, _ = app.create_contractor_with_token(cnt)
    imgs = models.ImageBase.mocks(app.faky, 2)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2, caption_count=2)
    _ = app.create_homeowner_booking(hmw_token, booking, files=imgs)


def test_homeowner_bookings_list_by_cid_preferences(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)

    TESTZIP = "30332"
    with Session(app.db.engine) as db:
        professions = models.WorkUnit.all_professions(db)
        preferences = models.ContractorPreferencesCreate(
            areas=[TESTZIP], professions=[professions[0][0]]
        )
        app.create_contractor_preference(cnt_token, preferences)

        # MATCHING BOOKING
        units = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids([professions[0][0]], db)
        ]
        booking = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=TESTZIP,
            units=units,
            captions=[],
            address=app.faky.fake.address(),
        )
        booking_view_matching = app.create_homeowner_booking(hmw_token, booking)

        # NON-MATCHING BOOKING
        units = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids([professions[1][0]], db)
        ]
        booking = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=app.faky.fake.postcode(),
            units=units,
            captions=[],
            address=app.faky.fake.address(),
        )
        _booking_view_not_matching = app.create_homeowner_booking(hmw_token, booking)

        response = app.api.get(
            f"homeowner/bookings/{cnt.id}/list",
            headers={"Authorization": f"Bearer {hmw_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        booking_list = models.HomeownerBookingList.model_validate_json(response.text)
        assert len(booking_list.bookings) == 1
        assert booking_list.bookings[0].id == booking_view_matching.id


def test_homeowner_bookings_list_by_cid_preferences_hard(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)

    TESTZIP = "30332"
    with Session(app.db.engine) as db:
        professions = models.WorkUnit.all_professions(db)
        preferences = models.ContractorPreferencesCreate(
            areas=[TESTZIP], professions=[professions[0][0]]
        )
        app.create_contractor_preference(cnt_token, preferences)

        # MATCHING BOOKING
        units = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids([professions[0][0]], db)
        ]
        booking = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=TESTZIP,
            units=units,
            captions=[],
            address=app.faky.fake.address(),
        )
        booking_view_matching = app.create_homeowner_booking(hmw_token, booking)

        # NON-MATCHING BOOKING
        units = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids([professions[0][0]], db)
        ]
        units.append(
            models.BookingUnitCreate(
                work_unit_id=100,
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
        )
        booking = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=app.faky.fake.postcode(),
            units=units,
            captions=[],
            address=app.faky.fake.address(),
        )
        _booking_view_not_matching = app.create_homeowner_booking(hmw_token, booking)

        c = models.ContractorCreate.mock(app.faky, TESTPASS)
        c.first_name = "ALL"
        c.last_name = "Professions"
        c, _, c_token = app.create_contractor_with_token(c)

        units = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids(
                [profession[0] for profession in professions], db
            )
        ]
        booking = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=TESTZIP,
            units=units,
            captions=[],
            address=app.faky.fake.address(),
        )

        preferences = booking.to_preferences(c.id, db)
        app.create_contractor_preference(c_token, preferences)

        response = app.api.get(
            f"homeowner/bookings/{cnt.id}/list",
            headers={"Authorization": f"Bearer {hmw_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        booking_list = models.HomeownerBookingList.model_validate_json(response.text)
        print(booking_list)
        print(len(booking_list.bookings))
        assert len(booking_list.bookings) == 1
        assert booking_list.bookings[0].id == booking_view_matching.id


def test_get_contractor_invite_info(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt.id)
    book = {
        "booking_id": str(book.booking_id),
        "contractor_id": str(book.contractor_id),
    }
    response = app.api.post(
        "homeowner/booking/invite",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=book,
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        f"contractor/booking/{booking_view.id}/invite/{cnt.id}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    print(response.text)
