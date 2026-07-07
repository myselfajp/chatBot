from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.service.deps import get_current_admin_user, get_user_service
from app.model.user import User
from app.schema.user import (
    UserListResponse,
    UserCreateRequest,
    UserCreateResponse,
    UserUpdateRequest,
    UserUpdateResponse,
    UserDetailResponse,
)
from app.service.user import UserService


router = APIRouter(prefix="/v1/admin", tags=["admin"])


@router.get("/users", response_model=UserListResponse)
def list_users(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by full name or email"),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status (true/false)"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)"),
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    """
    List all users (Admin only)

    Supports pagination, search, filtering, and sorting.
    Only accessible by administrators.
    """
    return user_service.list_users(
        db=db,
        page=page,
        limit=limit,
        search=search,
        role=role,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/users/{user_id}", response_model=UserDetailResponse)
def get_user(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    """
    Get user details by ID (Admin only)

    This endpoint allows administrators to retrieve detailed information about a specific user.
    """
    user = user_service.get_user(db=db, user_id=user_id)

    return UserDetailResponse(
        status="success",
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone_number=user.phone_number,
        role=user.role,
        is_active=user.is_active,
        is_email_verified=user.is_email_verified,
        is_two_factor_enabled=user.is_two_factor_enabled,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/users", response_model=UserCreateResponse, status_code=201)
def create_user(
    user_request: UserCreateRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    """
    Create a new user (Admin only)

    This endpoint allows administrators to create new users in the system.
    The password will be automatically hashed before storage.
    """
    new_user = user_service.create_user(
        db=db,
        email=user_request.email,
        password=user_request.password,
        full_name=user_request.full_name,
        phone_number=user_request.phone_number,
        role=user_request.role,
        is_active=user_request.is_active,
    )

    return UserCreateResponse(
        status="success",
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        phone_number=new_user.phone_number,
        role=new_user.role,
        is_active=new_user.is_active,
        is_email_verified=new_user.is_email_verified,
        is_two_factor_enabled=new_user.is_two_factor_enabled,
        created_at=new_user.created_at,
    )


@router.put("/users/{user_id}", response_model=UserUpdateResponse)
def update_user(
    user_id: int,
    user_request: UserUpdateRequest,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    """
    Update a user by ID (Admin only)

    This endpoint allows administrators to update user information.
    All fields are optional - only provide the fields you want to update.
    """
    updated_user = user_service.update_user(
        db=db,
        user_id=user_id,
        email=user_request.email,
        password=user_request.password,
        full_name=user_request.full_name,
        phone_number=user_request.phone_number,
        role=user_request.role,
        is_active=user_request.is_active,
        is_two_factor_enabled=user_request.is_two_factor_enabled,
    )

    return UserUpdateResponse(
        status="success",
        id=updated_user.id,
        email=updated_user.email,
        full_name=updated_user.full_name,
        phone_number=updated_user.phone_number,
        role=updated_user.role,
        is_active=updated_user.is_active,
        is_email_verified=updated_user.is_email_verified,
        is_two_factor_enabled=updated_user.is_two_factor_enabled,
        updated_at=updated_user.updated_at,
    )


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    admin_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
    user_service: UserService = Depends(get_user_service),
):
    """
    Delete a user by ID (Admin only)

    This endpoint allows administrators to delete a user from the system by their ID.
    Last admin user cannot be deleted, and you cannot delete your own account.
    """
    user_service.delete_user(db=db, user_id=user_id, current_user=admin_user)
    return None
