from fastapi import HTTPException, status


class APIError:
    CredentialsException = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    PermissionException = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or not enough permissions",
        headers={"WWW-Authenticate": "Bearer"},
    )

    class TokenException(HTTPException):
        detail = "Invalid or expired access token"
        status_code = status.HTTP_401_UNAUTHORIZED

        def __init__(self, header):
            super().__init__(
                status_code=self.status_code,
                detail=self.detail,
                headers={"WWW-Authenticate": header},
            )

    SignupException = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Email already registered",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ImageUploadException = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Each image should have a caption",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ContractorNotFound = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Contractor not found",
        headers={"WWW-Authenticate": "Bearer"},
    )

    HomeownerNotFound = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Homeowner not found",
        headers={"WWW-Authenticate": "Bearer"},
    )

    class BookingValidationException(HTTPException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = "Invalid input data"
        headers = {"WWW-Authenticate": "Bearer"}

        def __init__(self, e):
            super().__init__(
                status_code=self.status_code,
                detail=f"{self.detail}: {str(e)}",
                headers=self.headers,
            )

    class PortfolioValidationException(HTTPException):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
        detail = "Invalid input data"
        headers = {"WWW-Authenticate": "Bearer"}

        def __init__(self, e):
            super().__init__(
                status_code=self.status_code,
                detail=f"{self.detail}: {str(e)}",
                headers=self.headers,
            )

    BookingWithoutTasks = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Booking should have at least 1 task",
        headers={"WWW-Authenticate": "Bearer"},
    )

    BookingDetailsNotFound = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Booking details not found",
        headers={"WWW-Authenticate": "Bearer"},
    )

    BookingAlreadySend = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Booking already sent to contractor",
        headers={"WWW-Authenticate": "Bearer"},
    )

    BookingInviteNotFound = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="No valid booking invitation to accept",
        headers={"WWW-Authenticate": "Bearer"},
    )

    BookingInviteNotAccepted = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Booking not accepted by contractor",
        headers={"WWW-Authenticate": "Bearer"},
    )

    BookingInviteAlreadyAccepted = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Booking already accepted",
        headers={"WWW-Authenticate": "Bearer"},
    )

    BookingInviteAlreadyRejected = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Booking already rejected",
        headers={"WWW-Authenticate": "Bearer"},
    )

    QuoteAlreadyAccepted = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Quote already accepted",
        headers={"WWW-Authenticate": "Bearer"},
    )

    NotMatchingPreferences = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Contractor doesn't match all requirments",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ProjectDetailsNotFound = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Project details not found",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ProjectCompletionAlreadySignaled = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Project completion already signaled",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ProjectCompletionNotSignaled = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Project completion not signaled by contractor",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ProjectCompletionAlreadyAccepted = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Project completion already accepted",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ExternalPortfolioProjectNotFound = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="External portfolio project not found",
        headers={"WWW-Authenticate": "Bearer"},
    )

    PublicPortfolioProjectNotFound = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Public portfolio project not found",
        headers={"WWW-Authenticate": "Bearer"},
    )

    SearchFilterInvalidProfession = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid search filter profession",
        headers={"WWW-Authenticate": "Bearer"},
    )

    SearchFilterInvalidArea = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid search filter area or one not provided",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ReviewNotFound = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Review not found",
        headers={"WWW-Authenticate": "Bearer"},
    )

    ReviewAlreadyCreated = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Review has already been created for this project",
        headers={"WWW-Authenticate": "Bearer"},
    )

    class InvalidQuote(HTTPException):
        detail = "Invalid quote item due to:"
        status_code = status.HTTP_401_UNAUTHORIZED

        def __init__(self, error):
            super().__init__(
                status_code=self.status_code,
                detail=f"{self.detail} {error}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    QuoteItemNotFound = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Quote item not found for this booking or with this ID",
        headers={"WWW-Authenticate": "Bearer"},
    )

    QuoteNotFound = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Quote not found from this contractor in the booking",
        headers={"WWW-Authenticate": "Bearer"},
    )
