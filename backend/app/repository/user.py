from typing import Sequence, Optional, Tuple
from sqlalchemy import select, func, or_, desc, asc
from sqlalchemy.orm import Session
from app.model.user import User
from app.core.pagination import calculate_offset
from .base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User, resource_name="User")

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return db.execute(stmt).scalar_one_or_none()

    def count_admins(self, db: Session) -> int:
        stmt = select(func.count()).select_from(User).where(User.role == "admin")
        return db.execute(stmt).scalar_one()

    def list_ordered(
        self, db: Session, limit: int = 50, offset: int = 0
    ) -> Sequence[User]:
        stmt = select(User).order_by(User.id).limit(limit).offset(offset)
        return db.execute(stmt).scalars().all()

    def list_users_with_filters(
        self,
        db: Session,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[Sequence[User], int]:
        """
        List users with pagination, search, and filtering
        Returns tuple of (users, total_count)
        """
        # Validate sort_by to prevent injection
        allowed_sort_fields = [
            "id",
            "email",
            "full_name",
            "role",
            "created_at",
            "updated_at",
        ]
        if sort_by not in allowed_sort_fields:
            sort_by = "created_at"

        # Base query
        stmt = select(User)

        # Apply search filter
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    User.email.ilike(search_term),
                    User.full_name.ilike(search_term),
                )
            )

        # Apply role filter
        if role:
            stmt = stmt.where(User.role == role)

        # Apply is_active filter
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)

        # Count total before pagination
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.execute(count_stmt).scalar_one()

        # Apply sorting
        sort_column = getattr(User, sort_by)
        if sort_order.lower() == "asc":
            stmt = stmt.order_by(asc(sort_column))
        else:
            stmt = stmt.order_by(desc(sort_column))

        # Apply pagination
        offset = calculate_offset(page, limit)
        stmt = stmt.limit(limit).offset(offset)

        users = db.execute(stmt).scalars().all()
        return users, total

    def list_by_ids(self, db: Session, user_ids: list[int]) -> Sequence[User]:
        """
        Fetch users by a list of IDs in a single query.
        Returns a sequence of User objects; order is not guaranteed.
        """
        if not user_ids:
            return []
        stmt = select(User).where(User.id.in_(user_ids))
        return db.execute(stmt).scalars().all()

    def create_user(self, db: Session, user: User) -> User:
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_user(self, db: Session, user: User, update_data: dict) -> User:
        """
        Update a user with the provided data
        """
        return self.update(db, user, update_data)

    def delete_user(self, db: Session, user_id: int) -> None:
        stmt = select(User).where(User.id == user_id)
        user = db.execute(stmt).scalar_one_or_none()
        if user:
            db.delete(user)
            db.commit()
        else:
            raise ValueError(f"User with id {user_id} does not exist.")

    def bulk_delete_users(self, db: Session, user_ids: list[int]) -> tuple[int, dict]:
        """
        Delete multiple users by their IDs.
        Uses atomic transaction - all deletions succeed or all fail together.
        Returns a tuple of (deleted_count, failed_deletions)
        where failed_deletions is a dict of {user_id: reason}
        """
        deleted_count = 0
        failed_deletions = {}
        users_to_delete = []

        # First, validate all users and collect them
        for user_id in user_ids:
            stmt = select(User).where(User.id == user_id)
            user = db.execute(stmt).scalar_one_or_none()

            if not user:
                failed_deletions[user_id] = "User not found"
            else:
                users_to_delete.append(user)

        # If we have users to delete, delete them atomically
        if users_to_delete:
            try:
                for user in users_to_delete:
                    db.delete(user)

                db.commit()
                deleted_count = len(users_to_delete)
            except Exception as e:
                db.rollback()
                # If commit fails, mark all attempted deletions as failed
                for user in users_to_delete:
                    failed_deletions[user.id] = f"Database error: {str(e)}"
                deleted_count = 0

        return deleted_count, failed_deletions

    def bulk_update_users_by_ids(
        self, db: Session, user_ids: list[int], update_data: dict
    ) -> int:
        """
        Bulk update multiple users with the same data in a single query.

        Args:
            db: Database session
            user_ids: List of user IDs to update
            update_data: Dictionary of fields to update

        Returns:
            Number of users updated
        """
        if not user_ids or not update_data:
            return 0

        from sqlalchemy import update as sql_update
        from sqlalchemy.engine import CursorResult

        try:
            stmt = sql_update(User).where(User.id.in_(user_ids)).values(**update_data)
            result = db.execute(stmt)
            db.commit()
            return int(result.rowcount or 0)
        except Exception as e:
            db.rollback()
            raise e
