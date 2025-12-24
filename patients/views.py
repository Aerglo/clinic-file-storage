from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadForm, ManualSMSForm
from django.db.models import Q 
from .models import Patient
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import requests
from django.contrib import messages   
from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.views.decorators.cache import never_cache

# --- Helper Function: ترجمه کدهای وضعیت SMS.ir ---
def get_sms_status_message(status_code):
    status_messages = {
        0: "درخواست شما با خطا مواجه شده‌است.",
        1: "عملیات با موفقیت انجام شد",
        10: "کلید وب سرویس نامعتبر است",
        11: "کلید وب سرویس غیرفعال است",
        12: "کلید وب سرویس محدود به آی‌پی‌های تعریف شده می‌باشد.",
        13: "حساب کاربری غیرفعال است",
        14: "حساب کاربری در حالت تعلیق قرار دارد",
        15: "به منظور استفاده از وب سرویس پلن خود را ارتقا دهید",
        16: "مقدار ارسالی پارامتر نادرست می‌باشد",
        20: "تعداد درخواست بیشتر از حد مجاز است",
        101: "شماره خط نامعتبر میباشد",
        102: "اعتبار کافی نمیباشد",
        103: "درخواست شما دارای متن (های) خالی است",
        104: "درخواست شما دارای موبایل (های) نادرست است",
        105: "تعداد موبایل ها بیشتر از حد مجاز (100 عدد) میباشد",
        106: "تعداد متن ها بیشتر از حد مجاز (100 عدد) میباشد",
        107: "لیست موبایل ها خالی میباشد",
        108: "لیست متن ها خالی میباشد",
        109: "زمان ارسال نامعتبر میباشد",
        110: "تعداد شماره موبایل ها و تعداد متن ها برابر نیستند",
        111: "با این شناسه ارسالی ثبت نشده است",
        112: "رکوردی برای حذف یافت نشد",
        113: "قالب یافت نشد",
        114: "طول رشته مقدار پارامتر، بیش از حد مجاز (25 کاراکتر) میباشد",
        115: "شماره موبایل در لیست سیاه سامانه می‌باشد 🚫",
        116: "نام یک یا چند پارامتر مقداردهی نشده‌است.",
        117: "متن ارسال شده مورد تایید نمی‌باشد",
        118: "تعداد پیام ها بیشتر از حد مجاز میباشد",
        119: "به منظور استفاده از قالب‌ شخصی سازی شده پلن خود را ارتقا دهید",
        123: "خط ارسال‌کننده نیاز به فعال‌سازی دارد."
    }
    return status_messages.get(status_code, f"خطای ناشناخته (کد: {status_code})")

# --- SMS Function ---
def send_sms_with_sms_ir(phone_number, text_message):
    try:
        url = f"{settings.SMS_BASE_URL}send/bulk"
        
        # استفاده مجدد از settings برای امنیت
        headers = {
            "x-api-key": settings.SMS_API_KEY,  
            "Accept": "application/json"
        }
        
        phone = str(phone_number).strip().replace(" ", "")
        if not phone.startswith('0'):
            phone = f"0{phone}"

        payload = {
            "lineNumber": settings.SMS_LINE_NUMBER, 
            "messageText": text_message,
            "mobiles": [phone],
            "sendDateTime": None 
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            json_data = response.json()
            status_code = json_data.get('status')
            status_msg = get_sms_status_message(status_code)
            
            # خروجی شامل کد و پیام فارسی برای تصمیم‌گیری در View
            if status_code == 1:
                return True, status_msg, status_code
            else:
                return False, status_msg, status_code
        else:
            return False, f"خطای {response.status_code}", -1
            
    except Exception as e:
        return False, f"خطای ارتباطی: {str(e)}", -1

# --- Views ---

@login_required
def upload_patient_file(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            new_patient = form.save()
            
            full_link = request.build_absolute_uri(
                reverse('secure_download', args=[new_patient.unique_id])
            )
            
            if new_patient.phone_number:
                msg = f"بیمار گرامی {new_patient.name}،\nنقشه مغزی شما آماده است.\nلینک دریافت:\n{full_link}\nOFF11"
                
                # دریافت موفقیت، پیام و کد عددی
                is_sent, sms_status_msg, s_code = send_sms_with_sms_ir(new_patient.phone_number, msg)
                
                if is_sent:
                    messages.success(request, f'✅ پرونده ذخیره و پیامک برای {new_patient.name} ارسال شد.')
                elif s_code == 115: # بررسی کد لیست سیاه
                    messages.warning(request, f'⚠️ پرونده ذخیره شد اما پیامک به دلیل "لیست سیاه" ارسال نشد.')
                else:
                    messages.warning(request, f'⚠️ پرونده ذخیره شد اما پیامک با خطا مواجه شد: {sms_status_msg}')
            else:
                messages.success(request, '✅ پرونده با موفقیت ذخیره شد (بدون شماره موبایل).')

            return redirect('patient_detail', pk=new_patient.pk)
    else:
        form = UploadForm()

    return render(request, 'upload.html', {'form': form})

# بقیه توابع (patient_list, patient_detail, download_gate, etc.) تغییری ندارند و همان کد قبلی شما هستند
# جهت کوتاه شدن پاسخ فقط توابع تغییر یافته را آوردم.

@login_required
def send_manual_sms(request):
    patients = Patient.objects.filter(phone_number__isnull=False).values('name', 'phone_number')
    if request.method == 'POST':
        form = ManualSMSForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            msg = form.cleaned_data['message']
            
            is_sent, sms_status_msg, s_code = send_sms_with_sms_ir(phone, msg)
            
            if is_sent:
                messages.success(request, f'✅ پیامک با موفقیت به {phone} ارسال شد.')
            elif s_code == 115:
                messages.error(request, f'⛔ خطا: شماره {phone} در لیست سیاه مخابرات است.')
            else:
                messages.error(request, f'⛔ ارسال پیامک با خطا مواجه شد: {sms_status_msg}')
            
            return redirect('send_manual_sms') 
    else:
        form = ManualSMSForm()

    return render(request, 'manual_sms.html', {
        'form': form,
        'patients': patients, 
        'title': '📩 ارسال پیامک تکی'
    })