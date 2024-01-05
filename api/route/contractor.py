from typing import Annotated, List
import uuid
from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from api.core.auth.auth import (
    TokenAuthContractor,
    TokenAuthHomeowner,
    TokenAuthUser,
)
from api.core.db import SessionDB
from api.core.error import APIError
from api.core.search_engine.projection_engine import RecommendationEngine
import api.models as models

router = APIRouter()


# =========================== Profile =========================== #


@router.post("/signup", response_model=models.ContractorPublicView)
def signup(
    db: SessionDB,
    contractor: models.ContractorCreate = Depends(models.ContractorCreate.from_form),
    avatar: UploadFile = File(None),
):
    """
    Create new contractor
    - Default avatar is created if one not provided
    - Errors out when email or phone # are duplicate
    """
    if models.Contractor.by_email(contractor.email, db):
        raise APIError.SignupException
    cnt, _ = models.Contractor.create(contractor, db, avatar=avatar)
    view = models.ContractorPublicView.create(cnt)
    db.commit()
    return view


@router.get("/{cid}/public", response_model=models.ContractorPublicView)
def public_info(cid: uuid.UUID, _user: TokenAuthUser, db: SessionDB):
    """
    Contractor public view as seen by everyone
    """
    cnt = models.Contractor.by_cid(cid, db)
    if cnt is None:
        raise APIError.ContractorNotFound
    model = models.ContractorPublicView.create(cnt[0], professions=cnt[1], areas=cnt[2])
    print(f"model: ${model}")
    return model


@router.get("/{cid}/private", response_model=models.ContractorPrivateView)
def private_info(cid: uuid.UUID, _user: TokenAuthUser, db: SessionDB):
    """
    Contractor private profile view as seen by it's owner
    - Uses the identity decoded from the JWT access token
    Note: contains sensitive information
    """
    cnt = models.Contractor.by_cid(cid, db)
    user = models.User.by_id(cid, db)
    if cnt is None:
        raise APIError.ContractorNotFound
    if user is None:
        raise APIError.ContractorNotFound
    contractor = cnt[0].model_dump()
    contractor.pop("id")  # prevent clash with id from user
    return models.ContractorPrivateView(
        **contractor, **user.model_dump(), professions=cnt[1], areas=cnt[2]
    )


@router.get("/{cid}/analytics", response_model=models.ContractorAnalytics)
def analytics(cid: uuid.UUID, user: TokenAuthUser, db: SessionDB):
    analytics = models.ContractorAnalytics.by_cid(cid, db)
    if not analytics:
        raise APIError.ContractorNotFound
    return analytics


# =========================== Preferences =========================== #


@router.get("/{cid}/preferences", response_model=models.ContractorPreferencesView)
def preferences(cid: uuid.UUID, _user: TokenAuthUser, db: SessionDB):
    """
    Get all preferences for a contractor as seen by everyone

    Returns professions and not work unit strings
    """
    cnt = models.Contractor.by_cid(cid, db)
    if cnt is None:
        raise APIError.ContractorNotFound
    units = models.ContractorUnitPreference.by_cid(cnt[0].id, db)
    areas = models.ContractorAreaPreference.by_cid(cnt[0].id, db)
    return models.ContractorPreferencesView.create(areas, units, db)


@router.post("/preferences", response_model=models.ContractorPreferencesView)
def preferences_update(
    preferences: models.ContractorPreferencesCreate,
    user: TokenAuthContractor,
    db: SessionDB,
):
    """
    Create or update contractor's OWN preferences

    Note: If there are prior preferences all of them are deleted in favor of the
    new ones
    - Contractors initially start with no preferences
    """
    models.ContractorUnitPreference.clear(user.id, db)
    models.ContractorAreaPreference.clear(user.id, db)
    units = models.ContractorUnitPreference.create_from_professions(
        user.id, preferences.professions, db
    )
    areas = models.ContractorAreaPreference.create(user.id, preferences.areas, db)
    view = models.ContractorPreferencesView.create(areas, units, db)
    db.commit()
    return view


# =========================== Reviews =========================== #


