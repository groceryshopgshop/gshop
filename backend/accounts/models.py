
import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from .validators import (
    validate_and_normalize_email,
    validate_email_address,
    validate_and_normalize_phone_number,
    validate_phone_number,
)
from django.core.exceptions import ValidationError

class UserQuerySet(models.QuerySet):

    PROTECTED_FIELDS = {"email", "phone_number"}

    def update(self, **kwargs):
        protected = self.PROTECTED_FIELDS.intersection(kwargs)

        if protected:
            raise ValueError(
                "Email address cannot be changed after registration."
            )

        return super().update(**kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        protected = self.PROTECTED_FIELDS.intersection(fields)

        if protected:
            raise ValueError(
                "Email address cannot be changed after registration."
            )

        return super().bulk_update(objs, fields, batch_size=batch_size)



class UserManager(BaseUserManager.from_queryset(UserQuerySet)):
    def create_user(self, email, phone_number, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")

        if not phone_number:
            raise ValueError("Phone number is required.")

        if not full_name:
            raise ValueError("Full name is required.")

        if not password:
            raise ValueError("Password is required.")

        email = validate_and_normalize_email(email)
        phone_number = validate_and_normalize_phone_number(phone_number)
        full_name = full_name.strip()

        user = self.model(
            email=email,
            phone_number=phone_number,
            full_name=full_name,
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, phone_number, full_name, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(
            email=email,
            phone_number=phone_number,
            full_name=full_name,
            password=password,
            **extra_fields,
        )


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    full_name = models.CharField(max_length=150)

    email = models.EmailField(
        max_length=254,
        unique=True,
        validators=[validate_email_address],
    )

    phone_number = models.CharField(
        max_length=20,
        unique=True,
        validators=[validate_phone_number],
    )

    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone_number", "full_name"]

    class Meta:
        db_table = "accounts_user"
        ordering = ["-date_joined"]
    
        
        
    def clean_fields(self, exclude=None):
        errors = {}

        if self.email:
            try:
                self.email = validate_and_normalize_email(self.email)
            except ValidationError as error:
                errors["email"] = error.messages

        if self.phone_number:
            try:
                self.phone_number = validate_and_normalize_phone_number(
                    self.phone_number
                )
            except ValidationError as error:
                errors["phone_number"] = error.messages

        if errors:
            raise ValidationError(errors)

        super().clean_fields(exclude=exclude)

    
    def save(self, *args, **kwargs):
        self.email = validate_and_normalize_email(self.email)
        self.phone_number = validate_and_normalize_phone_number(
            self.phone_number
        )

        if self.pk:
            old_user = type(self).objects.filter(pk=self.pk).only(
                "email",
                "phone_number",
            ).first()

            if old_user:
                if old_user.email != self.email:
                    raise ValueError(
                        "Email address cannot be changed after registration."
                    )

                if old_user.phone_number != self.phone_number:
                    raise ValueError(
                        "Phone number can only be changed after successful verification."
                    )

        super().save(*args, **kwargs)


    def __str__(self):
        return self.email




class ContactVerification(models.Model):

    class ContactType(models.TextChoices):
        EMAIL = "email", "Email"
        PHONE = "phone", "Phone"

    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "email_verification", "Email Verification"
        PHONE_VERIFICATION = "phone_verification", "Phone Verification"
        PHONE_CHANGE = "phone_change", "Phone Number Change"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        related_name="contact_verifications",
    )

    contact_type = models.CharField(
        max_length=10,
        choices=ContactType.choices,
    )

    purpose = models.CharField(
        max_length=30,
        choices=Purpose.choices,
    )

    target_value = models.CharField(max_length=254)

    code_hash = models.CharField(max_length=255)

    expires_at = models.DateTimeField()

    attempts = models.PositiveSmallIntegerField(default=0)

    verified_at = models.DateTimeField(null=True, blank=True)

    consumed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    
    class Meta:
        db_table = "accounts_contact_verification"
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["user", "purpose", "created_at"],
                name="acct_ver_user_purpose_idx",
            ),
            models.Index(
                fields=["expires_at"],
                name="acct_ver_expires_idx",
            ),
        ]

        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        contact_type="email",
                        purpose="email_verification",
                    )
                    | models.Q(
                        contact_type="phone",
                        purpose__in=[
                            "phone_verification",
                            "phone_change",
                        ],
                    )
                ),
                name="acct_ver_valid_contact_purpose",
            ),
        ]


    def __str__(self):
        return f"{self.contact_type} verification for {self.user_id}"
