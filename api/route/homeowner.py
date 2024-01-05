from datetime import datetime
import uuid
from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from api.core.auth.auth import (
    TokenAuthContractor,
    TokenAuthHomeowner,
    TokenAuthUser,
)
from api.core.db import SessionDB
from api.core.error import APIError
import api.models as models

router = APIRouter()


# =========================== Profile ===========================


@router.post("/signup", response_model=models.HomeownerPublicView)
def signup(
    db: SessionDB,
    homeowner: models.HomeownerCreate = Depends(models.HomeownerCreate.from_form),
    avatar: UploadFile = File(None),
):
    """
    Create new homeowner
    - Default avatar is created if one not provided
    - Errors out when email or phone # are duplicate
    """
    if models.Homeowner.by_email(homeowner.email, db):
        raise APIError.SignupException
    hmw, _ = models.Homeowner.create(homeowner, db, avatar=avatar)
    view = models.HomeownerPublicView.create(hmw)
    db.commit()
    return view


@router.get("/{hid}/public", response_model=models.HomeownerPublicView)
def public_info(hid: uuid.UUID, _user: TokenAuthUser, db: SessionDB):
    """
    Homeowner public view as seen by everyone
    """
    homeowner = models.Homeowner.by_hid(hid, db)
    if not homeowner:
        raise APIError.HomeownerNotFound
    return models.HomeownerPublicView.create(homeowner)


@router.get("/{hid}/private", response_model=models.HomeownerPrivateView)
def private_info(hid: uuid.UUID, _user: TokenAuthUser, db: SessionDB):
    """
    Homeowner private profile view as seen by it's owner
    - Uses the identity decoded from the JWT access token
    Note: contains sensitive information
    """
    homeowner = models.Homeowner.by_hid(hid, db)
    if not homeowner:
        raise APIError.HomeownerNotFound
    user = models.User.by_id(hid, db)
    homeowner = homeowner.model_dump()
    homeowner.pop("id")  # prevent clash with id from user
    past_projects = models.Project.past_projects_by_hid(user.id, db)
    return models.HomeownerPrivateView(
        **homeowner,
        **user.model_dump(),
        past_projects=[(project[2], project[0], project[1]) for project in past_projects],
    )


# =========================== Reviews ===========================


@router.get(
    "/{hid}/reviews",
    response_model=models.HomeownerReviewList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No reviews"}},
)
def reviews(hid: uuid.UUID, user: TokenAuthUser, db: SessionDB):
    """
    Get all reviews for a homeowner as requested by everyone

    Return:
        -   [204 No Content] when no external projects
    """
    hmw = models.Homeowner.by_hid(hid, db)
    if hmw is None:
        raise APIError.HomeownerNotFound
    reviews = models.HomeownerReview.all_by_hid(hid, db)
    print(f"review {reviews}")
    if not reviews:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    reviews = models.HomeownerReviewList(
        reviews=[
            models.HomeownerReviewItem(
                bid=review[0],
                rating=review[1],
                created_at=review[2],
                public=review[3],
                title=review[4],
                avatar_uri=review[5],
            )
            for review in reviews
        ]
    )
    return reviews


@router.post("/{bid}/review")
def rating(
    bid: uuid.UUID,
    review: models.HomeownerReviewCreate,
    user: TokenAuthContractor,
    db: SessionDB,
):
    """
    Contractor posts a new ratings for a homeowner

    Note: Only available after confirmation of completion signal from the Homeowner
    """
    model = models.HomeownerReview.with_booking(bid, db)
    if not model:
        raise APIError.ProjectDetailsNotFound
    if model[1]:
        raise APIError.ReviewAlreadyCreated

    models.HomeownerReview.create(review, model[0], user.id, bid, db)
    db.commit()


@router.get("/review/{bid}/info", response_model=models.HomeownerReviewView)
def review(bid: uuid.UUID, user: TokenAuthUser, db: SessionDB):
    review = models.HomeownerReview.by_bid(bid, db)
    if not review:
        raise APIError.ReviewNotFound
    public = review[1]
    review = review[0].model_dump()
    review["rating_words"] = review["rating_words"].split(",") if review["rating_words"] else None
    view = models.HomeownerReviewView(**review, public=public)
    return view


# =========================== Booking ===========================