@router.get(
    "/{cid}/reviews",
    response_model=models.ContractorReviewList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No reviews"}},
)
def reviews(cid: uuid.UUID, user: TokenAuthUser, db: SessionDB):
    """
    Get all reviews for a contractor as requested by everyone

    Return:
        -   [204 No Content] when no external projects
    """
    cnt = models.Contractor.by_cid(cid, db)
    if cnt is None:
        raise APIError.ContractorNotFound

    reviews = models.ContractorReview.all_by_cid(cid, db)
    if not reviews:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    reviews = models.ContractorReviewList(
        reviews=[
            models.ContractorReviewItem(
                bid=review[0],
                agg_rating=(sum([review[1], review[2], review[3]]) / 3),
                created_at=review[4],
                public=review[5],
                title=review[6],
                avatar_uri=review[7],
                professions=review[8],
            )
            for review in reviews
        ]
    )
    return reviews


# TODO: add more info if it's public
# new field, if the field is None, then it's not public
# otherwise parse the json
@router.get("/review/{bid}/info")
def review(bid: uuid.UUID, user: TokenAuthUser, db: SessionDB):
    review = models.ContractorReview.by_bid(bid, db)
    if not review:
        raise APIError.ReviewNotFound
    public = review[1]
    review = review[0].model_dump()
    review["quality_words"] = (
        review["quality_words"].split(",") if review["quality_words"] else None
    )
    review["schedule_words"] = (
        review["schedule_words"].split(",") if review["schedule_words"] else None
    )
    review["budget_words"] = (
        review["budget_words"].split(",") if review["budget_words"] else None
    )
    view = models.ContractorReviewView(**review, public=public)
    return view


# =========================== Portfolio =========================== #


@router.get(
    "/portfolio/{cid}/external/projects",
    response_model=models.PortfolioExternalProjectsList,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "No external portfolio projects"}
    },
)
def portfolio_external_projects_list(
    cid: uuid.UUID, user: TokenAuthUser, db: SessionDB
):
    """
    Get a list of all external portfolio project IDs for a contractor
    - For each portfolio project ID not present call `contractor/portfolio/{cid}/external/project/{bid}/info`

    Return:
        -   [204 No Content] when no external projects
    """
    cnt = models.Contractor.by_cid(cid, db)
    if cnt is None:
        raise APIError.ContractorNotFound

    projects = models.ExternalPortfolioProject.by_cid(cid, db)
    if not projects:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    projects = models.PortfolioExternalProjectsList(
        external_projects=[
            models.PortfolioExternalProjectItem(
                id=project.id, title=project.title, created_at=project.created_at
            )
            for project in projects
        ]
    )
    return projects


@router.get(
    "/portfolio/{cid}/external/project/{bid}/info",
    response_model=models.PortfolioExternalProjectView,
)
def portfolio_external_project(
    cid: uuid.UUID, bid: uuid.UUID, user: TokenAuthUser, db: SessionDB
):
    """
    Get the information for an external portfolio project as seen by everyone

    Note: The external project is uploaded by the contractors, eg not sitesync
    verified
    """
    cnt = models.Contractor.by_cid(cid, db)
    if cnt is None:
        raise APIError.ContractorNotFound
    project = models.ExternalPortfolioProject.by_cid_and_bid(cid, bid, db)
    if not project:
        raise APIError.ExternalPortfolioProjectNotFound

    return models.PortfolioExternalProjectView.create(
        project[0], project[1], project[2], db
    )


@router.get(
    "/portfolio/{cid}/public/projects",
    response_model=models.PortfolioPublicProjectsList,
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "No public portfolio projects"}
    },
)
def portfolio_public_projects_list(cid: uuid.UUID, user: TokenAuthUser, db: SessionDB):
    """
    Get a list of all public portfolio project IDs for a contractor
    - For each portfolio project ID not present call `contractor/portfolio/{cid}/public/project/{bid}/info`

    Return:
        -   [204 No Content] when no public portfolio projects
    """
    cnt = models.Contractor.by_cid(cid, db)

    if cnt is None:
        raise APIError.ContractorNotFound
    projects = models.ContractorReview.public_list_by_cid(cid, db)
    if not projects:
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    projects = models.PortfolioPublicProjectsList(
        public_projects=[
            models.PortfolioPublicProjectItem(
                id=project[0],
                created_at=project[1],
                completed_at=project[2],
                title=project[3],
                avatar_uri=project[4],
                ratings=project[5],
            )
            for project in projects
        ]
    )
    return projects


