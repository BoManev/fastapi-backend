from api.core.db import DB
import api.models as models
from sqlmodel import Session
from test.utils import TESTPASS, TestApp


def generate_mocks():
    app = TestApp.for_mocks(DB())
    TESTZIP = str(30332)
    TESTZIP_NO_MATCH = str(55555)
    hmw, _, hmw_token = app.create_homeowner_with_token(
        models.HomeownerCreate(
            email="hmw@test.com",
            password=TESTPASS,
            phone_number="111-111-4444",
            first_name="Homeowner",
            last_name="Test",
        ),
    )
    cnt, _, cnt_token = app.create_contractor_with_token(
        models.ContractorCreate(
            email="cnt@test.com",
            password=TESTPASS,
            phone_number="111-111-5555",
            first_name="Contractor",
            last_name="Test",
            bio="Im a test contractor",
        ),
    )

    # MATCHING BOOKING
    with Session(app.db.engine) as db:
        professions = models.WorkUnit.all_professions(db)
        units_match = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids(
                [professions[0][0], professions[1][0]], db
            )
        ]
        booking_match = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=TESTZIP,
            units=units_match,
            captions=[],
            address=app.faky.fake.address(),
        )

        units_non_match = [
            models.BookingUnitCreate(
                work_unit_id=unit[0],
                quantity=app.faky.fake.random_number(digits=2),
                description=app.faky.fake.word(),
            )
            for unit in models.WorkUnit.professions_to_ids(
                [professions[2][0], professions[3][0]], db
            )
        ]
        booking_non_match = models.BookingDetailCreate(
            title=app.faky.fake.word(),
            zipcode=TESTZIP,
            units=units_non_match,
            captions=[],
            address=app.faky.fake.address(),
        )

    imgs = models.ImageBase.mocks(app.faky, 5)
    prf = models.PortfolioProjectCreate.mock(app.faky, unit_count=5, caption_count=5)
    app.create_contractor_portfolio(cnt_token, prf, imgs)

    # ================== Homeowner Mocks ================== #
    # Bookings
    for _ in range(3):
        # only read from this session (no commit)
        with Session(app.db.engine) as db:
            booking_match.title = app.faky.fake.word()
            booking_match.address = app.faky.fake.address()
            booking_view = app.create_homeowner_booking(hmw_token, booking_match)
            for _ in range(3):
                c = models.ContractorCreate.mock(app.faky, TESTPASS)
                c, _, c_token = app.create_contractor_with_token(c)

                imgs = models.ImageBase.mocks(app.faky, 2)
                prf = models.PortfolioProjectCreate.mock(
                    app.faky, unit_count=2, caption_count=2
                )
                app.create_contractor_portfolio(c_token, prf, imgs)

                preferences = booking_match.to_preferences(c.id, db)
                app.create_contractor_preference(c_token, preferences)

                book = models.BookingInviteCreate(
                    booking_id=booking_view.id, contractor_id=c.id
                )
                book = {
                    "booking_id": str(book.booking_id),
                    "contractor_id": str(book.contractor_id),
                }
                _ = app.api.post(
                    "homeowner/booking/invite",
                    headers={"Authorization": f"Bearer {hmw_token}"},
                    json=book,
                )
                _ = app.api.post(
                    f"contractor/booking/{booking_view.id}/accept",
                    headers={"Authorization": f"Bearer {c_token}"},
                )
                quote = models.QuoteCreate.mock(app.faky, booking_view.id, c.id, db)
                _ = app.api.post(
                    f"contractor/booking/{booking_view.id}/quote",
                    headers={"Authorization": f"Bearer {c_token}"},
                    json=quote.model_dump(mode="json"),
                )

    # Projects
    for _ in range(3):
        with Session(app.db.engine) as db:
            booking_match.title = app.faky.fake.word()
            booking_match.address = app.faky.fake.address()
            booking_view = app.create_homeowner_booking(hmw_token, booking_match)

            c = models.ContractorCreate.mock(app.faky, TESTPASS)
            c, _, c_token = app.create_contractor_with_token(c)

            imgs = models.ImageBase.mocks(app.faky, 2)
            prf = models.PortfolioProjectCreate.mock(
                app.faky, unit_count=2, caption_count=2
            )
            app.create_contractor_portfolio(c_token, prf, imgs)

            preferences = booking_match.to_preferences(c.id, db)
            app.create_contractor_preference(c_token, preferences)

            book = models.BookingInviteCreate(
                booking_id=booking_view.id, contractor_id=c.id
            )
            book = {
                "booking_id": str(book.booking_id),
                "contractor_id": str(book.contractor_id),
            }
            _ = app.api.post(
                "homeowner/booking/invite",
                headers={"Authorization": f"Bearer {hmw_token}"},
                json=book,
            )
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/accept",
                headers={"Authorization": f"Bearer {c_token}"},
            )
            quote = models.QuoteCreate.mock(app.faky, booking_view.id, c.id, db)
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/quote",
                headers={"Authorization": f"Bearer {c_token}"},
                json=quote.model_dump(mode="json"),
            )
            _ = app.api.post(
                f"homeowner/booking/{booking_view.id}/quote/{c.id}/accept",
                headers={"Authorization": f"Bearer {hmw_token}"},
            )

    # Past projects and reviews
    for _ in range(3):
        # only read from this session (no commit)
        with Session(app.db.engine) as db:
            booking_match.title = app.faky.fake.word()
            booking_match.address = app.faky.fake.address()
            booking_view = app.create_homeowner_booking(hmw_token, booking_match)

            c = models.ContractorCreate.mock(app.faky, TESTPASS)
            c, _, c_token = app.create_contractor_with_token(c)

            imgs = models.ImageBase.mocks(app.faky, 2)
            prf = models.PortfolioProjectCreate.mock(
                app.faky, unit_count=2, caption_count=2
            )
            app.create_contractor_portfolio(c_token, prf, imgs)

            preferences = booking_match.to_preferences(c.id, db)
            app.create_contractor_preference(c_token, preferences)

            book = models.BookingInviteCreate(
                booking_id=booking_view.id, contractor_id=c.id
            )
            book = {
                "booking_id": str(book.booking_id),
                "contractor_id": str(book.contractor_id),
            }
            _ = app.api.post(
                "homeowner/booking/invite",
                headers={"Authorization": f"Bearer {hmw_token}"},
                json=book,
            )
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/accept",
                headers={"Authorization": f"Bearer {c_token}"},
            )
            quote = models.QuoteCreate.mock(app.faky, booking_view.id, c.id, db)
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/quote",
                headers={"Authorization": f"Bearer {c_token}"},
                json=quote.model_dump(mode="json"),
            )
            _ = app.api.post(
                f"homeowner/booking/{booking_view.id}/quote/{c.id}/accept",
                headers={"Authorization": f"Bearer {hmw_token}"},
            )
            _ = app.api.post(
                f"contractor/project/{booking_view.id}/complete",
                headers={"Authorization": f"Bearer {c_token}"},
            )
            review = models.ContractorReviewCreate(
                quality_rating=5,
                budget_rating=4,
                on_schedule_rating=3,
                is_project_public=True,
                budget_words=["Worthwhile", "Well-Priced"],
            )
            _ = app.api.post(
                f"homeowner/project/{booking_view.id}/complete/accept",
                headers={"Authorization": f"Bearer {hmw_token}"},
                json=review.model_dump(),
            )
            review = models.HomeownerReviewCreate(
                rating=5,
                rating_words=["Respectful", "Good Communication"],
            )
            _ = app.api.post(
                f"homeowner/{booking_view.id}/review",
                headers={"Authorization": f"Bearer {c_token}"},
                json=review.model_dump(),
            )

