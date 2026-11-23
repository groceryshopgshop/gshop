# It will contain the controlled operations for:
# 1. Generating OTPs.
# 2. Securely hashing OTPs.
# 3. Managing OTP expiry and attempt limits.
# 4. Verifying submitted OTPs.
# 5. Updating phone numbers only after successful verification.
# 6. Preventing reuse of verification codes.


import secrets
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import models, transaction
from django.utils import timezone

from .models import ContactVerification, User
from .validators import validate_and_normalize_phone_number

OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_WAIT_SECONDS = 60


@transaction.atomic
def create_phone_change_verification(user, new_phone_number):
    new_phone_number = validate_and_normalize_phone_number(
        new_phone_number
    )
    locked_user = User.objects.select_for_update().get(pk=user.pk)

    if locked_user.phone_number == new_phone_number:
        raise ValueError("New phone number is the same as the current number.")

    if User.objects.filter(phone_number=new_phone_number).exclude(
        pk=locked_user.pk
    ).exists():
        raise ValueError("This phone number is already registered.")

    now = timezone.now()

    recent_request = ContactVerification.objects.filter(
        user=locked_user,
        purpose=ContactVerification.Purpose.PHONE_CHANGE,
        created_at__gte=now - timedelta(seconds=OTP_RESEND_WAIT_SECONDS),
    ).exists()

    if recent_request:
        raise ValueError("Please wait before requesting another OTP.")

    ContactVerification.objects.filter(
        user=locked_user,
        purpose=ContactVerification.Purpose.PHONE_CHANGE,
        verified_at__isnull=True,
        consumed_at__isnull=True,
    ).update(consumed_at=now)

    otp = f"{secrets.randbelow(1_000_000):06d}"

    verification = ContactVerification.objects.create(
        user=locked_user,
        contact_type=ContactVerification.ContactType.PHONE,
        purpose=ContactVerification.Purpose.PHONE_CHANGE,
        target_value=new_phone_number,
        code_hash=make_password(otp),
        expires_at=now + timedelta(minutes=OTP_EXPIRY_MINUTES),
    )

    return verification, otp



def verify_phone_change_and_update(user, verification_id, submitted_otp):
    error = None
    changed_phone = None

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(pk=user.pk)

        try:
            verification = ContactVerification.objects.select_for_update().get(
                pk=verification_id,
                user=locked_user,
                purpose=ContactVerification.Purpose.PHONE_CHANGE,
                contact_type=ContactVerification.ContactType.PHONE,
            )
        except ContactVerification.DoesNotExist:
            error = "Verification request not found."

        if error is None:
            now = timezone.now()

            if verification.consumed_at is not None:
                error = "This verification code has already been used."

            elif verification.verified_at is not None:
                error = "This verification has already been completed."

            elif verification.expires_at <= now:
                verification.consumed_at = now
                verification.save(update_fields=["consumed_at"])
                error = "Verification code has expired."

            elif verification.attempts >= OTP_MAX_ATTEMPTS:
                verification.consumed_at = now
                verification.save(update_fields=["consumed_at"])
                error = "Maximum verification attempts exceeded."

            else:
                verification.attempts += 1

                if not check_password(
                    submitted_otp,
                    verification.code_hash,
                ):
                    if verification.attempts >= OTP_MAX_ATTEMPTS:
                        verification.consumed_at = now

                    verification.save(
                        update_fields=["attempts", "consumed_at"]
                    )
                    error = "Invalid verification code."

                elif User.objects.filter(
                    phone_number=verification.target_value
                ).exclude(pk=locked_user.pk).exists():
                    verification.consumed_at = now
                    verification.save(
                        update_fields=["attempts", "consumed_at"]
                    )
                    error = "This phone number is already registered."

                else:
                    verification.verified_at = now
                    verification.consumed_at = now

                    verification.save(
                        update_fields=[
                            "attempts",
                            "verified_at",
                            "consumed_at",
                        ]
                    )

                    # Intentionally bypass the protected QuerySet.update()
                    # only after successful OTP verification.
                    models.QuerySet.update(
                        User.objects.filter(pk=locked_user.pk),
                        phone_number=verification.target_value,
                        phone_verified=True,
                    )

                    changed_phone = verification.target_value

    # Raise outside the transaction so failed-attempt counters
    # and expired-code consumption are committed.
    if error:
        raise ValueError(error)

    return changed_phone
