from fastapi import Query

DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def pagination_params(
    page: int = Query(1, ge=1),
    per_page: int = Query(DEFAULT_PER_PAGE, ge=1, le=MAX_PER_PAGE),
) -> tuple[int, int]:
    return page, min(per_page, MAX_PER_PAGE)


def apply_pagination(query, page: int, per_page: int):
    return query.offset((page - 1) * per_page).limit(per_page)
