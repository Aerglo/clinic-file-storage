from django.contrib import admin
from .models import Patient





@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'national_code', 'uploaded_at', 'file_link') 
    search_fields = ('name', 'national_code') 
    list_filter = ('uploaded_at',) 
    
    
    def file_link(self, obj):
        if obj.file:
            return "دانلود فایل"
        return "-"
    file_link.short_description = "پرونده"