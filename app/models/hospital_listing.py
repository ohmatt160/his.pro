from sqlalchemy import Boolean, Column, String, Text, JSON, ForeignKey

from app.models.base_model import BaseModel


class HospitalListing(BaseModel):
    """Patient-facing public profile settings for a facility."""
    __tablename__ = "hospital_listings"

    facility_slug = Column(String(100), ForeignKey("facilities.slug"), unique=True, nullable=False, index=True)
    is_public = Column(Boolean, default=False)
    display_name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    phone = Column(String(20))
    email = Column(String(120))
    photos = Column(JSON, default=list)
    department_profiles = Column(JSON, default=dict)
