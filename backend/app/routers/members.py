from fastapi import APIRouter, status

from app.core.dependencies import CurrentUser, DbSession
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate
from app.services import member_service

router = APIRouter(prefix="/businesses/{business_id}/members", tags=["Business members"])


@router.get("", response_model=list[MemberRead])
def list_members(business_id: int, db: DbSession, current_user: CurrentUser):
    return member_service.list_members(db, current_user, business_id)


@router.post("", response_model=MemberRead, status_code=status.HTTP_201_CREATED)
def add_member(business_id: int, payload: MemberCreate, db: DbSession, current_user: CurrentUser):
    return member_service.add_member(db, current_user, business_id, payload)


@router.patch("/{member_id}", response_model=MemberRead)
def update_member(
    business_id: int,
    member_id: int,
    payload: MemberUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    return member_service.update_member(db, current_user, business_id, member_id, payload)


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(business_id: int, member_id: int, db: DbSession, current_user: CurrentUser):
    member_service.remove_member(db, current_user, business_id, member_id)
