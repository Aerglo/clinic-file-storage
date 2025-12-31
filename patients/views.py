import time
import requests
from django.shortcuts import render, redirect, get_object_or_404
from .forms import UploadForm, ManualSMSForm
from django.db.models import Q 
from .models import Patient
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from django.contrib import messages   
from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.views.decorators.cache import never_cache

# --- Helper Function: ترجمه وضعیت دلیوری (کدهای جدید) ---
def get_delivery_status_message(state_code):
    status_messages = {
        1: "رسیده",
        2: "نرسیده به گوشی",
        3: "رسیده به مخابرات",
        4: "نرسیده به مخابرات",
        5: "رسیده به اپراتور",
        6: "ناموفق",
        7: "لیست سیاه",
        8: "نامشخص"
    }
    return status_messages.get(state_code, f"وضعیت نامشخص (کد: {state_code})")

# --- SMS Function: منطق جدید دو مرحله‌ای ---
def send_sms_with_sms_ir(phone_number, text_message):
    try:
        # اصلاح فرمت شماره موبایل
        phone = str(phone_number).strip().replace(" ", "")
        if not phone.startswith('0'):
            phone = f"0{phone}"

        # ---------------------------------------------------------
        # مرحله اول: ارسال درخواست و دریافت شناسه پیام (MessageId)
        # ---------------------------------------------------------
        
        # فرض بر این است که BASE_URL شما "https://api.sms.ir/v1/" است
        url_send = f"{settings.SMS_BASE_URL}send"
        
        params = {
            "username": settings.SMS_USERNAME,
            "password": settings.SMS_API_KEY,  # طبق گفته شما پسورد همان API KEY است
            "line": settings.SMS_LINE_NUMBER,
            "mobile": phone,
            "text": text_message
        }

        # ارسال درخواست اولیه (GET)
        response = requests.get(url_send, params=params)
        
        if response.status_code != 200:
            return False, f"خطای HTTP در مرحله اول: {response.status_code}", -1

        json_data = response.json()
        
        # اگر استاتوس 1 نباشد یعنی درخواست اولیه هم فیل شده
        if json_data.get('status') != 1:
            return False, json_data.get('message', 'خطا در ارسال اولیه'), -1

        # دریافت messageId از پاسخ
        message_id = json_data.get('data', {}).get('messageId')
        
        if not message_id:
            return False, "شناسه پیام (messageId) دریافت نشد", -1

        # ---------------------------------------------------------
        # مرحله دوم: وقفه (Delay)
        # ---------------------------------------------------------
        time.sleep(2)

        # ---------------------------------------------------------
        # مرحله سوم: استعلام وضعیت دلیوری با MessageId
        # ---------------------------------------------------------
        url_check = f"{settings.SMS_BASE_URL}send/{message_id}"
        
        headers = {
            "x-api-key": settings.SMS_API_KEY,
            "Accept": "application/json"
        }

        response_check = requests.get(url_check, headers=headers)
        
        if response_check.status_code != 200:
            # اگر پیامک ارسال شده ولی استعلام خطا داد، موفق در نظر می‌گیریم (با هشدار)
            return True, "پیام ارسال شد اما استعلام وضعیت نهایی خطا داشت.", 1

        json_check = response_check.json()
        delivery_data = json_check.get('data', {})
        
        # دریافت وضعیت دلیوری
        delivery_state = delivery_data.get('deliveryState')
        status_msg = get_delivery_status_message(delivery_state)

        # موفقیت: رسیده (1)، رسیده به مخابرات (3)، رسیده به اپراتور (5)
        # شکست: لیست سیاه (7) و بقیه موارد
        is_success = True if delivery_state in [1, 3, 5] else False
        
        return is_success, status_msg, delivery_state

    except Exception as e:
        return False, f"خطای سیستمی: {str(e)}", -1

# --- Views ---

@login_required
def upload_patient_file(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            new_patient = form.save()
            full_link = request.build_absolute_uri(reverse('secure_download', args=[new_patient.unique_id]))
            if new_patient.phone_number:
                msg = f"بیمار گرامی {new_patient.name}،\nنقشه مغزی شما آماده است.\nلینک دریافت:\n{full_link}\nOFF11"
                
                is_sent, sms_status_msg, s_code = send_sms_with_sms_ir(new_patient.phone_number, msg)
                
                if is_sent:
                    messages.success(request, f'✅ پرونده ذخیره و پیامک برای {new_patient.name} ارسال شد.')
                elif s_code == 7:  # کد 7 = لیست سیاه
                    messages.warning(request, f'⚠️ پرونده ذخیره شد اما شماره در لیست سیاه مخابرات است.')
                else:
                    messages.warning(request, f'⚠️ پرونده ذخیره شد اما پیامک ارسال نشد: {sms_status_msg}')
            else:
                messages.success(request, '✅ پرونده با موفقیت ذخیره شد (بدون شماره موبایل).')
            return redirect('patient_detail', pk=new_patient.pk)
    else:
        form = UploadForm()
    return render(request, 'upload.html', {'form': form})

@login_required
def patient_list(request):
    query = request.GET.get('q') 
    if query:
        patients = Patient.objects.filter(
            Q(name__icontains=query) | Q(national_code__icontains=query) | Q(phone_number__icontains=query) 
        ).order_by('-uploaded_at')
    else:
        patients = Patient.objects.all().order_by('-uploaded_at')
    return render(request, 'patient_list.html', {'patients': patients})

@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    full_link = request.build_absolute_uri(reverse('secure_download', args=[patient.unique_id]))
    return render(request, 'patient_detail.html', {'patient': patient, 'full_link': full_link})

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

@never_cache   
def download_gate(request, unique_id):
    patient = get_object_or_404(Patient, unique_id=unique_id)
    if timezone.now() > patient.created_at + timedelta(days=30):
        return render(request, 'gate.html', {'error_msg': '⌛ مهلت دسترسی به این پرونده تمام شده است.'})
    user_ip = get_client_ip(request)
    cache_key = f"block_attempt_{unique_id}_{user_ip}"
    failed_attempts = cache.get(cache_key, 0)
    if failed_attempts >= 5:
        return render(request, 'gate.html', {'error_msg': '⛔ تلاش بیش از حد. ۱ ساعت دیگر تلاش کنید.'})
    error_msg = None
    if request.method == 'POST':
        if request.POST.get('national_code') == patient.national_code:
            response = FileResponse(patient.file.open('rb'))
            response['Content-Disposition'] = 'inline' 
            return response
        else:
            cache.set(cache_key, failed_attempts + 1, 3600)
            error_msg = '⛔ کد ملی اشتباه است!'
    return render(request, 'gate.html', {'error_msg': error_msg})

@login_required
def update_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = UploadForm(instance=patient)
    return render(request, 'upload.html', {'form': form, 'title': '✏️ ویرایش پرونده'})

@login_required
def delete_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        patient.delete()
        return redirect('patient_list')
    return render(request, 'confirm_delete.html', {'patient': patient})

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
                messages.success(request, f'✅ پیامک به {phone} ارسال شد.')
            elif s_code == 7: # کد 7 = لیست سیاه
                messages.error(request, f'⛔ شماره در لیست سیاه مخابرات است.')
            else:
                messages.error(request, f'⛔ خطا: {sms_status_msg}')
            return redirect('send_manual_sms') 
    return render(request, 'manual_sms.html', {'form': ManualSMSForm(), 'patients': patients})