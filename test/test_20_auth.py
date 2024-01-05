import time
from fastapi import status
from api.core.error import APIError
import api.models as models
from test.utils import (
    TESTPASS,
    TestApp,
    test_app,  # noqa: F401
    test_app_with_1_second_token,  # noqa: F401
)


def test_contractor_auth_with_no_token(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _ = app.create_contractor(cnt)
    response = app.api.get(f"contractor/{cnt.id}/public")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"


def test_homeowner_auth_with_no_token(test_app: TestApp):
    app = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, _ = app.create_homeowner(hmw)
    response = app.api.get(f"homeowner/{hmw.id}/public")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()["detail"] == "Not authenticated"


def test_contractor_access_token_with_incorrect_password(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    _, user = app.create_contractor(cnt)
    response = app.api.post("token", data={"password": "wrong_password", "username": user.email})
    assert response.status_code == APIError.CredentialsException.status_code
    assert response.json()["detail"] == APIError.CredentialsException.detail


def test_contractor_access_token_with_incorrect_email(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    app.create_contractor(cnt)
    response = app.api.post("token", data={"password": TESTPASS, "username": "wrong_email"})
    assert response.status_code == APIError.CredentialsException.status_code
    assert response.json()["detail"] == APIError.CredentialsException.detail


def test_contractor_access_token_with_no_scopes(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    _, user = app.create_contractor(cnt)
    response = app.api.post("token", data={"password": TESTPASS, "username": user.email})
    assert response.status_code == APIError.PermissionException.status_code
    assert response.json()["detail"] == APIError.PermissionException.detail


def test_contractor_access_token_with_correct_password(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    app.create_contractor_with_token(cnt)


def test_homeowner_access_token_with_correct_password(test_app: TestApp):
    app = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    app.create_homeowner_with_token(hmw)


def test_contractor_valid_jwt_token(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, access_token = app.create_contractor_with_token(cnt)
    response = app.api.get(
        f"contractor/{cnt.id}/public",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == status.HTTP_200_OK


def test_contractor_invalid_jwt_token(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, _ = app.create_contractor_with_token(cnt)
    response = app.api.get(
        f"contractor/{cnt.id}/public",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == APIError.TokenException.status_code
    assert response.json()["detail"] == APIError.TokenException.detail


def test_contractor_tamper_jwt_token(test_app: TestApp):
    app = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, access_token = app.create_contractor_with_token(cnt)
    access_token = access_token[:10] + "X" if access_token[10] != "X" else "Y" + access_token[11:]
    response = app.api.get(
        f"contractor/{cnt.id}/public",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == APIError.TokenException.status_code
    assert response.json()["detail"] == APIError.TokenException.detail


def test_contractor_expired_jwt_token(test_app_with_1_second_token: TestApp):
    app = test_app_with_1_second_token
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    cnt, _, access_token = app.create_contractor_with_token(cnt)
    time.sleep(2)
    response = app.api.get(
        f"contractor/{cnt.id}/public",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == APIError.TokenException.status_code
    assert response.json()["detail"] == APIError.TokenException.detail
