from sqlalchemy import Column, String, Text, Boolean, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.models.base_model import BaseModel


class Branch(BaseModel):
    """A branch, clinic, campus, wing, or physical location under one facility tenant."""
    __tablename__ = "branches"
    __table_args__ = (
        UniqueConstraint("facility_slug", "slug", name="uq_branch_facility_slug"),
    )

    facility_id = Column(String(36), ForeignKey("facilities.id"), nullable=False, index=True)
    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    name = Column(String(160), nullable=False)
    slug = Column(String(120), nullable=False, index=True)
    location = Column(Text)
    address = Column(Text)
    phone = Column(String(30))
    email = Column(String(120))
    modules = Column(JSON, default=list)
    settings = Column(JSON, default=dict)
    is_public = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    facility = relationship("Facility", back_populates="branches", foreign_keys=[facility_slug])

    def to_dict(self):
        return super().to_dict()

