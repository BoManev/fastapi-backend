from sqlmodel import Session
from api import models
from fastapi import status
from test.utils import (
    TESTPASS,
    TestApp,
    test_app,  # noqa: F401
)


def test_post_multiple_qoutes_and_get_quote_info(test_app: TestApp):
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
    # quote 2
    cnt1 = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt1, _, cnt1_token = app.create_contractor_with_token(cnt1)
    with Session(app.db.engine) as db:
        preferences = booking.to_preferences(cnt1.id, db)
    app.create_contractor_preference(cnt1_token, preferences)
    book = models.BookingInviteCreate(booking_id=booking_view.id, contractor_id=cnt1.id)
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
        headers={"Authorization": f"Bearer {cnt1_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    with Session(app.db.engine) as db:
        quote = models.QuoteCreate.mock(app.faky, booking_view.id, cnt1.id, db)
    response = app.api.post(
        f"contractor/booking/{booking_view.id}/quote",
        headers={"Authorization": f"Bearer {cnt1_token}"},
        json=quote.model_dump(mode="json"),
    )
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        f"contractor/booking/{booking_view.id}/quote/info",
        headers={"Authorization": f"Bearer {cnt_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    quote = models.QuoteView.model_validate_json(response.text)
    response = app.api.get(
        f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    quote = models.QuoteView.model_validate_json(response.text)
    response = app.api.get(
        f"homeowner/booking/{booking_view.id}/quote/{cnt1.id}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    quote = models.QuoteView.model_validate_json(response.text)


def test_update_quote_item(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _, hmw_token = app.create_homeowner_with_token(hmw)
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, cnt_token = app.create_contractor_with_token(cnt)
    imgs = models.ImageBase.mocks(app.faky, 1)
    booking = models.BookingDetailCreate.mock(app.faky, unit_count=1, caption_count=1)
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
        f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    quote = models.QuoteView.model_validate_json(response.text)
    #print(quote)
    qiid = quote.items[0].id
    #print(f"qiid{qiid}")
    quote_update = models.QuoteItemUpdate(status=models.QuoteItemStatus.completed)
    response = app.api.post(
        f"contractor/booking/{booking_view.id}/qoute/info/{qiid}/update",
        headers={"Authorization": f"Bearer {cnt_token}"},
        json=quote_update.model_dump(),
    )
    print(response.text)
    assert response.status_code == status.HTTP_200_OK
    response = app.api.get(
        f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/info",
        headers={"Authorization": f"Bearer {hmw_token}"},
    )
    assert response.status_code == status.HTTP_200_OK
    quote = models.QuoteView.model_validate_json(response.text)
    assert quote.items[0].status == models.QuoteItemStatus.completed.value