@router.get(
    "/portfolio/{cid}/public/project/{bid}/info",
    response_model=models.PortfolioPublicProjectView,
)
def portfolio_public_project(
    cid: uuid.UUID, bid: uuid.UUID, user: TokenAuthUser, db: SessionDB
):
    """
    Get the information for a public portfolio project as seen by everyone

    Note: The public projects are made visible by the homeowner at the end of a project
    """
    cnt = models.Contractor.by_cid(cid, db)
    if cnt is None:
        raise APIError.ContractorNotFound
    print(cnt)
    project = models.Project.public_by_cid(cid, bid, db)
    print(project)
    if not project:
        raise APIError.PublicPortfolioProjectNotFound
  
    return models.PortfolioPublicProjectView.create(
        project[0], project[1], project[2], project[3], project[4], db
    )


@router.post("/portfolio/external/project", response_model=models.UploadPortfolioView)
def portfolio_external_project_upload(
    db: SessionDB,
    user: TokenAuthContractor,
    external_project: models.PortfolioProjectCreate = Depends(
        models.PortfolioProjectCreate.from_form
    ),
    files: list[UploadFile] = [],
):
    """
    Create a new portfolio external project

    param (files):
    - Optional list of images

    param (external_project):
    - This is a JSON encoded string with the following format:
    units: Array[uuid.UUID]
    title: string
    zipcode: string
    description: string
    captions: Array[string]

    field (external_project::units)
    - List of the work_unit_id's as selected from the quiz
    field (external_project::captions)
    - Captions list should have the same length as the number of images;
    - Leave an empty string for images with no caption
    """
    if len(files) != len(external_project.captions):
        raise APIError.ImageUploadException

    imgs_len = models.ExternalPortfolioProject.create(
        external_project, user.id, files, db
    )
    view = models.UploadPortfolioView(img_uploaded=imgs_len)
    db.commit()
    return view


# =========================== Booking =========================== #


@router.get(
    "/booking/invites",
    response_model=models.ContractorBookingList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No active bookings"}},
)
def booking_invites_list(user: TokenAuthContractor, db: SessionDB):
    """
    Get a list of all active booking invites IDs for a contractor
    - For each booking ID not present call `contractor/booking/{bid}/info`

    Return:
        -   [204 No Content] when no active booking invites
    """
    invites = models.BookingInvite.invites_ids_by_cid(user.id, db)
    if not invites:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    invites = models.ContractorBookingList(
        bookings=[
            models.ContractorBookingItem(
                id=invite[0],
                title=invite[1],
                created_at=invite[2],
                avatar_uri=invite[3],
                first_name=invite[4],
                last_name=invite[5],
                booking_units=invite[6],
            )
            for invite in invites
        ]
    )
    return invites


@router.get(
    "/bookings",
    response_model=models.ContractorBookingList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No active bookings"}},
)
def bookings_acccepted_list(user: TokenAuthContractor, db: SessionDB):
    """
    Get a list of all bookings with accepted invite IDs for a contractor
    - For each booking ID not present call `contractor/booking/{bid}/info`

    Return:
        -   [204 No Content] when no active bookings
    """
    bookings = models.BookingInvite.accepted_by_cid(user.id, db)
    if not bookings:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    bookings = models.ContractorBookingList(
        bookings=[
            models.ContractorBookingItem(
                id=invite[0],
                title=invite[1],
                created_at=invite[2],
                avatar_uri=invite[3],
                first_name=invite[4],
                last_name=invite[5],
                booking_units=invite[6],
            )
            for invite in bookings
        ]
    )
    return bookings


# TODO: Only display address once invite is accepted
@router.get("/booking/{bid}/info", response_model=models.ContractorBookingDetailView)
def booking_info(bid: uuid.UUID, user: TokenAuthContractor, db: SessionDB):
    """
    Get booking info by booking ID as seen by the contractor
    """
    booking = models.BookingDetail.by_bid_with_units_is_booked(bid, db)
    if not booking:
        raise APIError.BookingDetailsNotFound
    details = booking[0]
    units = booking[1]

    homeonwer = models.Homeowner.by_hid(details.homeowner_id, db)
    images = models.BookingImage.all_by_bid(bid, db)
    view = models.ContractorBookingDetailView(
        id=details.id,
        title=details.title,
        zipcode=details.zipcode,
        homeowner=models.HomeownerPublicView.create(homeonwer),
        units=models.BookingUnitView.create(units, db),
        images=[
            models.ImageView(uri=image.uri, caption=image.caption) for image in images
        ],
    )
    return view


