# HIS.Pro Backend Documentation

## API Route Naming Convention

The HIS.Pro backend follows RESTful API design principles with consistent naming conventions:

### Base Path Structure
All API routes are versioned under `/api/v1`:
```
Base Path: /api/v1/{resource}/{action_or_id}
```

### Resource Naming
- **Plural nouns** for collections (e.g., `/patients`, `/appointments`)
- **Singular nouns** for specific resources when combined with ID (e.g., `/patients/{patient_id}`)
- **Lowercase letters only** in all paths
- **Hyphens** (-) used to separate words in multi-word resource names (e.g., `/medical-records` would be used if needed)
- **Underscores** (_) used only in path parameter names (e.g., `{patient_id}`, `{facility_slug}`)

### Current Route Examples
| Resource | Collection Endpoint | Single Item Endpoint | Action Endpoint |
|----------|---------------------|----------------------|-----------------|
| Auth | `/api/v1/auth/register` | N/A | `/api/v1/auth/login` |
| Patients | `/api/v1/patients` | `/api/v1/patients/{patient_id}` | N/A |
| Facilities | `/api/v1/facilities` | `/api/v1/facilities/{slug}` | `/api/v1/facilities/{slug}/modules` |
| Appointments | `/api/v1/appointments` | `/api/v1/appointments/{appointment_id}` | N/A |

### Parameter Naming
- Path parameters use **snake_case** (e.g., `{patient_id}`, `{facility_slug}`)
- Query parameters use **snake_case** (e.g., `?page=1&per_page=20&search=john`)
- All parameter names are **lowercase**

## Number of Routes

The backend currently has **17 distinct API modules** (routers), each containing multiple endpoints:

1. Authentication (`auth`)
2. Patients (`patients`)
3. Appointments (`appointments`)
4. Laboratory (`laboratory`)
5. Pharmacy (`pharmacy`)
6. Billing (`billing`)
7. EMR (`emr`)
8. Users (`users`)
9. Password Reset (`password_reset`)
10. Facilities (`facilities`)
11. Radiology (`radiology`)
12. Inventory (`inventory`)
13. Queue (`queue`)
14. Alerts (`alerts`)
15. Dashboard (`dashboard`)
16. Audit Logs (`audit_logs`)
17. Files (`files`)

Each module contains between 2-5 endpoints (CRUD operations plus specific actions), resulting in approximately **60-70 total API endpoints**.

## How to Add a New Feature: Step-by-Step Example

Let's walk through adding a new "Medical Equipment Maintenance" feature as an example.

### Step 1: Create the Database Model
Create `app/models/equipment.py`:
```python
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from app.models.base_model import BaseModel

class Equipment(BaseModel):
    """Medical equipment model for tracking maintenance"""
    __tablename__ = 'equipment'
    
    name = Column(String(200), nullable=False)
    equipment_type = Column(String(100), nullable=False)  # e.g., MRI, X-ray, Ventilator
    serial_number = Column(String(100), unique=True)
    purchase_date = Column(DateTime)
    last_maintenance = Column(DateTime)
    next_maintenance_due = Column(DateTime)
    maintenance_interval_days = Column(Integer, default=90)
    is_active = Column(Boolean, default=True)
    facility_slug = Column(String(100), ForeignKey('facilities.slug'), nullable=True, index=True)
    notes = Column(Text)
    
    # Relationships
    facility = relationship('Facility', backref='equipment')
    
    def to_dict(self):
        data = super().to_dict()
        return data
```

### Step 2: Create the Service Layer
Create `app/services/equipment_service.py`:
```python
from app.models.equipment import Equipment
from app.extensions import db

class EquipmentService:
    @staticmethod
    def create_equipment(data, user_id, facility_slug=None):
        """Create new equipment record"""
        equipment = Equipment(
            name=data['name'],
            equipment_type=data['equipment_type'],
            serial_number=data.get('serial_number'),
            purchase_date=data.get('purchase_date'),
            last_maintenance=data.get('last_maintenance'),
            next_maintenance_due=data.get('next_maintenance_due'),
            maintenance_interval_days=data.get('maintenance_interval_days', 90),
            facility_slug=facility_slug
        )
        equipment.save()
        return equipment
    
    @staticmethod
    def get_equipment_by_id(equipment_id, facility_slug=None):
        """Get equipment by ID with optional facility filtering"""
        query = Equipment.query
        if facility_slug:
            query = query.filter_by(id=equipment_id, facility_slug=facility_slug)
        return query.first()
    
    @staticmethod
    def get_all_equipment(facility_slug=None, page=1, per_page=20, search=None):
        """Get paginated equipment list with filtering"""
        query = Equipment.query
        if facility_slug:
            query = query.filter_by(facility_slug=facility_slug)
        
        if search:
            query = query.filter(
                Equipment.name.ilike(f'%{search}%') |
                Equipment.equipment_type.ilike(f'%{search}%')
            )
        
        query = query.order_by(Equipment.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * per_page).limit(per_page).all()
        pages = (total + per_page - 1) // per_page
        
        return {
            'items': items,
            'total': total,
            'page': page,
            'per_page': per_page,
            'pages': pages
        }
    
    @staticmethod
    def update_equipment(equipment, data):
        """Update equipment information"""
        for key, value in data.items():
            if hasattr(equipment, key) and value is not None:
                setattr(equipment, key, value)
        equipment.save()
        return equipment
    
    @staticmethod
    def delete_equipment(equipment):
        """Soft delete equipment"""
        equipment.delete()
        return True
```

