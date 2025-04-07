# loyalty_app/models.py
from django.db import models
from django.contrib.auth.models import User
import uuid


class Shop(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shops')
    name = models.CharField(max_length=255)
    api_key = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    secret_key = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name