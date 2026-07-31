import csv
import io
import json
import re
import secrets
import string
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.facility import Facility
from app.models.inventory import Inventory
from app.models.patient import Patient
from app.models.user import User
from app.services.audit_log_service import AuditLogService
from app.utils.validators import Validators

MIGRATION_SOURCE_SYSTEMS = {
    "generic_csv",
    "generic_json",
    "excel",
    "csv",
    "openmrs",
    "bahmni",
    "dhis2",
    "other_his",
}

MIGRATION_IMPORT_MODES = {
    "patients",
    "staff",
    "appointments",
    "inventory",
    "full_archive",
}

MIGRATION_MAX_BYTES = 25 * 1024 * 1024
MAX_IMPORT_ROWS = 50_000

SOURCE_FIELD_ALIASES = {
    "openmrs": {
        "patients": {
            "first_name": ["given_name", "givenname", "preferred_name"],
            "last_name": ["family_name", "familyname"],
            "date_of_birth": ["birthdate", "birth_date"],
            "phone": ["telephone_number", "phone_number", "contact_number"],
            "email": ["email_address"],
            "address": ["address1", "address_1", "city_village", "cityvillage"],
            "external_id": ["identifier", "patient_identifier", "openmrs_id"],
        },
        "appointments": {
            "appointment_date": ["start_date_time", "startdatetime", "scheduled_date"],
            "patient_id": ["patient_uuid", "patient_identifier"],
            "doctor_username": ["provider", "provider_identifier", "clinician"],
        },
    },
    "bahmni": {
        "patients": {
            "first_name": ["given_name", "givenname"],
            "last_name": ["family_name", "familyname"],
            "date_of_birth": ["birthdate", "birth_date"],
            "phone": ["phone_number", "primary_contact", "telephone_number"],
            "external_id": ["identifier", "patient_identifier", "bahmni_id"],
        },
        "appointments": {
            "appointment_date": ["start_date_time", "startdatetime", "appointment_start_time"],
            "doctor_username": ["provider", "provider_name"],
        },
    },
    "dhis2": {
        "patients": {
            "first_name": ["first_name", "given_name", "firstname"],
            "last_name": ["last_name", "surname", "lastname"],
            "date_of_birth": ["date_of_birth", "dob", "birth_date"],
            "phone": ["phone_number", "phone"],
            "email": ["email_address", "email"],
            "external_id": ["tracked_entity_instance", "tei", "uid"],
        },
        "inventory": {
            "sku": ["code", "item_code", "uid"],
            "name": ["display_name", "item_name"],
            "current_stock": ["value", "quantity", "stock_on_hand"],
        },
    },
}

KNOWN_ENTITY_FIELDS = {
    "patients": {
        "first_name", "last_name", "date_of_birth", "dob", "birth_date", "gender", "sex",
        "phone", "phone_number", "mobile", "email", "email_address", "address", "blood_type",
        "blood_group", "emergency_contact_name", "next_of_kin", "emergency_contact_phone",
        "next_of_kin_phone", "medical_history", "history", "branch_id", "department_id",
        "branch", "department", "external_id", "identifier", "patient_identifier",
    },
    "staff": {
        "full_name", "name", "first_name", "last_name", "role", "staff_role", "email",
        "email_address", "username", "login_id", "phone", "phone_number", "department",
        "branch_id", "department_id", "branch", "password",
    },
    "inventory": {
        "sku", "item_code", "code", "name", "item_name", "description", "category", "unit",
        "reorder_level", "minimum_stock", "reorder_quantity", "reorder_qty", "current_stock",
        "quantity", "stock", "expiry_date", "expiration_date", "unit_cost", "cost",
    },
    "appointments": {
        "patient_id", "hispro_patient_id", "patient_email", "patient_phone", "email", "phone",
        "doctor_id", "clinician_id", "doctor_username", "doctor_email", "clinician",
        "appointment_date", "scheduled_at", "date", "duration_minutes", "duration", "status",
        "reason", "notes",
    },
}