@router.post("/booking/{bid}/accept")
def booking_invite_accept(bid: uuid.UUID, user: TokenAuthContractor, db: SessionDB):
    """
    Accept a homeowner's booking invitation.
    Error is raised if:
        - bid is invalid
        - not contractor invitation is present
        - already accepted
    """
    booking = models.BookingDetail.by_bid_with_units_is_booked(bid, db)
    if not booking:
        raise APIError.BookingDetailsNotFound
    if booking[0].is_booked:
        raise APIError.BookingInviteAlreadyAccepted

    invite = models.BookingInvite.match(user.id, bid, db)
    if not invite:
        raise APIError.BookingInviteNotFound
    if invite and invite[0].rejected:
        raise APIError.BookingInviteAlreadyRejected
    if invite and invite[0].accepted:
        raise APIError.BookingInviteAlreadyAccepted

    invite[0].accepted = True
    invite[0].rejected = False
    db.add(invite[0])
    db.commit()


@router.post("/booking/{bid}/reject")
def booking_invite_reject(bid: uuid.UUID, user: TokenAuthContractor, db: SessionDB):
    """
    Reject a homeowner's booking invitation.
    Error is raised if:
        - bid is invalid
        - not contractor invitation is present
        - already rejected
    """
    booking = models.BookingDetail.by_bid_with_units_is_booked(bid, db)
    if not booking:
        raise APIError.BookingDetailsNotFound
    if booking[0].is_booked:
        raise APIError.BookingInviteAlreadyAccepted

    invite = models.BookingInvite.match(user.id, bid, db)
    if not invite:
        raise APIError.BookingInviteNotFound
    if invite and invite[0].rejected:
        raise APIError.BookingInviteAlreadyRejected
    if invite and invite[0].accepted:
        raise APIError.BookingInviteAlreadyAccepted

    invite[0].accepted = False
    invite[0].rejected = True
    db.add(invite[0])
    db.commit()


@router.get(
    "/booking/{bid}/invite/{cid}/info",
    response_model=models.ContractorBookingInviteView,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No active projects"}},
)
def invite_info(bid: uuid.UUID, cid: uuid.UUID, _user: TokenAuthUser, db: SessionDB):
    invite = models.BookingInvite.by_cid_unchecked(cid, bid, db)
    if not invite:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return models.ContractorBookingInviteView(**invite[0].model_dump())


# =========================== Quotes ===========================


@router.post("/booking/{bid}/quote")
def booking_quote(
    bid: uuid.UUID, quote: models.QuoteCreate, user: TokenAuthContractor, db: SessionDB
):
    """
    Contractor creates a new quote for a given booking
    Update a qoute by calling this with the new quote

    - This will essentially regenerate the tasks

    Note:
    -There can be multiple quote items per booking unit
    Use the booking info to get the booking units and let the user select
    - There is 1:1 between materials and quote items, eg only 1 material per
    quote item

    """
    booking_invite = models.BookingInvite.by_cid(user.id, bid, db)
    if not booking_invite:
        raise APIError.BookingInviteNotFound
    booking_invite = booking_invite[0]
    error = models.Quote.create(quote, bid, booking_invite.id, db)
    print(error)
    if error:
        raise APIError.InvalidQuote(error)
    db.commit()


@router.get("/booking/{bid}/quote/info", response_model=models.QuoteView)
def booking_quote_info(bid: uuid.UUID, user: TokenAuthContractor, db: SessionDB):
    """
    Gets the quote information for a given booking
    Contractor may only have a single quote per booking

    Return:
        -   [204 No Content]: when no quote is present
    """
    model = models.Quote.by_cid(bid, user.id, db)
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


@router.post("/booking/{bid}/qoute/info/{qiid}/update")
def booking_quote_item_update(
    bid: uuid.UUID,
    qiid: uuid.UUID,
    new_status: models.QuoteItemUpdate,
    user: TokenAuthContractor,
    db: SessionDB,
):
    """
    Update the status of a quote item.
    Select a qiid (quote_item_id) from the the quote info and provide the new
    status

    Note: Quote must be accepted before the status of a quote_item can be changed
    """
    item = models.QuoteItem.by_qiid(qiid, bid, db)
    if not item:
        raise APIError.QuoteItemNotFound
    item.status = new_status.status
    #print(item.status)
    db.add(item)
    db.commit()


