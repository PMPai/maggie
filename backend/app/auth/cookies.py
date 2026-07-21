from fastapi import Response
from app.config import get_settings

settings = get_settings()


def set_auth_cookies(response: Response, access_token: str, refresh_token: str, csrf_token: str):
    response.set_cookie(
        "access_token", access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True, secure=(settings.APP_ENV == "production"), samesite="lax",
    )
    response.set_cookie(
        "refresh_token", refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=True, secure=(settings.APP_ENV == "production"), samesite="lax",
        path="/api/auth",
    )
    response.set_cookie(
        "csrf_token", csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        httponly=False, secure=(settings.APP_ENV == "production"), samesite="lax",
    )


def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/api/auth")
    response.delete_cookie("csrf_token")
