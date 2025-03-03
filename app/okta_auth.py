import requests
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from pydantic import BaseModel


OKTA_DOMAIN = "https://genpact.oktapreview.com"
OKTA_AUTH_SERVER_ID = "default"
OKTA_ISSUER = f"{OKTA_DOMAIN}/oauth2/{OKTA_AUTH_SERVER_ID}"
OKTA_AUDIENCE = "api://default"  
OKTA_JWKS_URI = f"{OKTA_ISSUER}/v1/keys"


bearer_scheme = HTTPBearer()


def get_jwks():
    try:
        response = requests.get(OKTA_JWKS_URI)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        raise HTTPException(status_code=500, detail=f"HTTP error while fetching JWKS: {http_err}")
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error while fetching JWKS: {err}")


class AuthError(HTTPException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=401, detail=detail)


async def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    token = credentials.credentials
    try:
        jwks = get_jwks()

        try:
            header = jwt.get_unverified_header(token)
        except JWTError as e:
            raise AuthError(detail=f"Error decoding token header: {str(e)}")
        
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        
        if not rsa_key:
            raise AuthError(detail="Unable to find the appropriate key in JWKS")

        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                audience=OKTA_AUDIENCE,
                issuer=OKTA_ISSUER
            )
        except JWTError as e:
            raise AuthError(detail=f"Error decoding token payload: {str(e)}")

        return payload

    except AuthError as e:
        raise e
    except Exception as e:
        raise AuthError(detail=f"Unexpected error during token verification: {str(e)}")


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    payload = await verify_token(credentials)
    return payload.get("sub", "No subject found in token")  