@dataclass
class ParsedMigration:
    source_system: str
    import_mode: str
    file_name: str
    file_size: int
    detected_format: str
    rows_by_entity: dict[str, list[dict[str, Any]]]
    warnings: list[str]


def _sanitize_key(key: str) -> str:
    cleaned = Validators.sanitize_string(key or "").strip()
    cleaned = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", cleaned)
    return cleaned.lower().replace(" ", "_").replace("-", "_")


def _flatten_nested_export(row: dict[str, Any]) -> dict[str, Any]:
    flattened = dict(row)
    person = row.get("person") if isinstance(row.get("person"), dict) else None
    if person:
        names = person.get("names") if isinstance(person.get("names"), list) else []
        preferred_name = next((name for name in names if isinstance(name, dict) and name.get("preferred")), None)
        first_name = preferred_name or (names[0] if names else {})
        for source, target in (
            ("givenName", "given_name"),
            ("middleName", "middle_name"),
            ("familyName", "family_name"),
            ("gender", "gender"),
            ("birthdate", "birthdate"),
        ):
            value = first_name.get(source) if source in first_name else person.get(source)
            if value not in (None, ""):
                flattened[target] = value
        addresses = person.get("addresses") if isinstance(person.get("addresses"), list) else []
        if addresses and isinstance(addresses[0], dict):
            address = addresses[0]
            flattened.setdefault("address1", address.get("address1"))
            flattened.setdefault("city_village", address.get("cityVillage"))
        DataMigrationService._flatten_attribute_list(person.get("attributes"), flattened)

    DataMigrationService._flatten_attribute_list(row.get("attributes"), flattened)
    identifiers = row.get("identifiers") if isinstance(row.get("identifiers"), list) else []
    if identifiers and isinstance(identifiers[0], dict):
        flattened.setdefault("identifier", identifiers[0].get("identifier") or identifiers[0].get("value"))
    return flattened


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    row = _flatten_nested_export(row)
    return {
        _sanitize_key(str(key)): (value.strip() if isinstance(value, str) else value)
        for key, value in row.items()
        if key is not None
    }


def _first(row: dict[str, Any], *keys: str, default: Any = None) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return default


def _parse_date(value: Any, field_name: str) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"{field_name} must be a valid date")


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} is required")
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed.replace(tzinfo=None)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    raise ValueError(f"{field_name} must be a valid date/time")


def _parse_int(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return max(int(float(str(value))), 0)


def _parse_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0.00")
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _temp_password(length: int = 14) -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(char.islower() for char in password)
            and any(char.isupper() for char in password)
            and any(char.isdigit() for char in password)
        ):
            return password


def _entity_for_mode(import_mode: str) -> list[str]:
    if import_mode == "full_archive":
        return ["patients", "staff", "appointments", "inventory"]
    return [import_mode]


