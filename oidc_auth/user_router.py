from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/api/user/info")
async def user_info(request: Request):
    """Return current authenticated user info from OIDC session."""
    user = getattr(request.state, "user", None)
    if not user:
        return JSONResponse({"id": None, "email": None, "name": None}, status_code=200)
    return JSONResponse({
        "id": user.get("id"),
        "email": user.get("email"),
        "name": user.get("name"),
    })
