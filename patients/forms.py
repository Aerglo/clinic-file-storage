from django import forms
from .models import Patient

class UploadForm(forms.ModelForm):
    class Meta:
        model = Patient
        # ترتیب فیلدها مهمه: اول مشخصات، بعد شماره، آخر فایل
        fields = ['name', 'national_code', 'phone_number', 'file']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'نام کامل بیمار را بنویسید'
            }),
            'national_code': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'مثلاً: 0012345678',
                'type': 'tel' # اینم عددی کردم که تو موبایل راحت باشن
            }),
            # >>>> این بخش جدیده <<<<
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'مثلاً: 09123456789',
                'type': 'tel', # نکته طلایی: کیبورد موبایل رو عددی می‌کنه
                'maxlength': '11'
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
        }
        
        labels = {
            'name': 'نام و نام خانوادگی',
            'national_code': 'کد ملی (جهت رمز عبور)',
            'phone_number': 'شماره موبایل (جهت ارسال پیامک)',
            'file': 'فایل نقشه مغزی (تصویر یا PDF)',
        }
        
        error_messages = {
            'national_code': {
                'unique': '⛔ این کد ملی قبلاً در سیستم ثبت شده است.',
            }
        }

# فرم ارسال پیامک دستی
class ManualSMSForm(forms.Form):
    phone_number = forms.CharField(
        label="شماره موبایل گیرنده",
        max_length=11,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '0912...',
            'type': 'tel',
            'list': 'patient-list' # این خط جادویی برای پیشنهاد شماره‌هاست
        })
    )
    message = forms.CharField(
        label="متن پیامک",
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'متن پیام خود را اینجا بنویسید...'
        })
    )