from api import models  # prevetn ciruclar import
from fastapi import status
from api.core.error import APIError
from test.utils import TESTPASS, TestApp, test_app  # noqa: F401


def test_health(test_app: TestApp):
    app: TestApp = test_app
    print(app.api.base_url)
    response = app.api.get(
        "health",
    )
    print(response.text)
    assert response.status_code == status.HTTP_200_OK


def test_contractor_signup(test_app: TestApp):
    app: TestApp = test_app
    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    _ = app.create_contractor(cnt)


def test_homeowner_signup(test_app: TestApp):
    app: TestApp = test_app
    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    _ = app.create_homeowner(hmw)


def test_contractor_signup_already_registered(test_app: TestApp):
    app: TestApp = test_app

    cnt = models.ContractorCreate.mock(app.faky, TESTPASS)
    _ = app.create_contractor(cnt)
    response = app.api.post("contractor/signup", data=cnt.model_dump())
    assert response.status_code == APIError.SignupException.status_code
    assert response.json()["detail"] == APIError.SignupException.detail


def test_homeowner_signup_already_registered(test_app: TestApp):
    app: TestApp = test_app

    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    _ = app.create_homeowner(hmw)
    response = app.api.post("homeowner/signup", data=hmw.model_dump())
    assert response.status_code == APIError.SignupException.status_code
    assert response.json()["detail"] == APIError.SignupException.detail


def test_quiz(test_app: TestApp):
    app: TestApp = test_app

    hmw = models.HomeownerCreate.mock(app.faky, TESTPASS)
    hmw, user, access_token = app.create_homeowner_with_token(hmw)
    reponse = app.api.get("quiz", headers={"Authorization": f"Bearer {access_token}"})
    assert reponse.status_code == status.HTTP_200_OK