class DataMigrationService:
    @staticmethod
    def _flatten_attribute_list(attributes: Any, target: dict[str, Any]) -> None:
        if not isinstance(attributes, list):
            return
        for attribute in attributes:
            if not isinstance(attribute, dict):
                continue
            raw_key = (
                attribute.get("displayName")
                or attribute.get("name")
                or attribute.get("code")
                or attribute.get("attribute")
            )
            if isinstance(raw_key, dict):
                raw_key = raw_key.get("displayName") or raw_key.get("name") or raw_key.get("code")
            value = attribute.get("value")
            if raw_key and value not in (None, ""):
                target[str(raw_key)] = value

    @staticmethod
    def _apply_source_profile(source_system: str, rows_by_entity: dict[str, list[dict[str, Any]]]) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
        profile = SOURCE_FIELD_ALIASES.get(source_system, {})
        warnings: list[str] = []
        mapped: dict[str, list[dict[str, Any]]] = {}
        for entity, rows in rows_by_entity.items():
            entity_aliases = profile.get(entity, {})
            known = KNOWN_ENTITY_FIELDS.get(entity, set()) | set(entity_aliases.keys())
            mapped_rows = []
            unknown_fields: set[str] = set()
            for row in rows:
                normalized = dict(row)
                for canonical, aliases in entity_aliases.items():
                    if normalized.get(canonical) in (None, ""):
                        value = _first(normalized, *aliases)
                        if value not in (None, ""):
                            normalized[canonical] = value
                unknown_fields.update(key for key in normalized if key not in known and not key.startswith("_"))
                mapped_rows.append(normalized)
            if unknown_fields:
                warnings.append(
                    f"{entity}: {len(unknown_fields)} unsupported field(s) ignored: "
                    + ", ".join(sorted(unknown_fields)[:8])
                )
            mapped[entity] = mapped_rows
        return mapped, warnings

    @staticmethod
    async def parse_upload(upload: UploadFile, source_system: str, import_mode: str) -> ParsedMigration:
        source_system = Validators.sanitize_string(source_system).lower()
        import_mode = Validators.sanitize_string(import_mode).lower()
        if source_system not in MIGRATION_SOURCE_SYSTEMS:
            raise HTTPException(status_code=400, detail="Unsupported migration source")
        if import_mode not in MIGRATION_IMPORT_MODES:
            raise HTTPException(status_code=400, detail="Unsupported migration type")

        file_name = Validators.sanitize_string(upload.filename or "migration-file")
        extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
        if extension not in {"csv", "json"}:
            raise HTTPException(status_code=400, detail="Use a CSV or JSON migration file")

        content = await upload.read(MIGRATION_MAX_BYTES + 1)
        if len(content) > MIGRATION_MAX_BYTES:
            raise HTTPException(status_code=413, detail="Migration file is too large")
        if not content:
            raise HTTPException(status_code=400, detail="Migration file is empty")

        warnings: list[str] = []
        rows_by_entity: dict[str, list[dict[str, Any]]] = {entity: [] for entity in _entity_for_mode(import_mode)}
        if extension == "csv":
            text = content.decode("utf-8-sig", errors="replace")
            reader = csv.DictReader(io.StringIO(text))
            if not reader.fieldnames:
                raise HTTPException(status_code=400, detail="CSV header row is required")
            target = "patients" if import_mode == "full_archive" else import_mode
            risky_prefixes = ("=", "+", "-", "@")
            for index, row in enumerate(reader, start=1):
                normalized = _normalize_row(row)
                rows_by_entity.setdefault(target, []).append(normalized)
                if index <= 200 and any(str(value or "").startswith(risky_prefixes) for value in normalized.values()):
                    warnings.append("Formula-like values were detected and will be escaped during import.")
            if not rows_by_entity.get(target):
                warnings.append("No data rows were found after the CSV header.")
        else:
            try:
                payload = json.loads(content.decode("utf-8-sig"))
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="JSON migration file is invalid")
            rows_by_entity = DataMigrationService._rows_from_json(payload, import_mode, source_system)

        records_detected = sum(len(rows) for rows in rows_by_entity.values())
        if records_detected > MAX_IMPORT_ROWS:
            raise HTTPException(status_code=413, detail="Migration has too many records for one job")
        if records_detected > 10_000:
            warnings.append("Large imports are processed in the background and may take several minutes.")
        rows_by_entity, profile_warnings = DataMigrationService._apply_source_profile(source_system, rows_by_entity)
        warnings.extend(profile_warnings)

        return ParsedMigration(
            source_system=source_system,
            import_mode=import_mode,
            file_name=file_name,
            file_size=len(content),
            detected_format=extension,
            rows_by_entity=rows_by_entity,
            warnings=list(dict.fromkeys(warnings)),
        )

    @staticmethod
    def _rows_from_json(payload: Any, import_mode: str, source_system: str) -> dict[str, list[dict[str, Any]]]:
        entities = _entity_for_mode(import_mode)
        rows_by_entity = {entity: [] for entity in entities}
        if isinstance(payload, list):
            target = "patients" if import_mode == "full_archive" else import_mode
            rows_by_entity[target] = [_normalize_row(row) for row in payload if isinstance(row, dict)]
            return rows_by_entity
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="JSON migration must be an object or array")

        source_rows = DataMigrationService._source_rows_from_json(payload, import_mode, source_system)
        if source_rows is not None:
            return source_rows

        for entity in entities:
            value = payload.get(entity)
            if value is None and import_mode != "full_archive":
                value = payload
            if isinstance(value, list):
                rows_by_entity[entity] = [_normalize_row(row) for row in value if isinstance(row, dict)]
            elif isinstance(value, dict):
                rows_by_entity[entity] = [_normalize_row(value)]
        return rows_by_entity

    @staticmethod
    def _source_rows_from_json(payload: dict[str, Any], import_mode: str, source_system: str) -> dict[str, list[dict[str, Any]]] | None:
        target = "patients" if import_mode == "full_archive" else import_mode
        if source_system in {"openmrs", "bahmni"}:
            for key in ("results", "patients", "data"):
                value = payload.get(key)
                if isinstance(value, list):
                    return {entity: ([_normalize_row(row) for row in value if isinstance(row, dict)] if entity == target else []) for entity in _entity_for_mode(import_mode)}
        if source_system == "dhis2":
            for key in ("trackedEntityInstances", "tracked_entities", "events", "dataValues"):
                value = payload.get(key)
                if isinstance(value, list):
                    return {entity: ([_normalize_row(row) for row in value if isinstance(row, dict)] if entity == target else []) for entity in _entity_for_mode(import_mode)}
        return None

    @staticmethod
    def summarize(parsed: ParsedMigration, db: Session, facility: Facility) -> dict[str, Any]:
        entity_summaries = {}
        warnings = list(parsed.warnings)
        for entity, rows in parsed.rows_by_entity.items():
            prepared = DataMigrationService._prepare_entity(entity, rows, db, facility, None)
            entity_summaries[entity] = {
                "records_detected": len(rows),
                "valid": len(prepared["valid"]),
                "duplicates": len(prepared["duplicates"]),
                "errors": prepared["errors"][:50],
            }
            warnings.extend(prepared["warnings"])
        return {
            "status": "validated",
            "source_system": parsed.source_system,
            "import_mode": parsed.import_mode,
            "file_name": parsed.file_name,
            "file_size": parsed.file_size,
            "detected_format": parsed.detected_format,
            "records_detected": sum(len(rows) for rows in parsed.rows_by_entity.values()),
            "accepted_entities": [entity for entity, rows in parsed.rows_by_entity.items() if rows],
            "entity_summaries": entity_summaries,
            "warnings": list(dict.fromkeys(warnings)),
            "next_step": "queue_import",
        }

    @staticmethod
    def import_parsed(
        parsed: ParsedMigration,
        db: Session,
        facility: Facility,
        actor: User,
        request=None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        result = DataMigrationService.summarize(parsed, db, facility)
        imported: dict[str, int] = {}
        skipped: dict[str, int] = {}
        errors: dict[str, list[dict[str, Any]]] = {}
        if dry_run:
            result["status"] = "dry_run"
            result["records_imported"] = 0
            return result

        for entity, rows in parsed.rows_by_entity.items():
            prepared = DataMigrationService._prepare_entity(entity, rows, db, facility, actor)
            imported[entity] = 0
            skipped[entity] = len(prepared["duplicates"])
            errors[entity] = prepared["errors"][:50]
            for obj in prepared["valid"]:
                db.add(obj)
                imported[entity] += 1
            db.flush()

        AuditLogService.log_action(
            user_id=actor.id,
            action="IMPORT_DATA_MIGRATION",
            resource_type="facility",
            resource_id=facility.id,
            facility_slug=facility.slug,
            details={
                "source_system": parsed.source_system,
                "import_mode": parsed.import_mode,
                "file_name": parsed.file_name,
                "imported": imported,
                "skipped": skipped,
                "errors": {key: len(value) for key, value in errors.items()},
            },
            request=request,
            commit=False,
            raise_on_error=True,
            session=db,
        )
        result["status"] = "completed"
        result["records_imported"] = sum(imported.values())
        result["imported"] = imported
        result["skipped_duplicates"] = skipped
        result["errors"] = errors
        return result

    @staticmethod
    def _prepare_entity(entity: str, rows: list[dict[str, Any]], db: Session, facility: Facility, actor: User | None) -> dict:
        if entity == "patients":
            return DataMigrationService._prepare_patients(rows, db, facility, actor)
        if entity == "staff":
            return DataMigrationService._prepare_staff(rows, db, facility)
        if entity == "inventory":
            return DataMigrationService._prepare_inventory(rows, db, facility)
        if entity == "appointments":
            return DataMigrationService._prepare_appointments(rows, db, facility)
        return {"valid": [], "duplicates": [], "errors": [{"row": 0, "error": "Unsupported entity"}], "warnings": []}

    @staticmethod
    def _prepare_patients(rows, db, facility, actor):
        valid, duplicates, errors = [], [], []
        seen = set()
        for index, row in enumerate(rows, start=1):
            try:
                first_name = Validators.sanitize_string(_first(row, "first_name", "firstname", "given_name"))
                last_name = Validators.sanitize_string(_first(row, "last_name", "lastname", "surname", "family_name"))
                dob = _parse_date(_first(row, "date_of_birth", "dob", "birth_date"), "date_of_birth")
                if not first_name or not last_name or not dob:
                    raise ValueError("first_name, last_name and date_of_birth are required")
                email = Validators.sanitize_string(_first(row, "email", "email_address", default="") or "") or None
                phone = Validators.sanitize_string(_first(row, "phone", "phone_number", "mobile", default="") or "") or None
                key = (first_name.lower(), last_name.lower(), dob.isoformat(), email or phone or "")
                duplicate_query = db.query(Patient).filter(
                    Patient.facility_slug == facility.slug,
                    Patient.is_active == True,
                    Patient.first_name == first_name,
                    Patient.last_name == last_name,
                    Patient.date_of_birth == dob,
                )
                if email and phone:
                    duplicate_query = duplicate_query.filter(or_(Patient.email == email, Patient.phone == phone))
                elif email:
                    duplicate_query = duplicate_query.filter(Patient.email == email)
                elif phone:
                    duplicate_query = duplicate_query.filter(Patient.phone == phone)
                else:
                    duplicate_query = duplicate_query.filter(Patient.id == "__none__")
                duplicate = key in seen or duplicate_query.first()
                if duplicate:
                    duplicates.append({"row": index, "reason": "Patient already exists"})
                    continue
                seen.add(key)
                valid.append(Patient(
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=dob,
                    gender=DataMigrationService._normalize_gender(_first(row, "gender", "sex")),
                    phone=phone,
                    email=email,
                    address=Validators.sanitize_string(_first(row, "address", default="") or "") or None,
                    blood_type=DataMigrationService._normalize_blood_type(_first(row, "blood_type", "blood_group")),
                    emergency_contact_name=Validators.sanitize_string(_first(row, "emergency_contact_name", "next_of_kin", default="") or "") or None,
                    emergency_contact_phone=Validators.sanitize_string(_first(row, "emergency_contact_phone", "next_of_kin_phone", default="") or "") or None,
                    medical_history={"source_system_notes": _first(row, "medical_history", "history", default="")},
                    created_by=actor.id if actor else None,
                    facility_id=facility.id,
                    facility_slug=facility.slug,
                    branch_id=DataMigrationService._branch_id(row, db, facility),
                    department_id=DataMigrationService._branch_id(row, db, facility),
                ))
            except Exception as exc:
                errors.append({"row": index, "error": str(exc)})
        return {"valid": valid, "duplicates": duplicates, "errors": errors, "warnings": []}

    @staticmethod
    def _prepare_staff(rows, db, facility):
        valid, duplicates, errors = [], [], []
        seen = set()
        for index, row in enumerate(rows, start=1):
            try:
                full_name = Validators.sanitize_string(_first(row, "full_name", "name", default="") or "")
                first_name = Validators.sanitize_string(_first(row, "first_name", default="") or "")
                last_name = Validators.sanitize_string(_first(row, "last_name", default="") or "")
                if full_name and not first_name:
                    parts = full_name.split()
                    first_name = parts[0]
                    last_name = " ".join(parts[1:]) or "Member"
                role = DataMigrationService._normalize_role(_first(row, "role", "staff_role"))
                email = Validators.sanitize_string(_first(row, "email", "email_address"))
                username = Validators.sanitize_string(_first(row, "username", "login_id", default=email.split("@")[0] if email else ""))
                if not first_name or not last_name or not role or not email or not username:
                    raise ValueError("first_name, last_name, role, email and username are required")
                key = (username.lower(), email.lower())
                if key in seen or db.query(User).filter(or_(User.username == username, User.email == email)).first():
                    duplicates.append({"row": index, "reason": "Staff username or email already exists"})
                    continue
                seen.add(key)
                user = User(
                    username=username,
                    email=email.lower(),
                    role=role,
                    first_name=first_name,
                    last_name=last_name,
                    phone=Validators.sanitize_string(_first(row, "phone", "phone_number", default="") or "") or None,
                    department=Validators.sanitize_string(_first(row, "department", default="") or "") or None,
                    facility_id=facility.id,
                    facility_slug=facility.slug,
                    branch_id=DataMigrationService._branch_id(row, db, facility),
                    department_id=DataMigrationService._branch_id(row, db, facility),
                    must_change_password=True,
                )
                user.set_password(_first(row, "password", default="") or _temp_password())
                valid.append(user)
            except Exception as exc:
                errors.append({"row": index, "error": str(exc)})
        return {"valid": valid, "duplicates": duplicates, "errors": errors, "warnings": []}

    @staticmethod
    def _prepare_inventory(rows, db, facility):
        valid, duplicates, errors = [], [], []
        seen = set()
        for index, row in enumerate(rows, start=1):
            try:
                sku = Validators.sanitize_string(_first(row, "sku", "item_code", "code"))
                name = Validators.sanitize_string(_first(row, "name", "item_name", "description"))
                category = str(_first(row, "category", default="supplies")).lower()
                if category not in Inventory.CATEGORIES:
                    category = "supplies"
                if not sku or not name:
                    raise ValueError("sku and name are required")
                if sku.lower() in seen or db.query(Inventory).filter_by(facility_slug=facility.slug, sku=sku).first():
                    duplicates.append({"row": index, "reason": "Inventory SKU already exists"})
                    continue
                seen.add(sku.lower())
                valid.append(Inventory(
                    facility_id=facility.id,
                    facility_slug=facility.slug,
                    name=name,
                    sku=sku,
                    category=category,
                    unit=Validators.sanitize_string(_first(row, "unit", default="unit")),
                    reorder_level=_parse_int(_first(row, "reorder_level", "minimum_stock"), 0),
                    reorder_quantity=_parse_int(_first(row, "reorder_quantity", "reorder_qty"), 0),
                    current_stock=_parse_int(_first(row, "current_stock", "quantity", "stock"), 0),
                    expiry_date=_parse_date(_first(row, "expiry_date", "expiration_date"), "expiry_date"),
                    unit_cost=_parse_decimal(_first(row, "unit_cost", "cost", default="0")),
                    is_active=True,
                ))
            except Exception as exc:
                errors.append({"row": index, "error": str(exc)})
        return {"valid": valid, "duplicates": duplicates, "errors": errors, "warnings": []}

    @staticmethod
    def _prepare_appointments(rows, db, facility):
        valid, duplicates, errors = [], [], []
        for index, row in enumerate(rows, start=1):
            try:
                patient = DataMigrationService._find_patient(row, db, facility)
                doctor = DataMigrationService._find_doctor(row, db, facility)
                appointment_date = _parse_datetime(_first(row, "appointment_date", "scheduled_at", "date"), "appointment_date")
                if not patient or not doctor:
                    raise ValueError("patient and doctor must already exist in this facility")
                duplicate = db.query(Appointment).filter_by(
                    facility_slug=facility.slug,
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    appointment_date=appointment_date,
                ).first()
                if duplicate:
                    duplicates.append({"row": index, "reason": "Appointment already exists"})
                    continue
                valid.append(Appointment(
                    patient_id=patient.id,
                    doctor_id=doctor.id,
                    facility_id=facility.id,
                    facility_slug=facility.slug,
                    branch_id=patient.branch_id or patient.department_id,
                    department_id=patient.department_id or patient.branch_id,
                    appointment_date=appointment_date,
                    scheduled_time=appointment_date,
                    duration_minutes=_parse_int(_first(row, "duration_minutes", "duration"), 30),
                    status=str(_first(row, "status", default="SCHEDULED")).upper(),
                    reason=Validators.sanitize_string(_first(row, "reason", default="") or "") or None,
                    notes=Validators.sanitize_string(_first(row, "notes", default="") or "") or None,
                ))
            except Exception as exc:
                errors.append({"row": index, "error": str(exc)})
        return {"valid": valid, "duplicates": duplicates, "errors": errors, "warnings": []}

    @staticmethod
    def _find_patient(row, db, facility) -> Patient | None:
        patient_id = _first(row, "patient_id", "hispro_patient_id")
        if patient_id:
            return db.query(Patient).filter_by(id=patient_id, facility_slug=facility.slug, is_active=True).first()
        email = _first(row, "patient_email", "email")
        phone = _first(row, "patient_phone", "phone")
        query = db.query(Patient).filter_by(facility_slug=facility.slug, is_active=True)
        if email:
            return query.filter(Patient.email == email).first()
        if phone:
            return query.filter(Patient.phone == phone).first()
        return None

    @staticmethod
    def _find_doctor(row, db, facility) -> User | None:
        doctor_id = _first(row, "doctor_id", "clinician_id")
        if doctor_id:
            return db.query(User).filter_by(id=doctor_id, facility_slug=facility.slug, is_active=True).first()
        login = _first(row, "doctor_username", "doctor_email", "clinician")
        if not login:
            return None
        return db.query(User).filter(
            User.facility_slug == facility.slug,
            User.is_active == True,
            User.role.in_(["DOCTOR", "ADMIN"]),
            or_(User.username == login, User.email == str(login).lower()),
        ).first()

    @staticmethod
    def _branch_id(row, db, facility) -> str | None:
        value = _first(row, "branch_id", "department_id", "branch", "department")
        if not value:
            return None
        branch = db.query(Branch).filter(
            Branch.facility_slug == facility.slug,
            Branch.is_active == True,
            or_(Branch.id == str(value), Branch.slug == str(value)),
        ).first()
        return str(branch.id) if branch else None

    @staticmethod
    def _normalize_gender(value: Any) -> str | None:
        if not value:
            return None
        text = str(value).strip().upper()
        mapping = {"M": "MALE", "MALE": "MALE", "F": "FEMALE", "FEMALE": "FEMALE", "O": "OTHER", "OTHER": "OTHER"}
        return mapping.get(text)

    @staticmethod
    def _normalize_blood_type(value: Any) -> str | None:
        if not value:
            return None
        text = str(value).strip().upper().replace(" ", "")
        return text if text in {"A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"} else None

    @staticmethod
    def _normalize_role(value: Any) -> str | None:
        text = str(value or "").strip().upper().replace(" ", "_")
        mapping = {
            "RECEPTION": "RECEPTIONIST",
            "RECEPTIONIST": "RECEPTIONIST",
            "LAB": "LAB_TECH",
            "LAB_TECH": "LAB_TECH",
            "DOCTOR": "DOCTOR",
            "NURSE": "NURSE",
            "PHARMACIST": "PHARMACIST",
            "BILLING": "BILLING",
            "BILLING_OFFICER": "BILLING",
            "CASHIER": "BILLING",
            "ADMIN": "ADMIN",
            "BRANCH_ADMIN": "BRANCH_ADMIN",
        }
        return mapping.get(text)
