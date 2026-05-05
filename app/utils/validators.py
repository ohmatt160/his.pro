"""
Input validation and sanitization utilities for the HIS.Pro API
"""

import re
from datetime import datetime, date
from typing import Optional, Tuple, Any
from marshmallow import ValidationError

class Validators:
    """Comprehensive validation utilities"""
    
    @staticmethod
    def generate_slug(name: str) -> str:
        """
        Generate URL-friendly slug from name
        """
        # Convert to lowercase and replace spaces/special chars with dashes
        slug = name.lower().strip()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'[\s-]+', '-', slug)  # Replace spaces/dashes with single dash
        slug = slug.strip('-')
        return slug
    
    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format
        Returns: (is_valid, error_message)
        """
        if not email:
            return False, "Email is required"
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        
        if len(email) > 254:
            return False, "Email is too long"
        
        return True, None
    
    @staticmethod
    def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
        """
        Validate phone number format
        Returns: (is_valid, error_message)
        """
        if not phone:
            return True, None  # Phone is optional
        
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
        
        if not cleaned.isdigit():
            return False, "Phone number must contain only digits"
        
        if len(cleaned) < 10:
            return False, "Phone number is too short"
        
        if len(cleaned) > 15:
            return False, "Phone number is too long"
        
        return True, None
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength
        Returns: (is_valid, error_message)
        """
        if not password:
            return False, "Password is required"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
        
        if len(password) > 128:
            return False, "Password is too long"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, None
    
    @staticmethod
    def validate_date(date_str: str, format: str = '%Y-%m-%d') -> Tuple[bool, Optional[str], Optional[date]]:
        """
        Validate date format
        Returns: (is_valid, error_message, parsed_date)
        """
        if not date_str:
            return False, "Date is required", None
        
        try:
            parsed_date = datetime.strptime(date_str, format).date()
            return True, None, parsed_date
        except ValueError:
            return False, f"Invalid date format. Expected format: {format}", None
    
    @staticmethod
    def validate_datetime(datetime_str: str, format: str = '%Y-%m-%dT%H:%M:%S') -> Tuple[bool, Optional[str], Optional[datetime]]:
        """
        Validate datetime format
        Returns: (is_valid, error_message, parsed_datetime)
        """
        if not datetime_str:
            return False, "Datetime is required", None
        
        try:
            parsed_datetime = datetime.strptime(datetime_str, format)
            return True, None, parsed_datetime
        except ValueError:
            return False, f"Invalid datetime format. Expected format: {format}", None
    
    @staticmethod
    def validate_string(value: str, min_length: int = 0, max_length: int = 255, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
        """
        Validate string length
        Returns: (is_valid, error_message)
        """
        if not value and min_length > 0:
            return False, f"{field_name} is required"
        
        if value and len(value) < min_length:
            return False, f"{field_name} must be at least {min_length} characters"
        
        if value and len(value) > max_length:
            return False, f"{field_name} must be at most {max_length} characters"
        
        return True, None
    
    @staticmethod
    def validate_integer(value: Any, min_value: int = None, max_value: int = None, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
        """
        Validate integer value
        Returns: (is_valid, error_message)
        """
        if value is None:
            return False, f"{field_name} is required"
        
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            return False, f"{field_name} must be an integer"
        
        if min_value is not None and int_value < min_value:
            return False, f"{field_name} must be at least {min_value}"
        
        if max_value is not None and int_value > max_value:
            return False, f"{field_name} must be at most {max_value}"
        
        return True, None
    
    @staticmethod
    def validate_float(value: Any, min_value: float = None, max_value: float = None, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
        """
        Validate float value
        Returns: (is_valid, error_message)
        """
        if value is None:
            return False, f"{field_name} is required"
        
        try:
            float_value = float(value)
        except (ValueError, TypeError):
            return False, f"{field_name} must be a number"
        
        if min_value is not None and float_value < min_value:
            return False, f"{field_name} must be at least {min_value}"
        
        if max_value is not None and float_value > max_value:
            return False, f"{field_name} must be at most {max_value}"
        
        return True, None
    
    @staticmethod
    def validate_enum(value: str, allowed_values: list, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
        """
        Validate enum value
        Returns: (is_valid, error_message)
        """
        if not value:
            return False, f"{field_name} is required"
        
        if value not in allowed_values:
            return False, f"{field_name} must be one of: {', '.join(allowed_values)}"
        
        return True, None
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """
        Sanitize string input by removing potentially dangerous characters
        """
        if not value:
            return value
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Remove control characters except newlines and tabs
        value = re.sub(r'[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)
        
        # Strip leading/trailing whitespace
        value = value.strip()
        
        return value
    
    @staticmethod
    def sanitize_html(value: str) -> str:
        """
        Sanitize HTML content by escaping special characters
        """
        if not value:
            return value
        
        # Escape HTML special characters
        value = value.replace('&', '&amp;')
        value = value.replace('<', '&lt;')
        value = value.replace('>', '&gt;')
        value = value.replace('"', '&quot;')
        value = value.replace("'", '&#x27;')
        
        return value
    
    @staticmethod
    def validate_uuid(value: str, field_name: str = "Field") -> Tuple[bool, Optional[str]]:
        """
        Validate UUID format
        Returns: (is_valid, error_message)
        """
        if not value:
            return False, f"{field_name} is required"
        
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        if not re.match(uuid_pattern, value, re.IGNORECASE):
            return False, f"{field_name} must be a valid UUID"
        
        return True, None
    
    @staticmethod
    def validate_pagination(page: int, per_page: int) -> Tuple[bool, Optional[str]]:
        """
        Validate pagination parameters
        Returns: (is_valid, error_message)
        """
        if page < 1:
            return False, "Page must be at least 1"
        
        if per_page < 1:
            return False, "Per page must be at least 1"
        
        if per_page > 100:
            return False, "Per page must be at most 100"
        
        return True, None


def validate_request_data(data: dict, validation_rules: dict) -> Tuple[bool, dict]:
    """
    Validate request data against validation rules
    
    Args:
        data: Request data dictionary
        validation_rules: Dictionary of field names and their validation rules
    
    Returns:
        Tuple of (is_valid, errors_dict)
    """
    errors = {}
    
    for field, rules in validation_rules.items():
        value = data.get(field)
        
        for rule in rules:
            if rule['type'] == 'required' and not value:
                errors[field] = f"{field} is required"
                break
            elif rule['type'] == 'email' and value:
                is_valid, error = Validators.validate_email(value)
                if not is_valid:
                    errors[field] = error
                    break
            elif rule['type'] == 'phone' and value:
                is_valid, error = Validators.validate_phone(value)
                if not is_valid:
                    errors[field] = error
                    break
            elif rule['type'] == 'password' and value:
                is_valid, error = Validators.validate_password(value)
                if not is_valid:
                    errors[field] = error
                    break
            elif rule['type'] == 'string' and value:
                is_valid, error = Validators.validate_string(
                    value,
                    min_length=rule.get('min_length', 0),
                    max_length=rule.get('max_length', 255),
                    field_name=field
                )
                if not is_valid:
                    errors[field] = error
                    break
            elif rule['type'] == 'integer' and value is not None:
                is_valid, error = Validators.validate_integer(
                    value,
                    min_value=rule.get('min_value'),
                    max_value=rule.get('max_value'),
                    field_name=field
                )
                if not is_valid:
                    errors[field] = error
                    break
            elif rule['type'] == 'enum' and value:
                is_valid, error = Validators.validate_enum(
                    value,
                    allowed_values=rule.get('values', []),
                    field_name=field
                )
                if not is_valid:
                    errors[field] = error
                    break
    
    return len(errors) == 0, errors
