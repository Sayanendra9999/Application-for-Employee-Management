"""Employee module — Input validation & response formatting utilities."""

import re
from datetime import date


# ── Validators ───────────────────────────────────────────────────────────

def validate_phone(phone):
    """Validate phone number format. Returns (valid, cleaned_or_error)."""
    if not phone or not phone.strip():
        return True, ''
    cleaned = re.sub(r'[\s\-\(\)]', '', phone.strip())
    if not re.match(r'^\+?\d{7,15}$', cleaned):
        return False, 'Invalid phone number format'
    return True, phone.strip()


def validate_bank_account(account):
    """Validate bank account number. Returns (valid, error_message)."""
    if not account or not account.strip():
        return False, 'Bank account number is required'
    cleaned = account.strip()
    if len(cleaned) < 5 or len(cleaned) > 30:
        return False, 'Bank account must be 5-30 characters'
    return True, None


def validate_pan(pan):
    """Validate PAN number format (Indian). Returns (valid, error_message)."""
    if not pan or not pan.strip():
        return False, 'PAN number is required'
    cleaned = pan.strip().upper()
    if not re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', cleaned):
        return False, 'Invalid PAN format (expected: ABCDE1234F)'
    return True, None


def validate_expense_amount(amount):
    """Validate expense amount. Returns (valid, error_message)."""
    if amount is None:
        return False, 'Amount is required'
    if amount <= 0:
        return False, 'Amount must be greater than zero'
    if amount > 500000:
        return False, 'Amount exceeds maximum limit (₹5,00,000)'
    return True, None


def validate_date_not_future(d):
    """Validate that date is not in the future. Returns (valid, error_message)."""
    if d and d > date.today():
        return False, 'Date cannot be in the future'
    return True, None


# ── Response Formatters ──────────────────────────────────────────────────

FIELD_DISPLAY_NAMES = {
    'phone': 'Phone Number',
    'bank_account': 'Bank Account',
    'pan_number': 'PAN Number',
    'emergency_contact': 'Emergency Contact',
    'emergency_phone': 'Emergency Phone',
}


def get_field_display_name(field_name):
    """Get human-readable display name for a field."""
    return FIELD_DISPLAY_NAMES.get(field_name, field_name.replace('_', ' ').title())


def format_currency(amount):
    """Format amount as Indian Rupees."""
    if amount is None:
        return '₹0'
    return f'₹{amount:,.0f}'