### Step 3: Create the API Router
Create `app/routes/equipment.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import logging

from app.extensions import get_db
from app.services.equipment_service import EquipmentService
from app.utils.dependencies import get_current_user, role_required
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/equipment", tags=["equipment"])

# Pydantic Models
class EquipmentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    equipment_type: str = Field(..., min_length=1, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    purchase_date: Optional[str] = None  # ISO date string
    last_maintenance: Optional[str] = None
    next_maintenance_due: Optional[str] = None
    maintenance_interval_days: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None

class EquipmentResponse(BaseModel):
    id: str
    name: str
    equipment_type: str
    serial_number: Optional[str]
    purchase_date: Optional[str]
    last_maintenance: Optional[str]
    next_maintenance_due: Optional[str]
    maintenance_interval_days: int
    is_active: bool
    facility_slug: Optional[str]
    created_at: str
    updated_at: Optional[str]

# Endpoints
@router.post("", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
async def create_equipment(
    equipment_data: EquipmentCreate,
    current_user: User = Depends(role_required('ADMIN', 'BIOMED')),
    db: Session = Depends(get_db)
):
    """Create new equipment record"""
    try:
        # Convert string dates to datetime objects if provided
        data = equipment_data.dict()
        date_fields = ['purchase_date', 'last_maintenance', 'next_maintenance_due']
        for field in date_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        equipment = EquipmentService.create_equipment(
            data=data,
            user_id=current_user.id,
            facility_slug=current_user.facility_slug
        )
        
        return EquipmentResponse(
            id=str(equipment.id),
            name=equipment.name,
            equipment_type=equipment.equipment_type,
            serial_number=equipment.serial_number,
            purchase_date=equipment.purchase_date.isoformat() if equipment.purchase_date else None,
            last_maintenance=equipment.last_maintenance.isoformat() if equipment.last_maintenance else None,
            next_maintenance_due=equipment.next_maintenance_due.isoformat() if equipment.next_maintenance_due else None,
            maintenance_interval_days=equipment.maintenance_interval_days,
            is_active=equipment.is_active,
            facility_slug=equipment.facility_slug,
            created_at=equipment.created_at.isoformat() if equipment.created_at else "",
            updated_at=equipment.updated_at.isoformat() if equipment.updated_at else None
        )
    except Exception as e:
        logger.error(f"Error creating equipment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create equipment")

@router.get("", response_model=List[EquipmentResponse])
async def get_equipment(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, max_length=100),
    current_user: User = Depends(role_required('ADMIN', 'BIOMED', 'NURSE')),
    db: Session = Depends(get_db)
):
    """Get paginated list of equipment"""
    try:
        facility_slug = current_user.facility_slug if current_user else None
        
        result = EquipmentService.get_all_equipment(
            facility_slug=facility_slug,
            page=page,
            per_page=per_page,
            search=search
        )
        
        equipment_list = []
        for equipment in result['items']:
            equipment_list.append(EquipmentResponse(
                id=str(equipment.id),
                name=equipment.name,
                equipment_type=equipment.equipment_type,
                serial_number=equipment.serial_number,
                purchase_date=equipment.purchase_date.isoformat() if equipment.purchase_date else None,
                last_maintenance=equipment.last_maintenance.isoformat() if equipment.last_maintenance else None,
                next_maintenance_due=equipment.next_maintenance_due.isoformat() if equipment.next_maintenance_due else None,
                maintenance_interval_days=equipment.maintenance_interval_days,
                is_active=equipment.is_active,
                facility_slug=equipment.facility_slug,
                created_at=equipment.created_at.isoformat() if equipment.created_at else "",
                updated_at=equipment.updated_at.isoformat() if equipment.updated_at else None
            ))
        
        return equipment_list
    except Exception as e:
        logger.error(f"Error retrieving equipment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve equipment")

# Additional endpoints (GET/{id}, PUT/{id}, DELETE/{id}) would follow similar patterns
```

### Step 4: Register the Router
In `app/main.py`, add:
```python
# Import the new router
from app.routes.equipment import router as equipment_router

# In the create_app function, include the router:
app.include_router(equipment_router, prefix="/api/v1")
```

### Step 5: Update Facility Modules (Optional)
If this feature should be facility-configurable, update `app/models/facility.py`:
```python
class Facility(BaseModel):
    # ... existing code ...
    
    # Available modules
    AVAILABLE_MODULES = [
        'appointments',
        'patients',
        'billing',
        'lab',
        'pharmacy',
        'radiology',
        'inventory',
        'medical_records',
        'reports',
        'dashboard',
        'equipment'  # Add new module here
    ]
```

### Step 6: Add Permissions (Optional)
Create a new role in your role management system (e.g., "BIOMED" for biomedical engineers) and update the `role_required` dependencies in your router as shown in the example.

### Step 7: Test the Implementation
1. Run migrations if using Alembic (not currently implemented but recommended)
2. Start the server: `python run.py`
3. Test endpoints using:
   - `POST /api/v1/equipment` to create equipment
   - `GET /api/v1/equipment` to list equipment
   - `GET /api/v1/equipment/{id}` to get specific equipment

## Key Principles Followed

1. **Separation of Concerns**: Each layer (model, service, router) has distinct responsibilities
2. **Dependency Injection**: Database sessions and user context injected via FastAPI dependencies
3. **Input Validation**: Pydantic models validate request data at the API boundary
4. **Error Handling**: Consistent HTTP exception handling with logging
5. **Multi-tenancy**: Automatic facility-based filtering using `facility_slug`
6. **Security**: Role-based access control protecting endpoints
7. **Scalability**: Pagination on list endpoints, connection pooling in database layer

This pattern ensures new features integrate seamlessly with existing code while maintaining consistency, security, and maintainability.