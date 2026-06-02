from typing import Dict

from pydantic import BaseModel


class ReportSection(BaseModel):
    total: int
    by_status: Dict[str, int] = {}


class RevenueReport(BaseModel):
    invoice_count: int
    outstanding_invoice_count: int
    invoiced_total: float
    payments_total: float
    outstanding_total: float


class InventoryReport(BaseModel):
    active_items: int
    low_stock_items: int
    stock_value: float


class FacilityReportSummary(BaseModel):
    facility_slug: str
    date_from: str
    date_to: str
    patients: ReportSection
    appointments: ReportSection
    consultations: ReportSection
    admissions: ReportSection
    queue: ReportSection
    laboratory: ReportSection
    radiology: ReportSection
    billing: RevenueReport
    inventory: InventoryReport
    alerts: ReportSection
    generated_at: str
