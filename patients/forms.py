from django import forms
from .models import Patient

class UploadForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['name', 'national_code', 'file']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'نام کامل بیمار را بنویسید'
            }),
            'national_code': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'مثلاً: 0012345678'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
        labels = {
            'name': 'نام و نام خانوادگی',
            'national_code': 'کد ملی (جهت رمز عبور)',
            'file': 'فایل نقشه مغزی (تصویر یا PDF)',
        }
        error_messages = {
            'national_code': {
                'unique': '⛔ این کد ملی قبلاً در سیستم ثبت شده است.',
            }
        }