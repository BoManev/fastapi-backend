from functools import lru_cache
from passlib.context import CryptContext
from pydantic import model_validator


@lru_cache()
def get_crypt_context():
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return get_crypt_context().hash(password)


def verify_password(password, expected_hash):
    return get_crypt_context().verify(password, expected_hash)


class HashedPassword(str):
    """Takes a plain text password and hashes it"""

    @staticmethod
    def __get_validators__():
        yield HashedPassword.validate

    @model_validator(mode="before")
    def validate(cls, password, info):
        if not isinstance(password, str):
            raise ValueError("password must be string")
        hashed_password = hash_password(password)
        return hashed_password
