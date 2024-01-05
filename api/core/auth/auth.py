from typing import Annotated
from fastapi import Depends, Security
from api.core.auth.utils import validate_token_scopes, validate_user_login
from api.models.user import User

PasswordAuthUser = Annotated[User, Depends(validate_user_login)]

TokenAuthContractor = Annotated[User, Security(validate_token_scopes, scopes=["contractor"])]
TokenAuthHomeowner = Annotated[User, Security(validate_token_scopes, scopes=["homeowner"])]
TokenAuthUser = Annotated[User, Security(validate_token_scopes, scopes=[])]
