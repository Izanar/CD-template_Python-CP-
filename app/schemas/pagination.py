from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
    total_pages: int
    current_page: int
    has_next: bool
    has_prev: bool

    @classmethod
    def from_pagination(cls, total: int, limit: int, offset: int) -> "PaginationMeta":
        total_pages = (total // limit) + (1 if total % limit > 0 else 0)
        current_page = (offset // limit) + 1
        has_next = (offset + limit) < total
        has_prev = offset > 0

        return cls(
            total=total,
            limit=limit,
            offset=offset,
            total_pages=total_pages,
            current_page=current_page,
            has_next=has_next,
            has_prev=has_prev,
        )


class PaginationResponse(BaseModel, Generic[T]):
    meta: PaginationMeta
    items: List[T]

    @classmethod
    def create(cls, items: List[T], total: int, limit: int, offset: int) -> "PaginationResponse":
        return cls(
            meta=PaginationMeta.from_pagination(total, limit, offset),
            items=items,
        )
