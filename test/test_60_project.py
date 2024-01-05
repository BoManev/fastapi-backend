from sqlmodel import Session
from api import models
from fastapi import status
from test.utils import (
    TESTPASS,
    TestApp,
    test_app,  # noqa: F401
)


def test_create_project_by_homeowner_accepts_quote(test_app: TestApp):
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


def test_get_homeowner_projects_list_and_fetch_infos(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)

    ## PROJECT 1
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

    imgs = models.ImageBase.mocks(app.faky, 2)
    response = app.api.post(
        f"contractor/project/{booking_view.id}/images",
        headers={"Authorization": f"Bearer {cnt_token}"},
        files=imgs,
        data={"captions": [app.faky.fake.word() for _ in range(2)]},
    )
    assert response.status_code == status.HTTP_200_OK

    ## PROJECT 2
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

    imgs = models.ImageBase.mocks(app.faky, 2)
    response = app.api.post(
        f"contractor/project/{booking_view.id}/images",
        headers={"Authorization": f"Bearer {cnt_token}"},
        files=imgs,
        data={"captions": [app.faky.fake.word() for _ in range(2)]},
    )

    response = app.api.get(
        "homeowner/projects",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    pids = [
        project.id for project in models.ProjectList.model_validate_json(response.text).projects
    ]
    response = app.api.get(
        f"homeowner/project/{pids[0]}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        f"homeowner/project/{pids[1]}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_get_contractor_projects_list_and_fetch_infos(test_app: TestApp):
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

    response = app.api.get("contractor/projects", headers={"Authorization": f"Bearer {cnt_token}"})
    assert response.status_code == status.HTTP_200_OK
    pid = models.ProjectList.model_validate_json(response.text).projects[0].id

    response = app.api.get(
        f"contractor/project/{pid}/info",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_contractor_get_project_list_with_many_projects():
    pass


def test_homeowner_get_project_list_with_many_projects():
    pass


def test_contractor_get_project_list_with_no_projects(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    response = app.api.get(
        "contractor/projects",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_homeowner_get_project_list_with_no_projects(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    response = app.api.get(
        "homeowner/projects",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


def test_contractor_upload_images_to_project(test_app: TestApp):
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
    response = app.api.get(
        "contractor/projects",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    pid = models.ProjectList.model_validate_json(response.text).projects[0].id

    imgs = models.ImageBase.mocks(app.faky, 2)
    response = app.api.post(
        f"contractor/project/{pid}/images",
        headers={"Authorization": f"Bearer {cnt_token}"},
        files=imgs,
        data={"captions": [app.faky.fake.word() for _ in range(2)]},
    )
    assert response.status_code == status.HTTP_200_OK


def test_homeowner_upload_images_to_project(test_app: TestApp):
    pass


# TODO: test without bookings images and test without project images
def test_get_public_portfolio_project(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    imgs = models.ImageBase.mocks(app.faky, 2)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=2, caption_count=2)
    booking_view = app.create_homeowner_booking(hmw_token, booking, files=imgs)
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
    response = app.api.get(
        "contractor/projects",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    pid = models.ProjectList.model_validate_json(response.text).projects[0].id

    imgs = models.ImageBase.mocks(app.faky, 2)
    response = app.api.post(
        f"contractor/project/{pid}/images",
        headers={"Authorization": f"Bearer {cnt_token}"},
        files=imgs,
        data={"captions": [app.faky.fake.word() for _ in range(2)]},
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.post(
        f"contractor/project/{pid}/complete",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    review = models.ContractorReviewCreate(
        quality_rating=5, budget_rating=5, on_schedule_rating=5, is_project_public=True
    )
    response = app.api.post(
        f"homeowner/project/{pid}/complete/accept",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=review.model_dump(),
    )
    assert response.status_code == status.HTTP_200_OK

    response = app.api.get(
        f"contractor/portfolio/{cnt.id}/public/projects",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    pids = models.PortfolioPublicProjectsList.model_validate_json(response.text).public_projects
    assert len(pids) == 1

    response = app.api.get(
        f"contractor/portfolio/{cnt.id}/public/project/{pid}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = models.PortfolioPublicProjectView.model_validate_json(response.text)


def test_get_public_portfolio_project_without_images(test_app: TestApp):
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
    response = app.api.get(
        "contractor/projects",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    pid = models.ProjectList.model_validate_json(response.text).projects[0].id

    response = app.api.post(
        f"contractor/project/{pid}/complete",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    review = models.ContractorReviewCreate(
        quality_rating=5, budget_rating=5, on_schedule_rating=5, is_project_public=True
    )
    response = app.api.post(
        f"homeowner/project/{pid}/complete/accept",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=review.model_dump(),
    )
    assert response.status_code == status.HTTP_200_OK

    response = app.api.get(
        f"contractor/portfolio/{cnt.id}/public/projects",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    pids = models.PortfolioPublicProjectsList.model_validate_json(response.text).public_projects
    assert len(pids) == 1

    response = app.api.get(
        f"contractor/portfolio/{cnt.id}/public/project/{pid}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    response = models.PortfolioPublicProjectView.model_validate_json(response.text)