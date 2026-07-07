from app.repository.user import UserRepository
from app.core.security import hash_password
from app.model.user import User
from app.schema.user import UserListItem, UserListData, UserListResponse
from app.core.pagination import calculate_total_pages
from app.core.validation import (
    validate_email,
    validate_password,
    validate_phone_number,
    sanitize_string,
)
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session
from fastapi import HTTPException


class UserService:
    def __init__(self, user_repo: Optional[UserRepository] = None):
        self.user_repo = user_repo or UserRepository()

    def create_user(
        self,
        db: Session,
        email: str,
        password: str,
        full_name: str,
        phone_number: str,
        role: str = "customer",
        is_active: bool = True,
    ) -> User:
        """
        Create a new user (Admin only)

        Args:
            db: Database session
            email: User email (must be unique)
            password: Plain text password (will be hashed)
            full_name: User's full name (required)
            phone_number: User's phone number (required)
            role: User role (admin, editor, seo)
            is_active: Whether user is active

        Returns:
            Created User object

        Raises:
            HTTPException: If email already exists
        """
        # Validate email format
        email = email.lower().strip()
        is_valid, error_msg = validate_email(email)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Check if email already exists
        existing_user = self.user_repo.get_by_email(db, email)
        if existing_user:
            raise HTTPException(
                status_code=400, detail=f"User with email {email} already exists"
            )

        # Validate password strength
        is_valid, error_msg = validate_password(password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Validate phone number
        is_valid, error_msg = validate_phone_number(phone_number)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # Sanitize inputs
        sanitized_full_name = sanitize_string(full_name, max_length=255)
        if not sanitized_full_name:
            raise HTTPException(status_code=400, detail="Full name is required")
        full_name = sanitized_full_name

        # Validate role
        valid_roles = ["admin", "customer"]
        if role not in valid_roles:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
            )

        # Hash the password
        hashed_password = hash_password(password)

        # Create user object - email is not verified by default
        new_user = User(
            email=email,
            password_hash=hashed_password,
            full_name=full_name,
            role=role,
            is_active=is_active,
            phone_number=phone_number,
            is_email_verified=False,  # New users must verify email
            is_two_factor_enabled=False,  # 2FA disabled by default
        )

        # Save to database
        created_user = self.user_repo.create_user(db, new_user)

        return created_user

    def list_users(
        self,
        db: Session,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> UserListResponse:
        """
        List users with pagination, search, filtering, and sorting.

        Args:
            db: Database session
            page: Page number (1-indexed)
            limit: Items per page
            search: Search term for full name or email
            role: Filter by role
            is_active: Filter by active status (true/false)
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)

        Returns:
            UserListResponse with paginated user data
        """
        # Get users with filters from repository
        users, total = self.user_repo.list_users_with_filters(
            db=db,
            page=page,
            limit=limit,
            search=search,
            role=role,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Calculate total pages
        total_pages = calculate_total_pages(total, limit)

        # Map users to response schema
        user_items: List[UserListItem] = []
        for user in users:
            user_item = UserListItem(
                id=user.id,
                full_name=user.full_name,
                email=user.email,
                phone_number=user.phone_number,
                role=user.role,
                is_active=user.is_active,
                is_email_verified=user.is_email_verified,
                is_two_factor_enabled=user.is_two_factor_enabled,
                created_at=user.created_at,
                updated_at=user.updated_at,
            )
            user_items.append(user_item)

        # Build response
        data = UserListData(
            users=user_items,
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )

        return UserListResponse(status="success", data=data)

    def get_user(self, db: Session, user_id: int) -> User:
        """
        Get a user by ID.

        Args:
            db: Database session
            user_id: ID of the user to retrieve

        Returns:
            User object

        Raises:
            HTTPException: If user not found
        """
        user = self.user_repo.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User with id {user_id} not found"
            )
        return user

    def update_user(
        self,
        db: Session,
        user_id: int,
        email: Optional[str] = None,
        password: Optional[str] = None,
        full_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_two_factor_enabled: Optional[bool] = None,
    ) -> User:
        """
        Update a user (Admin only)

        Args:
            db: Database session
            user_id: ID of the user to update
            email: New email (optional, must be unique)
            password: New password (optional, will be hashed)
            full_name: New full name (optional)
            phone_number: New phone number (optional)
            role: New role (optional, must be valid)
            is_active: New active status (optional)
            is_two_factor_enabled: Enable/disable 2FA (optional)

        Returns:
            Updated User object

        Raises:
            HTTPException: If user not found, email already exists, or invalid role
        """
        # Get the user
        user = self.user_repo.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User with id {user_id} not found"
            )

        # Build update dictionary with only provided fields
        update_data = {}

        # Check if email is being updated and if it's unique
        if email is not None and email != user.email:
            email = email.lower().strip()
            is_valid, error_msg = validate_email(email)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)

            existing_user = self.user_repo.get_by_email(db, email)
            if existing_user:
                raise HTTPException(
                    status_code=400, detail=f"User with email {email} already exists"
                )
            update_data["email"] = email
            # If email changes, require re-verification
            update_data["is_email_verified"] = False

        # Hash password if it's being updated
        if password is not None:
            is_valid, error_msg = validate_password(password)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            update_data["password_hash"] = hash_password(password)

        # Validate role if it's being updated
        if role is not None:
            valid_roles = ["admin", "customer"]
            if role not in valid_roles:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                )

            # Check if we're demoting the last admin
            if user.role == "admin" and role != "admin":
                admin_count = self.user_repo.count_admins(db)
                if admin_count <= 1:
                    raise HTTPException(
                        status_code=403,
                        detail="Cannot change role: This is the last admin user. System must have at least one admin.",
                    )

            update_data["role"] = role

        # Add other fields if provided with validation
        if full_name is not None:
            full_name = sanitize_string(full_name, max_length=255)
            if not full_name:
                raise HTTPException(status_code=400, detail="Full name cannot be empty")
            update_data["full_name"] = full_name

        if phone_number is not None:
            is_valid, error_msg = validate_phone_number(phone_number)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_msg)
            update_data["phone_number"] = phone_number

        if is_active is not None:
            update_data["is_active"] = is_active

        if is_two_factor_enabled is not None:
            update_data["is_two_factor_enabled"] = is_two_factor_enabled

        # If no fields to update, return the user as is
        if not update_data:
            return user

        # Update the user
        updated_user = self.user_repo.update_user(db, user, update_data)

        return updated_user

    def verify_email(self, db: Session, user_id: int) -> User:
        """
        Verify a user's email address.

        Args:
            db: Database session
            user_id: ID of the user to verify

        Returns:
            Updated User object

        Raises:
            HTTPException: If user not found
        """
        user = self.user_repo.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User with id {user_id} not found"
            )

        update_data = {"is_email_verified": True}
        updated_user = self.user_repo.update_user(db, user, update_data)

        return updated_user

    def delete_user(self, db: Session, user_id: int, current_user: User) -> None:
        """
        Delete a user by ID.

        Args:
            db: Database session
            user_id: ID of the user to delete
            current_user: The admin performing the deletion

        Raises:
            HTTPException: If user does not exist or cannot be deleted
        """
        # Get the user to delete
        user = self.user_repo.get(db, user_id)
        if not user:
            raise HTTPException(
                status_code=404, detail=f"User with id {user_id} not found"
            )

        # Prevent self-deletion
        if user.id == current_user.id:
            raise HTTPException(
                status_code=403, detail="Cannot delete your own account"
            )

        # Prevent deleting the last admin
        if user.role == "admin":
            admin_count = self.user_repo.count_admins(db)
            if admin_count <= 1:
                raise HTTPException(
                    status_code=403,
                    detail="Cannot delete the last admin user. System must have at least one admin.",
                )

        self.user_repo.delete_user(db, user_id)
