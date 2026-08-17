from fastapi import APIRouter, HTTPException, Security
from fastapi.security import APIKeyHeader
from ..auth import login, get_doctor_from_token

router = APIRouter()

authorization_header = APIKeyHeader(name="Authorization")

@router.post("/login")
def doctor_login(doctor_id: str, password: str):
    result = login(doctor_id, password)

    if not result:
        raise HTTPException(
            status_code=401,
            detail="Invalid doctor_id or password"
        )

    return result


def require_doctor(
    authorization: str = Security(authorization_header)
) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing bearer token"
        )

    token = authorization.removeprefix("Bearer ").strip()

    doctor_id = get_doctor_from_token(token)

    if not doctor_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    return doctor_id