# =========================== Projects ===========================


@router.get(
    "/projects",
    response_model=models.ProjectList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No active projects"}},
)
def projects_list(user: TokenAuthContractor, db: SessionDB):
    """
    Get a list of all active projects IDs for a contractor
    - For each booking ID not present call `contractor/booking/{bid}/info`

    Return:
        -   [204 No Content] when no active projects
    """
    projects = models.Project.list_by_cid(user.id, db)
    if not projects:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    projects = models.ProjectList(
        projects=[
            models.ProjectItem(
                id=project[0],
                created_at=project[1],
                title=project[2],
                avatar_uri=project[3],
                first_name=project[4],
                last_name=project[5],
                booking_units=project[6],
            )
            for project in projects
        ]
    )
    return projects


@router.get("/project/{bid}/info", response_model=models.ContractorProjectView)
def project(bid: uuid.UUID, user: TokenAuthContractor, db: SessionDB):
    """
    Get a project's information based on a project ID as seen by the contractor
    """
    # TODO: add quote
    project = models.Project.by_cid(bid, user.id, db)
    if not project:
        raise APIError.ProjectDetailsNotFound
    view = models.ContractorProjectView(
        homeowner=models.HomeownerPublicView.create(project[4]),
        booking=models.BookingDetailViewBase(**project[1], booking_images=project[2]),
        project_images=project[3],
        **project[0].model_dump(),
    )
    return view


@router.post("/project/{bid}/complete")
def signal_project_completion(bid: uuid.UUID, user: TokenAuthContractor, db: SessionDB):
    """
    Contractor signals project completion to the homeowner

    Note: Homeowner needs to accept or reject this signal to change project
    completion status and/or visibility
    """
    project = models.Project.by_id(bid, db)
    if not project:
        raise APIError.ProjectDetailsNotFound
    if project.contractor_id != user.id:
        raise APIError.ProjectDetailsNotFound
    if project.signal_completion:
        raise APIError.ProjectCompletionAlreadySignaled

    project.signal_completion = True
    db.add(project)
    db.commit()


@router.post("/project/{bid}/images")
def project_images_upload(
    bid: uuid.UUID,
    captions: Annotated[List[str], Form()],
    user: TokenAuthContractor,
    db: SessionDB,
    files: list[UploadFile],
):
    """
    Upload a project's images

    param (files):
    - Optional list of images

    param (captions):
    - Captions list should have the same length as the number of images;
    - Leave an empty string for images with no caption
    """
    if len(files) != len(captions):
        raise APIError.ImageUploadException

    # TODO: safety checks
    models.ProjectImage.store(bid, files, captions, db)
    db.commit()


# =========================== Search ===========================


@router.post(
    "/search",
    response_model=models.SearchContractorList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No matching contractors"}},
)
def search_by_filter(filter: models.Filter, user: TokenAuthUser, db: SessionDB):
    contractors = models.Filter.by_units_and_area(
        filter.professions, str(filter.zipcode), db
    )
    if not contractors:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return models.SearchContractorList(
        contractors=[
            models.ContractorPublicView(
                **contractor[0].model_dump(),
                professions=contractor[1],
                areas=contractor[2],
            )
            for contractor in contractors
        ]
    )


@router.get(
    "/{bid}/search",
    response_model=models.SearchContractorList,
    responses={status.HTTP_204_NO_CONTENT: {"description": "No matches bookings"}},
)
def search_by_booking(bid: uuid.UUID, user: TokenAuthHomeowner, db: SessionDB):    
    contractors = models.BookingDetail.match_all(bid, db)
    if not contractors:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return models.SearchContractorList(
        contractors=[
            models.ContractorPublicView(
                **contractor[0].model_dump(),
                professions=contractor[1],
                areas=contractor[2],
            )
            for contractor in contractors
        ]
    )

    # recommendation = RecommendationEngine(SQL_Model=contractors)
    # static_vec_preference = {
    #     "quality_rating": 4,
    #     "on_schedule_rating": 10,
    #     "budget_rating": 3,
    # }  # Tune parms later
    # recommendation.set_static_vector(
    #     static_vec_preference
    # )  # TODO pass vec parameters as dict (preference)

    # return recommendation.recommend()
