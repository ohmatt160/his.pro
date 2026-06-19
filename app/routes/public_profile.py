from typing import List
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.extensions import db_session, get_db
from app.models.facility import Facility
from app.models.hospital_listing import HospitalListing
from app.models.user import User
from app.schemas.public_profile import PublicProfileUpdate, PublicService
from app.utils.dependencies import role_required
from app.utils.validators import Validators

router = APIRouter(tags=["public-profile"])


def _facility_or_404(slug: str) -> Facility:
    facility = db_session.query(Facility).filter_by(slug=slug, is_active=True).first()
    if not facility:
        raise HTTPException(status_code=404, detail="Facility not found")
    return facility


def _require_facility_admin(current_user: User, facility: Facility) -> None:
    if current_user.role != "ADMIN" or current_user.facility_slug != facility.slug:
        raise HTTPException(status_code=403, detail="Admin access required")


def _listing_for(facility: Facility) -> HospitalListing:
    listing = db_session.query(HospitalListing).filter_by(facility_slug=facility.slug).first()
    if listing:
        return listing
    listing = HospitalListing(
        facility_slug=facility.slug,
        is_public=False,
        display_name=facility.name,
        description="",
        phone=facility.phone,
        email=facility.email,
        photos=[],
        department_profiles={},
    )
    db_session.add(listing)
    db_session.flush()
    return listing


def _normalize_services(services: list) -> list[dict]:
    normalized = []
    for service in services or []:
        if isinstance(service, str):
            normalized.append({
                "id": None,
                "name": service,
                "price": None,
                "duration": None,
                "description": None,
            })
        elif isinstance(service, dict):
            normalized.append({
                "id": service.get("id"),
                "name": service.get("name") or "",
                "price": service.get("price"),
                "duration": service.get("duration"),
                "description": service.get("description"),
            })
    return [service for service in normalized if service["name"]]


def _profile_response(facility: Facility, listing: HospitalListing) -> dict:
    profiles = listing.department_profiles or {}
    departments = []
    for dept in (facility.departments or []):
        profile = profiles.get(dept["id"], {})
        departments.append({
            "id": dept["id"],
            "name": dept.get("name", ""),
            "location": dept.get("location", ""),
            "is_visible": bool(profile.get("is_visible", dept.get("is_visible", False))),
            "services": _normalize_services(profile.get("services", dept.get("services", []))),
            "staff_ids": profile.get("staff_ids", []),
            "working_hours": profile.get("working_hours", {}),
            "photos": profile.get("photos", []),
        })
    return {
        "is_public": bool(listing.is_public),
        "display_name": listing.display_name or facility.name,
        "description": listing.description or "",
        "phone": listing.phone or facility.phone or "",
        "email": listing.email or facility.email or "",
        "photos": listing.photos or [],
        "departments": departments,
    }


@router.get("/facilities/{slug}/public-profile")
async def get_public_profile(
    slug: str,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db),
):
    facility = _facility_or_404(slug)
    _require_facility_admin(current_user, facility)
    listing = _listing_for(facility)
    db_session.commit()
    return _profile_response(facility, listing)


@router.put("/facilities/{slug}/public-profile")
async def update_public_profile(
    slug: str,
    data: PublicProfileUpdate,
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db),
):
    facility = _facility_or_404(slug)
    _require_facility_admin(current_user, facility)
    listing = _listing_for(facility)
    listing.is_public = data.is_public
    listing.display_name = Validators.sanitize_string(data.display_name or facility.name)
    listing.description = Validators.sanitize_string(data.description or "")
    listing.phone = Validators.sanitize_string(data.phone or "")
    listing.email = Validators.sanitize_string(data.email or "")
    listing.photos = data.photos or []
    profiles = listing.department_profiles or {}
    known_department_ids = {dept["id"] for dept in (facility.departments or [])}
    for dept in data.departments:
        if dept.id in known_department_ids:
            profiles[dept.id] = dept.model_dump()
    listing.department_profiles = profiles
    db_session.add(listing)
    db_session.commit()
    db_session.refresh(listing)
    return _profile_response(facility, listing)


@router.put("/facilities/{slug}/public-profile/departments/{dept_id}/services")
async def update_department_services(
    slug: str,
    dept_id: str,
    services: List[PublicService],
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db),
):
    facility = _facility_or_404(slug)
    _require_facility_admin(current_user, facility)
    if dept_id not in {dept["id"] for dept in (facility.departments or [])}:
        raise HTTPException(status_code=404, detail="Department not found")
    listing = _listing_for(facility)
    profiles = listing.department_profiles or {}
    profile = profiles.get(dept_id, {"id": dept_id, "is_visible": False})
    profile["services"] = [
        {**service.model_dump(), "id": service.id or str(uuid.uuid4())}
        for service in services
    ]
    profiles[dept_id] = profile
    listing.department_profiles = profiles
    db_session.add(listing)
    db_session.commit()
    return _profile_response(facility, listing)


@router.put("/facilities/{slug}/public-profile/departments/{dept_id}/staff")
async def update_public_staff(
    slug: str,
    dept_id: str,
    staff_ids: List[str],
    current_user: User = Depends(role_required('ADMIN')),
    db: Session = Depends(get_db),
):
    facility = _facility_or_404(slug)
    _require_facility_admin(current_user, facility)
    if dept_id not in {dept["id"] for dept in (facility.departments or [])}:
        raise HTTPException(status_code=404, detail="Department not found")
    listing = _listing_for(facility)
    profiles = listing.department_profiles or {}
    profile = profiles.get(dept_id, {"id": dept_id, "is_visible": False})
    profile["staff_ids"] = staff_ids
    profiles[dept_id] = profile
    listing.department_profiles = profiles
    db_session.add(listing)
    db_session.commit()
    return _profile_response(facility, listing)
