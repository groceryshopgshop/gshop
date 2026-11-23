# How it works
# - 9876543210 is interpreted as an Indian number.
# - +919876543210 is parsed as an international-format Indian number.
# - +14155552671 is parsed as a US number.
# - Invalid or impossible numbers are rejected.
# - Valid numbers are returned in E.164 format.
import phonenumbers

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
def validate_and_normalize_phone_number(value):
    if not value:
        raise ValidationError("Phone number is required.")

    if not value.lstrip("+").isdigit() or value.count("+") > 1 or (
        "+" in value and not value.startswith("+")
    ):
        raise ValidationError(
            "Phone number must contain digits only, with an optional leading +."
        )

    if not value:
        raise ValidationError("Phone number is required.")

    try:
        if value.startswith("+"):
            parsed_number = phonenumbers.parse(value, None)
        else:
            # Bare numbers are interpreted as Indian numbers.
            parsed_number = phonenumbers.parse(value, "IN")

    except phonenumbers.NumberParseException:
        raise ValidationError("Enter a valid phone number with country code.")

    if not phonenumbers.is_possible_number(parsed_number):
        raise ValidationError("Phone number has an invalid length.")

    if not phonenumbers.is_valid_number(parsed_number):
        raise ValidationError("Enter a valid phone number.")

    return phonenumbers.format_number(
        parsed_number,
        phonenumbers.PhoneNumberFormat.E164,
    )


def validate_phone_number(value):
    validate_and_normalize_phone_number(value)




def validate_and_normalize_email(value):
    if not value:
        raise ValidationError("Email address is required.")

    normalized_email = str(value).strip().lower()

    try:
        validate_email(normalized_email)
    except ValidationError:
        raise ValidationError("Enter a valid email address.")

    return normalized_email


def validate_email_address(value):
    validate_and_normalize_email(value)
