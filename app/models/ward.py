from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.models.base_model import BaseModel


class WardBed(BaseModel):
    """Physical ward bed inventory for a facility."""

    __tablename__ = "ward_beds"

    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    ward_name = Column(String(120), nullable=False, index=True)
    bed_number = Column(String(40), nullable=False)
    status = Column(String(30), default="AVAILABLE", index=True)
    notes = Column(Text)

    STATUSES = ["AVAILABLE", "OCCUPIED", "MAINTENANCE"]

    admissions = relationship("WardAdmission", back_populates="bed")


class WardAdmission(BaseModel):
    """Inpatient admission and nursing handover state."""

    __tablename__ = "ward_admissions"

    facility_slug = Column(String(100), ForeignKey("facilities.slug"), nullable=False, index=True)
    patient_id = Column(String(36), ForeignKey("patients.id"), nullable=False, index=True)
    bed_id = Column(String(36), ForeignKey("ward_beds.id"), nullable=True, index=True)
    admitted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    ward_name = Column(String(120), nullable=False, index=True)
    reason = Column(Text)
    acuity = Column(String(30), default="normal", index=True)
    status = Column(String(30), default="ACTIVE", index=True)
    observations = Column(JSON, default=list)
    nursing_notes = Column(JSON, default=list)
    admitted_at = Column(DateTime, default=datetime.utcnow)
    discharged_at = Column(DateTime)

    STATUSES = ["ACTIVE", "DISCHARGED", "TRANSFERRED"]
    ACUITY = ["normal", "urgent"]

    patient = relationship("Patient")
    bed = relationship("WardBed", back_populates="admissions")
