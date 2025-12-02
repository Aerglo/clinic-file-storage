import uuid
from django.db import models

# Create your models here.

class Patient(models.Model):
    name = models.CharField(max_length=100)
    national_code = models.CharField(max_length=10, unique=True)
    file = models.FileField(upload_to='qeeg_files/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    def __str__(self):
        return self.name