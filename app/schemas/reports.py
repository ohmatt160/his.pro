from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    total: int
    by_status: Dict[str, int] = Field(default_factory=dict)


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


class ReportMetricRow(BaseModel):
    label: str
    value: float | int
    metadata: dict = Field(default_factory=dict)


class RevenueDetailReport(BaseModel):
    facility_slug: str
    date_from: str
    date_to: str
    invoice_count: int
    paid_invoice_count: int
    outstanding_invoice_count: int
    invoiced_total: float
    collected_total: float
    outstanding_total: float
    receipt_count: int
    payment_methods: List[ReportMetricRow]
    invoice_statuses: List[ReportMetricRow]
    recent_payments: List[ReportMetricRow]
    generated_at: str


class DepartmentActivityRow(BaseModel):
    department: str
    module: str
    total: int
    completed: int
    pending: int
    by_status: Dict[str, int] = Field(default_factory=dict)


class DepartmentActivityReport(BaseModel):
    facility_slug: str
    date_from: str
    date_to: str
    departments: List[DepartmentActivityRow]
    generated_at: str


class OperationsReport(BaseModel):
    facility_slug: str
    date_from: str
    date_to: str
    queue: ReportSection
    appointments: ReportSection
    active_tasks_by_role: List[ReportMetricRow]
    high_priority_tasks: List[ReportMetricRow]
    generated_at: str


class InventoryDetailItem(BaseModel):
    id: str
    name: str
    sku: str
    category: str
    current_stock: int
    reorder_level: int
    reorder_quantity: int
    unit: str
    stock_value: float
    supplier_name: Optional[str] = None


class InventoryDetailReport(BaseModel):
    facility_slug: str
    active_items: int
    low_stock_items: int
    stock_value: float
    reorder_items: List[InventoryDetailItem]
    by_category: List[ReportMetricRow]
    generated_at: str