# ================== Random Contractor Mocks MATCHING ================== #

    with Session(app.db.engine) as db:
        for _ in range(10):
            c = models.ContractorCreate.mock(app.faky, TESTPASS)
            c, _, c_token = app.create_contractor_with_token(c)
            preferences = booking_match.to_preferences(c.id, db)
            preferences.professions.append(professions[4][0])
            app.create_contractor_preference(c_token, preferences)

            imgs = models.ImageBase.mocks(app.faky, 2)
            prf = models.PortfolioProjectCreate.mock(
                app.faky, unit_count=2, caption_count=2
            )
            app.create_contractor_portfolio(c_token, prf, imgs)

# ======= Random Contractor Mocks NON-MATCHING ========= #
    with Session(app.db.engine) as db:
        for _ in range(10):
            c = models.ContractorCreate.mock(app.faky, TESTPASS)
            c, _, c_token = app.create_contractor_with_token(c)

            preferences = booking_non_match.to_preferences(c.id, db)
            app.create_contractor_preference(c_token, preferences)

            imgs = models.ImageBase.mocks(app.faky, 2)
            prf = models.PortfolioProjectCreate.mock(
                app.faky, unit_count=2, caption_count=2
            )
            app.create_contractor_portfolio(c_token, prf, imgs)

# ======= Contractor Mocks for all professions ========= #
    with Session(app.db.engine) as db:
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

        imgs = models.ImageBase.mocks(app.faky, 2)
        prf = models.PortfolioProjectCreate.mock(
            app.faky, unit_count=2, caption_count=2
        )
        app.create_contractor_portfolio(c_token, prf, imgs)

