from django.contrib import admin
from .models import Patient

# روش ساده (فقط رجیستر کن)
# admin.site.register(Patient) <--- این خیلی ساده‌ست، پایینی رو بزن که باکلاس باشه

# روش حرفه‌ای (با ستون‌بندی و سرچ)
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'national_code', 'uploaded_at', 'file_link') # ستون‌هایی که نشون میده
    search_fields = ('name', 'national_code') # باکس سرچ اضافه می‌کنه
    list_filter = ('uploaded_at',) # فیلتر تاریخ بغل صفحه میاره
    
    # این تابع برای اینه که لینک فایل رو تو لیست نشون بده (خیلی کاربردیه)
    def file_link(self, obj):
        if obj.file:
            return "دانلود فایل"
        return "-"
    file_link.short_description = "پرونده"