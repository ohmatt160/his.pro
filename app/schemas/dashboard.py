from pydantic import BaseModel


class DashboardStats(BaseModel):
    facility_slug: str
    patient_count: int
    today_appointments: int
    pending_lab_orders: int
    pending_radiology_orders: int
    low_inventory_items: int
    active_alerts: int
    queue_status: dict
    active_queue_count: int
    generated_at: str
