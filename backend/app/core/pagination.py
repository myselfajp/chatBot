"""
Pagination utilities for consistent pagination across the application.
"""
from typing import Generic, TypeVar, List
from pydantic import BaseModel
from math import ceil


T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    Pagination parameters for list endpoints.
    """
    page: int = 1
    limit: int = 20
    
    def get_offset(self) -> int:
        """Calculate the offset for database queries."""
        return (self.page - 1) * self.limit
    
    def validate(self) -> None:
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValueError("Page must be >= 1")
        if self.limit < 1 or self.limit > 100:
            raise ValueError("Limit must be between 1 and 100")


class PaginationMeta(BaseModel):
    """
    Pagination metadata for responses.
    """
    total: int
    page: int
    limit: int
    total_pages: int
    
    @classmethod
    def create(cls, total: int, page: int, limit: int) -> "PaginationMeta":
        """
        Create pagination metadata with calculated total pages.
        
        Args:
            total: Total number of items
            page: Current page number
            limit: Items per page
            
        Returns:
            PaginationMeta instance
        """
        total_pages = ceil(total / limit) if total > 0 else 0
        return cls(
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages
        )


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response wrapper.
    """
    status: str = "success"
    data: List[T]
    meta: PaginationMeta
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        limit: int,
        status: str = "success"
    ) -> "PaginatedResponse[T]":
        """
        Create a paginated response.
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            limit: Items per page
            status: Response status
            
        Returns:
            PaginatedResponse instance
        """
        meta = PaginationMeta.create(total=total, page=page, limit=limit)
        return cls(status=status, data=items, meta=meta)


def calculate_offset(page: int, limit: int) -> int:
    """
    Calculate database offset from page and limit.
    
    Args:
        page: Page number (1-indexed)
        limit: Items per page
        
    Returns:
        Offset for database query
    """
    return (page - 1) * limit


def calculate_total_pages(total: int, limit: int) -> int:
    """
    Calculate total number of pages.
    
    Args:
        total: Total number of items
        limit: Items per page
        
    Returns:
        Total number of pages
    """
    return ceil(total / limit) if total > 0 else 0
