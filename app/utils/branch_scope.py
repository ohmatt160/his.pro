from fastapi import HTTPException
from sqlalchemy import or_


def user_branch_id(user) -> str | None:
    if not user:
        return None
    return getattr(user, "branch_id", None) or getattr(user, "department_id", None)


def require_facility_slug(user) -> str:
    facility_slug = getattr(user, "facility_slug", None)
    if not facility_slug:
        raise HTTPException(status_code=400, detail="User is not associated with a facility")
    return facility_slug


def effective_branch_id(user, requested_branch_id: str | None = None, requested_department_id: str | None = None) -> str | None:
    if not user:
        return None
    role = (getattr(user, "role", None) or "").upper()
    if role == "ADMIN":
        return requested_branch_id or requested_department_id
    return user_branch_id(user)


def tenant_query(db, model, user, requested_branch_id: str | None = None, requested_department_id: str | None = None):
    facility_slug = require_facility_slug(user)
    query = db.query(model).filter(model.facility_slug == facility_slug)
    branch_id = effective_branch_id(user, requested_branch_id, requested_department_id)
    return apply_branch_filter(query, model, branch_id)


def tenant_get(db, model, resource_id: str, user, not_found_detail: str = "Resource not found"):
    row = (
        db.query(model)
        .filter(model.id == resource_id, model.facility_slug == require_facility_slug(user))
        .first()
    )
    return require_tenant_row(row, user, not_found_detail)


def require_tenant_row(row, user, not_found_detail: str = "Resource not found"):
    if not row:
        raise HTTPException(status_code=404, detail=not_found_detail)

    facility_slug = require_facility_slug(user)
    if getattr(row, "facility_slug", None) != facility_slug:
        raise HTTPException(status_code=404, detail=not_found_detail)

    role = (getattr(user, "role", None) or "").upper()
    branch_id = None if role == "ADMIN" else user_branch_id(user)
    if branch_id and not belongs_to_branch(row, branch_id):
        raise HTTPException(status_code=404, detail=not_found_detail)

    return row


def branch_scope_for_user(user) -> str | None:
    return None if (getattr(user, "role", "") or "").upper() == "ADMIN" else user_branch_id(user)


def ensure_patient_branch_access(patient, user, requested_branch_id: str | None = None):
    require_tenant_row(patient, user, "Patient not found")
    branch_id = effective_branch_id(user, requested_branch_id)
    if branch_id and not belongs_to_branch(patient, branch_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return branch_id


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
