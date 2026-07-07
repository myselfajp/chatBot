from __future__ import annotations

from typing import Generic, TypeVar, Type, Sequence, Optional, Union
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

T = TypeVar("T")


class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], resource_name: Optional[str] = None):
        self.model = model
        self.resource_name = resource_name or model.__name__

    def get(self, db: Session, id: int) -> Union[T, None]:
        return db.get(self.model, id)

    def list(self, db: Session, limit: int = 50, offset: int = 0) -> Sequence[T]:
        if limit < 0 or offset < 0:
            raise HTTPException(status_code=400, detail="limit/offset must be >= 0")
        stmt = select(self.model).limit(limit).offset(offset)
        return db.execute(stmt).scalars().all()

    def create(self, db: Session, obj_in: dict) -> T:
        # Filter out fields that don't exist in the model
        model_columns = {col.key for col in self.model.__table__.columns}
        filtered_obj_in = {k: v for k, v in obj_in.items() if k in model_columns}
        obj = self.model(**filtered_obj_in)
        db.add(obj)
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
            print(f"IntegrityError: {error_msg}")
            raise HTTPException(
                status_code=409,
                detail=f"{self.resource_name} already exists or violates a constraint: {error_msg}",
            )
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: T, obj_in: dict) -> T:
        # Filter out fields that don't exist in the model
        model_columns = {col.key for col in self.model.__table__.columns}
        filtered_obj_in = {k: v for k, v in obj_in.items() if k in model_columns}
        for k, v in filtered_obj_in.items():
            setattr(db_obj, k, v)
        db.add(db_obj)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"{self.resource_name} update violates a constraint",
            )
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: T) -> None:
        db.delete(db_obj)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete {self.resource_name}: referenced by other records",
            )

    def bulk_delete(self, db: Session, ids: list[int]) -> tuple[int, dict]:
        """
        Delete multiple records by their IDs.
        Uses atomic transaction - all deletions succeed or all fail together.
        Returns a tuple of (deleted_count, failed_deletions)
        where failed_deletions is a dict of {id: reason}
        """
        deleted_count = 0
        failed_deletions = {}
        objects_to_delete = []

        # First, validate all objects and collect them
        for obj_id in ids:
            obj = db.get(self.model, obj_id)

            if not obj:
                failed_deletions[obj_id] = f"{self.resource_name} not found"
            else:
                objects_to_delete.append(obj)

        # If we have objects to delete, delete them atomically
        if objects_to_delete:
            try:
                for obj in objects_to_delete:
                    db.delete(obj)

                db.commit()
                deleted_count = len(objects_to_delete)
            except IntegrityError as e:
                db.rollback()
                error_msg = str(e.orig) if hasattr(e, "orig") else str(e)
                # If commit fails, mark all attempted deletions as failed
                for obj in objects_to_delete:
                    failed_deletions[obj.id] = f"Database error: {error_msg}"
                deleted_count = 0
            except Exception as e:
                db.rollback()
                # If commit fails, mark all attempted deletions as failed
                for obj in objects_to_delete:
                    failed_deletions[obj.id] = f"Database error: {str(e)}"
                deleted_count = 0

        return deleted_count, failed_deletions
