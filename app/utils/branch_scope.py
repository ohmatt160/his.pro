from sqlalchemy import or_


def user_branch_id(user) -> str | None:
    if not user:
        return None
    return getattr(user, "branch_id", None) or getattr(user, "department_id", None)


def effective_branch_id(user, requested_branch_id: str | None = None, requested_department_id: str | None = None) -> str | None:
    if not user:
        return None
    role = (getattr(user, "role", None) or "").upper()
    if role == "ADMIN":
        return requested_branch_id or requested_department_id
    return user_branch_id(user)


def apply_branch_filter(query, model, branch_id: str | None):
    if not branch_id:
        return query

    predicates = []
    if hasattr(model, "branch_id"):
        predicates.append(model.branch_id == branch_id)
    if hasattr(model, "department_id"):
        predicates.append(model.department_id == branch_id)

    if not predicates:
        return query
    return query.filter(or_(*predicates))


def belongs_to_branch(row, branch_id: str | None) -> bool:
    if not branch_id:
        return True
    return getattr(row, "branch_id", None) == branch_id or getattr(row, "department_id", None) == branch_id
