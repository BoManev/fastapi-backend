from sqlmodel import Session
from api import models
from fastapi import status
from test.utils import (
    TESTPASS,
    TestApp,
    test_app,  # noqa: F401
)


def test_create_contractor_review(test_app: TestApp):
    app: TestApp = test_app
    # Create HW
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    # Create CNT
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    # Create Booking
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=5)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    # HW sends BookingInvite
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
    # CNT accepts BookingInvite
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

    # HW accepts CNT
    response = app.api.post(
        f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/accept",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )

    response = app.api.get(
        "homeowner/projects",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    # HW gets projects
    assert response.status_code == status.HTTP_200_OK
    pid = models.ProjectList.model_validate_json(response.text).projects[0].id

    response = app.api.post(
        f"contractor/project/{pid}/complete",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    # response = app.api.get(
    #     "contractor/private",
    #     headers={"Authorization": f"Bearer {cnt_token}"},
    # )
    review = models.ContractorReviewCreate(
        quality_rating=5,
        budget_rating=5,
        on_schedule_rating=5,
        is_project_public=True,
        budget_words=["YEET", "SKIII"],
    )
    response = app.api.post(
        f"homeowner/project/{pid}/complete/accept",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=review.model_dump(),
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        f"contractor/{cnt.id}/reviews",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    models.ContractorReviewList.model_validate_json(response.text)
    # response = app.api.get(
    #     "contractor/private",
    #     headers={"Authorization": f"Bearer {cnt_token}"},
    # )
    # assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        f"contractor/{cnt.id}/analytics",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    # TODO: after switching to floats check that ratings are 2.5
    analytics = models.ContractorAnalytics.model_validate_json(response.text)
    assert analytics.reviews == 1
    assert analytics.completed_projects == 1
    response = app.api.get(
        f"contractor/review/{pid}/info",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    review = models.ContractorReviewView.model_validate_json(response.text)
    assert set(["YEET", "SKIII"]) == set(review.budget_words)


def test_create_homeowner_review(test_app: TestApp):
    app: TestApp = test_app
    # Create HW
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    # Create CNT
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    # Create Booking
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=5)
    booking_view = app.create_homeowner_booking(hmw_token, booking)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt.id, db)
    app.create_contractor_preference(cnt_token, preferences)
    # HW sends BookingInvite
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
    # CNT accepts BookingInvite
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

    # HW accepts CNT
    response = app.api.post(
        f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/accept",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )

    response = app.api.get(
        "homeowner/projects",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    # HW gets projects
    assert response.status_code == status.HTTP_200_OK
    bid = models.ProjectList.model_validate_json(response.text).projects[0].id

    response = app.api.post(
        f"contractor/project/{bid}/complete",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    # response = app.api.get(
    #     "contractor/private",
    #     headers={"Authorization": f"Bearer {cnt_token}"},
    # )

    review = models.ContractorReviewCreate(
        quality_rating=5,
        budget_rating=5,
        on_schedule_rating=5,
        is_project_public=True,
        budget_words=["YEET", "SKIII"],
    )
    response = app.api.post(
        f"homeowner/project/{bid}/complete/accept",
        headers={"Authorization": f"Bearer {hmw_token}"},
        json=review.model_dump(),
    )
    assert response.status_code == status.HTTP_200_OK

    review = models.HomeownerReviewCreate(
        rating=5,
        rating_words=["YEET", "SKIII"],
    )

    response = app.api.post(
        f"homeowner/{bid}/review",
        headers={"Authorization": f"Bearer {cnt_token}"},
        json=review.model_dump(),
    )
    assert response.status_code == status.HTTP_200_OK

    response = app.api.get(
        f"homeowner/{hmw.id}/reviews",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK

    # response = app.api.get(
    #     "homeowner/private",
    #     headers={"Authorization": f"Bearer {hmw_token}"},
    # )
    # assert response.status_code == status.HTTP_200_OK
    # print(response.text)
