from fastapi import APIRouter

from app.routes.alerts import router as alerts_router
from app.routes.appointments import router as appointments_router
from app.routes.audit_logs import router as audit_logs_router
from app.routes.auth import router as auth_router
from app.routes.billing import router as billing_router
from app.routes.consultations import router as consultations_router
from app.routes.dashboard import router as dashboard_router
from app.routes.emr import router as emr_router
from app.routes.facilities import router as facilities_router
from app.routes.files import router as files_router
from app.routes.files_new import router as files_new_router
from app.routes.inventory import router as inventory_router
from app.routes.laboratory import router as laboratory_router
from app.routes.password_reset import router as password_reset_router
from app.routes.patients import router as patients_router
from app.routes.pharmacy import router as pharmacy_router
from app.routes.queue import router as queue_router
from app.routes.radiology import router as radiology_router
from app.routes.reports import router as reports_router
from app.routes.suppliers import router as suppliers_router
from app.routes.users import router as users_router
from app.routes.wards import router as wards_router


api_router = APIRouter()
api_router.include_router(alerts_router)
api_router.include_router(appointments_router)
api_router.include_router(audit_logs_router)
api_router.include_router(auth_router)
api_router.include_router(billing_router)
api_router.include_router(consultations_router)
api_router.include_router(dashboard_router)
api_router.include_router(emr_router)
api_router.include_router(facilities_router)
api_router.include_router(files_router)
api_router.include_router(files_new_router)
api_router.include_router(inventory_router)
api_router.include_router(laboratory_router)
api_router.include_router(password_reset_router)
api_router.include_router(patients_router)
api_router.include_router(pharmacy_router)
api_router.include_router(queue_router)
api_router.include_router(radiology_router)
api_router.include_router(reports_router)
api_router.include_router(suppliers_router)
api_router.include_router(users_router)
api_router.include_router(wards_router)