@router.post("/booking", response_model=models.HomeownerBookingDetailView)
def booking(
    db: SessionDB,
    user: TokenAuthHomeowner,
    booking: models.BookingDetailCreate = Depends(models.BookingDetailCreate.from_form),
    files: list[UploadFile] = [],
):
    """
    Create a new booking

    param (files):
    - Optional list of images

    param (booking):
    - This is a JSON encoded string with the following format:
    units: Array[{"work_unit_id": number, "quantity": number, "description"?: string}]
    title: string
    zipcode: string
    address: string
    captions: Array[string]

    field (booking::units)
    - List of the work_unit_id's as selected from the quiz
    field (booking::captions)
    - Captions list should have the same length as the number of images;
    - Leave an empty string for images with no caption
    """
    if len(booking.units) == 0:
        raise APIError.BookingWithoutTasks

    if len(files) != len(booking.captions):
        raise APIError.ImageUploadException

    book = models.BookingDetail.create(user.id, booking, db)
    bid = book.id
    models.BookingUnit.create_many(book.id, booking.units, db)
    models.BookingImage.store(book.id, files, booking.captions, db)

    db.commit()

    model = models.BookingDetail.by_hid_active(bid, user.id, db)
    booking: models.BookingDetail = model[0]
    view = models.HomeownerBookingDetailView(
        id=booking.id,
        title=booking.title,
        zipcode=booking.title,
        address=booking.address,
        units=model[1],
        accepted_contractors=model[2],
        images=model[3],
    )
    return view


@router.get("/booking/{bid}/info", response_model=models.HomeownerBookingDetailView)
def booking_info(bid: uuid.UUID, user: TokenAuthHomeowner, db: SessionDB):
    """
    Get booking info by booking ID as seen by the homeowner
    """
    model = models.BookingDetail.by_hid_active(bid, user.id, db)
    if not model:
        raise APIError.BookingDetailsNotFound
    booking: models.BookingDetail = model[0]

    view = models.HomeownerBookingDetailView(
        id=booking.id,
        title=booking.title,
        zipcode=booking.title,
        address=booking.address,
        units=model[1],
        accepted_contractors=model[2],
        images=model[3],
    )
    return view


@router.get(
    "/bookings",
    response_model=models.HomeownerBookingList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No active bookings"}},
)
def bookings_list(user: TokenAuthHomeowner, db: SessionDB):
    """
    Get a list of all active booking IDs for a homeowner
    - For each booking ID not present call `homeowner/booking/{bid}/info`

    Return:
        -   [204 No Content]: when no active bookings
    """
    bookings = models.BookingDetail.by_hid_active_list(user.id, db)
    if not bookings:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    bookings = models.HomeownerBookingList(
        bookings=[
            models.HomeownerBookingItem(**booking[0].model_dump(), booking_units=booking[1])
            for booking in bookings
        ]
    )
    return bookings


@router.get(
    "/bookings/{cid}/list",
    response_model=models.HomeownerBookingList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No active bookings"}},
)
def bookings_list_by_cid_preferences(user: TokenAuthHomeowner, cid: uuid.UUID, db: SessionDB):
    """
    Get a list of all active booking IDs for a homeowner which matches the preferences
    from a contractor ID
    - For each booking ID not present call `homeowner/booking/{bid}/info`

    Return:
        -   [204 No Content]: when no active bookings
    """
    bookings = models.BookingDetail.match_all_by_hid_and_cid(user.id, cid, db)
    if not bookings:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    bookings = models.HomeownerBookingList(
        bookings=[
            models.HomeownerBookingItem(**booking[0].model_dump(), booking_units=booking[1])
            for booking in bookings
        ]
    )

    return bookings


@router.post("/booking/invite")
def booking_invite(db: SessionDB, user: TokenAuthHomeowner, book: models.BookingInviteCreate):
    """
    Send a booking invitation to a contractor
    - Contractor unit preferences must match all booking work_units
        - Professions are internally mapped to units
    - Contractor must not have a previous invitation
    """
    model = models.BookingDetail.match_one(book.booking_id, book.contractor_id, user.id, db)
    if not model:
        raise APIError.NotMatchingPreferences
    invite = models.BookingInvite.create(book, db)
    if not invite:
        raise APIError.BookingInviteNotFound
    db.commit()


@router.post("/booking/{bid}/quote/{cid}/accept")
def quote_accept(cid: uuid.UUID, bid: uuid.UUID, user: TokenAuthHomeowner, db: SessionDB):
    """
    Homeowner accepts a quote, which turns a booking into a project

    - Homeowner must have sent an invitation and the contractor must have accepted it
    """
    booking = models.BookingDetail.by_hid_with_units_is_booked(user.id, bid, db)
    if not booking:
        raise APIError.BookingDetailsNotFound
    details = booking[0]
    _units = booking[1]

    if details.homeowner_id != user.id:
        raise APIError.BookingDetailsNotFound

    invite = models.BookingInvite.by_cid(cid, bid, db)
    if not invite:
        raise APIError.BookingInviteNotFound
    if invite and not invite[0].accepted:
        raise APIError.BookingInviteNotAccepted
    
    quote = models.Quote.by_bid(bid, cid, db)
    if not quote:
        raise APIError.QuoteNotFound
    quote.accepted = True
    db.add(quote)

    project = models.ProjectCreate(booking_id=bid, contractor_id=cid)
    project = models.Project.create(project, db)
    details.is_active = False
    details.is_booked = True
    db.add(details)
    db.commit()


