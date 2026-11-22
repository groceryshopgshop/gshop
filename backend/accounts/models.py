
import uuid

from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, phone_number, full_name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email address is required.")

        if not phone_number:
            raise ValueError("Phone number is required.")

        if not full_name:
            raise ValueError("Full name is required.")

        email = self.normalize_email(email).lower()

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

    email = models.EmailField(max_length=254, unique=True)

    phone_number = models.CharField(max_length=20, unique=True)

    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["phone_number", "full_name"]

    class Meta:
        db_table = "accounts_user"
        ordering = ["-date_joined"]

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()

        if self.pk:
            old_user = type(self).objects.filter(pk=self.pk).only("email").first()

            if old_user and old_user.email != self.email:
                raise ValueError("Email address cannot be changed after registration.")

        super().save(*args, **kwargs)

    def __str__(self):
        return self.email
