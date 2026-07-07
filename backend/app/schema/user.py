from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserListItem(BaseModel):
    id: int
    full_name: str
    email: str
    phone_number: str
    role: str
    is_active: bool
    is_email_verified: bool
    is_two_factor_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListData(BaseModel):
    users: List[UserListItem]
    total: int
    page: int
    limit: int
    total_pages: int


class UserListResponse(BaseModel):
    status: str = "success"
    data: UserListData


class UserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone_number: str
    role: str = "customer"
    is_active: bool = True

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123",
                "full_name": "John Doe",
                "phone_number": "09123456789",
                "role": "customer",
                "is_active": True,
            }
        }


class UserCreateResponse(BaseModel):
    status: str = "success"
    id: int
    email: str
    full_name: str
    phone_number: str
    role: str
    is_active: bool
    is_email_verified: bool
    is_two_factor_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_two_factor_enabled: Optional[bool] = None

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "full_name": "John Doe",
                "phone_number": "09123456789",
                "role": "customer",
                "is_active": True,
                "is_two_factor_enabled": False,
                "password": "NewSecurePassword123",
            }
        }


class UserUpdateResponse(BaseModel):
    status: str = "success"
    id: int
    email: str
    full_name: str
    phone_number: str
    role: str
    is_active: bool
    is_email_verified: bool
    is_two_factor_enabled: bool
    updated_at: datetime

    class Config:
        from_attributes = True


class UserDetailResponse(BaseModel):
    status: str = "success"
    id: int
    email: str
    full_name: str
    phone_number: str
    role: str
    is_active: bool
    is_email_verified: bool
    is_two_factor_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