# ======= Contractor Mocks for each professions ========= #
    with Session(app.db.engine) as db:
        for profession in professions:
            for _ in range(5):
                c = models.ContractorCreate.mock(app.faky, TESTPASS)
                c, _, c_token = app.create_contractor_with_token(c)
                units = [
                    models.BookingUnitCreate(
                        work_unit_id=unit[0],
                        quantity=app.faky.fake.random_number(digits=2),
                        description=app.faky.fake.word(),
                    )
                    for unit in models.WorkUnit.professions_to_ids([profession[0]], db)
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

                imgs = models.ImageBase.mocks(app.faky, 2)
                prf = models.PortfolioProjectCreate.mock(
                    app.faky, unit_count=2, caption_count=2
                )
                app.create_contractor_portfolio(c_token, prf, imgs)

    # ================== Contractor Mocks ================== #

    preferences = booking_match.to_preferences(cnt.id, db)
    app.create_contractor_preference(cnt_token, preferences)

    with Session(app.db.engine) as db:
        for _ in range(3):
            h = models.HomeownerCreate.mock(app.faky, TESTPASS)
            h, _, h_token = app.create_homeowner_with_token(h)
            booking_match.title = app.faky.fake.word()
            booking_match.address = app.faky.fake.address()
            booking_view = app.create_homeowner_booking(h_token, booking_match)
            book = models.BookingInviteCreate(
                booking_id=booking_view.id, contractor_id=cnt.id
            )
            book = {
                "booking_id": str(book.booking_id),
                "contractor_id": str(book.contractor_id),
            }
            _ = app.api.post(
                "homeowner/booking/invite",
                headers={"Authorization": f"Bearer {h_token}"},
                json=book,
            )

    # Bookings
    with Session(app.db.engine) as db:
        for _ in range(3):
            h = models.HomeownerCreate.mock(app.faky, TESTPASS)
            h, _, h_token = app.create_homeowner_with_token(h)
            booking_match.title = app.faky.fake.word()
            booking_match.address = app.faky.fake.address()
            booking_view = app.create_homeowner_booking(h_token, booking_match)
            book = models.BookingInviteCreate(
                booking_id=booking_view.id, contractor_id=cnt.id
            )
            book = {
                "booking_id": str(book.booking_id),
                "contractor_id": str(book.contractor_id),
            }
            _ = app.api.post(
                "homeowner/booking/invite",
                headers={"Authorization": f"Bearer {h_token}"},
                json=book,
            )
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/accept",
                headers={"Authorization": f"Bearer {cnt_token}"},
            )
            quote = models.QuoteCreate.mock(app.faky, booking_view.id, cnt.id, db)
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/quote",
                headers={"Authorization": f"Bearer {cnt_token}"},
                json=quote.model_dump(mode="json"),
            )

        with Session(app.db.engine) as db:
            for _ in range(3):
                h = models.HomeownerCreate.mock(app.faky, TESTPASS)
                h, _, h_token = app.create_homeowner_with_token(h)
                booking_match.title = app.faky.fake.word()
                booking_match.address = app.faky.fake.address()
                booking_view = app.create_homeowner_booking(h_token, booking_match)
                book = models.BookingInviteCreate(
                    booking_id=booking_view.id, contractor_id=cnt.id
                )
                book = {
                    "booking_id": str(book.booking_id),
                    "contractor_id": str(book.contractor_id),
                }
                _ = app.api.post(
                    "homeowner/booking/invite",
                    headers={"Authorization": f"Bearer {h_token}"},
                    json=book,
                )
                _ = app.api.post(
                    f"contractor/booking/{booking_view.id}/accept",
                    headers={"Authorization": f"Bearer {cnt_token}"},
                )
                quote = models.QuoteCreate.mock(app.faky, booking_view.id, cnt.id, db)
                _ = app.api.post(
                    f"contractor/booking/{booking_view.id}/quote",
                    headers={"Authorization": f"Bearer {cnt_token}"},
                    json=quote.model_dump(mode="json"),
                )
                _ = app.api.post(
                    f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/accept",
                    headers={"Authorization": f"Bearer {h_token}"},
                )

    # Past projects and reviews
    for _ in range(3):
        with Session(app.db.engine) as db:
            h = models.HomeownerCreate.mock(app.faky, TESTPASS)
            h, _, h_token = app.create_homeowner_with_token(h)
            booking_match.title = app.faky.fake.word()
            booking_match.address = app.faky.fake.address()
            booking_view = app.create_homeowner_booking(h_token, booking_match)

            imgs = models.ImageBase.mocks(app.faky, 2)
            prf = models.PortfolioProjectCreate.mock(
                app.faky, unit_count=2, caption_count=2
            )
            app.create_contractor_portfolio(cnt_token, prf, imgs)

            preferences = booking_match.to_preferences(c.id, db)
            app.create_contractor_preference(cnt_token, preferences)

            book = models.BookingInviteCreate(
                booking_id=booking_view.id, contractor_id=cnt.id
            )
            book = {
                "booking_id": str(book.booking_id),
                "contractor_id": str(book.contractor_id),
            }
            _ = app.api.post(
                "homeowner/booking/invite",
                headers={"Authorization": f"Bearer {h_token}"},
                json=book,
            )
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/accept",
                headers={"Authorization": f"Bearer {cnt_token}"},
            )
            quote = models.QuoteCreate.mock(app.faky, booking_view.id, cnt.id, db)
            _ = app.api.post(
                f"contractor/booking/{booking_view.id}/quote",
                headers={"Authorization": f"Bearer {cnt_token}"},
                json=quote.model_dump(mode="json"),
            )
            _ = app.api.post(
                f"homeowner/booking/{booking_view.id}/quote/{cnt.id}/accept",
                headers={"Authorization": f"Bearer {h_token}"},
            )
            _ = app.api.post(
                f"contractor/project/{booking_view.id}/complete",
                headers={"Authorization": f"Bearer {cnt_token}"},
            )
            review = models.ContractorReviewCreate(
                quality_rating=3,
                budget_rating=4,
                on_schedule_rating=5,
                is_project_public=True,
                budget_words=["Worthwhile", "Well-Priced"],
            )
            _ = app.api.post(
                f"homeowner/project/{booking_view.id}/complete/accept",
                headers={"Authorization": f"Bearer {h_token}"},
                json=review.model_dump(),
            )
            review = models.HomeownerReviewCreate(
                rating=4,
                rating_words=["Respectful", "Good Communication"],
            )
            _ = app.api.post(
                f"homeowner/{booking_view.id}/review",
                headers={"Authorization": f"Bearer {cnt_token}"},
                json=review.model_dump(),
            )


# Public Projects and Reviews
# from fastapi_events.handlers.local import local_handler
# from fastapi_events.typing import Event

# @local_handler.register(event_name="test")
# def handle_all_cat_events(event: Event):
#     event_name, payload = event
#     print(f"[name] {event_name} [payload] {payload}")