@router.post("/booking/{bid}/quote/reject")
def quote_reject(bid: uuid.UUID, user: TokenAuthHomeowner, db: SessionDB):
    """
    Homeowner rejects a quote
    Note: this doesn't create a new project
    """
    pass


# =========================== Quote ===========================


@router.get("/booking/{bid}/quote/{cid}/info", response_model=models.QuoteView)
def booking_quote_info(bid: uuid.UUID, cid: uuid.UUID, user: TokenAuthHomeowner, db: SessionDB):
    """
    Gets the quote information for a given booking.
    Accepted contractors may not have a quote yet, in that case inform the user
    that a quote is not present

    Return:
        -   [204 No Content]: when no quote is present
    """
    model = models.Quote.by_cid(bid, cid, db)
    if not model:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    items = []
    for item in model[1]:
        items.append(
            models.QuoteItemView(
                **item.get("quote_item", None),
                booking_unit=models.BookingUnitView(**item.get("booking_unit", None)),
                material_unit=models.MaterialView(**item.get("material_unit", None)),
            )
        )
    return models.QuoteView(**model[0].model_dump(), items=items)


# =========================== Projects ===========================


@router.get(
    "/projects",
    response_model=models.ProjectList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No active projects"}},
)
def projects_list(user: TokenAuthHomeowner, db: SessionDB):
    """
    Get a list of all active projects IDs for a homeowner
        - For each booking ID not present call `homeowner/booking/{bid}/info`

    Return:
        -   [204 No Content]: when no active bookins
    """
    projects = models.Project.list_by_hid(user.id, db)
    if not projects:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    projects = models.ProjectList(
        projects=[
            models.ProjectItem(
                title=project[1],
                id=project[2],
                created_at=project[3],
                avatar_uri=project[4],
                first_name=project[5],
                last_name=project[6],
                booking_units=project[7],
            )
            for project in projects
        ]
    )
    return projects


@router.get("/project/{bid}/info", response_model=models.HomeownerProjectView)
def project(bid: uuid.UUID, user: TokenAuthHomeowner, db: SessionDB):
    """
    Get a project's information based on a booking ID as seen by the homeowner

    Note: Bookings and Projects have 1:1 mapping thru the booking_id, eg bid == pid
    """
    # TODO: add quote
    project = models.Project.by_hid(bid, user.id, db)
    if not project:
        raise APIError.ProjectDetailsNotFound
    view = models.HomeownerProjectView(
        contractor=models.ContractorPublicView.create(project[4]),
        booking=models.BookingDetailViewBase(**project[1], booking_images=project[2]),
        project_images=project[3],
        **project[0].model_dump(),
    )
    return view


# TODO: update analytics and update contractor
@router.post("/project/{bid}/complete/accept")
def accept_project_completion(
    bid: uuid.UUID,
    user: TokenAuthHomeowner,
    db: SessionDB,
    review: models.ContractorReviewCreate,
):
    """
    Homeowner accepts contractor's signal for project completion.
    This removes the project from the homeowner and contractor dashboards.
    This will add the project to the homeowner's profile past projects.

    param(public):
    - When set to TRUE it will make the project visible on the contractor portfolio

    - The contractor must have signaled completion first
    """
    project = models.Project.by_id(bid, db)
    if not project:
        raise APIError.ProjectDetailsNotFound
    if not project.signal_completion:
        raise APIError.ProjectCompletionNotSignaled
    if not project.is_active:
        raise APIError.ProjectCompletionAlreadyAccepted

    booking = models.BookingDetail.by_hid_with_units_not_booked(user.id, project.booking_id, db)
    if not booking:
        raise APIError.ProjectDetailsNotFound
    details = booking[0]
    units = booking[1]  # noqa: F841
    if details.homeowner_id != user.id:
        raise APIError.ProjectDetailsNotFound

    if not review.is_project_public:
        project.is_public = False
    else:
        project.is_public = review.is_project_public

    project.is_active = False
    project.completed_at = datetime.utcnow()
    models.ContractorReview.create(
        review, project.contractor_id, details.homeowner_id, project.booking_id, db
    )
    db.add(project)
    db.commit()


@router.post("/project/{bid}/complete/reject")
def reject_project_completion(bid: uuid.UUID, user: TokenAuthHomeowner, db: SessionDB):
    """
    Homeowner rejects contractor's signal for project completion.
    This DOES NOT change the project completion, nor public/private visibility

    - The contractor must have signaled completion first
    """
    project = models.Project.by_id(bid, db)
    if not project:
        raise APIError.ProjectDetailsNotFound
    if not project.signal_completion:
        raise APIError.ProjectCompletionNotSignaled

    booking = models.BookingDetail.by_hid_with_units_not_booked(user.id, project.booking_id, db)
    if not booking:
        raise APIError.ProjectDetailsNotFound
    details = booking[0]
    units = booking[1]  # noqa: F841
    if details.homeowner_id != user.id:
        raise APIError.ProjectDetailsNotFound

    project.is_active = True
    project.signal_completion = False
    db.add(project)
    db.commit()
