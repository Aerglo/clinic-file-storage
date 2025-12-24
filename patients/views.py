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
        115: "شماره موبایل(ها) در لیست سیاه سامانه می‌باشند",
        116: "نام یک یا چند پارامتر مقداردهی نشده‌است.",
        117: "متن ارسال شده مورد تایید نمی‌باشد",
        118: "تعداد پیام ها بیشتر از حد مجاز میباشد",
        119: "به منظور استفاده از قالب‌ شخصی سازی شده پلن خود را ارتقا دهید",
        123: "خط ارسال‌کننده نیاز به فعال‌سازی دارد."
    }
    return status_messages.get(status_code, f"خطای ناشناخته (کد: {status_code})")

# --- SMS Function: بهینه شده برای جلوگیری از ارور 400 ---
def send_sms_with_sms_ir(phone_number, text_message):
    try:
        url = f"{settings.SMS_BASE_URL}send/bulk"
        
        headers = {
            "x-api-key": "1Y7Cew52CazJ4SsuIiE3LZaYxofiRZTMconkkUkATpgUbMtM",  
            "Accept": "application/json"
        }
        
        # پاکسازی شماره موبایل
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
        
        # بررسی وضعیت پاسخ HTTP
        if response.status_code == 200:
            json_data = response.json()
            status_code = json_data.get('status')
            status_msg = get_sms_status_message(status_code)
            
            if status_code == 1:
                return True, status_msg
            else:
                return False, status_msg
        else:
            # در صورت ارور 400 یا سایر خطاها، متن پاسخ سرور را برمی‌گردانیم
            return False, f"خطای {response.status_code}: {response.text[:100]}"
            
    except Exception as e:
        return False, f"خطای ارتباطی: {str(e)}"

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
                
                is_sent, sms_status_msg = send_sms_with_sms_ir(new_patient.phone_number, msg)
                
                if is_sent:
                    messages.success(request, f'✅ پرونده ذخیره و پیامک برای {new_patient.name} ارسال شد.')
                else:
                    messages.warning(request, f'⚠️ پرونده ذخیره شد اما پیامک ارسال نشد. علت: {sms_status_msg}')
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
            Q(name__icontains=query) | 
            Q(national_code__icontains=query) |
            Q(phone_number__icontains=query) 
        ).order_by('-uploaded_at')
    else:
        patients = Patient.objects.all().order_by('-uploaded_at')
    
    return render(request, 'patient_list.html', {'patients': patients})

@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    full_link = request.build_absolute_uri(reverse('secure_download', args=[patient.unique_id]))
    
    return render(request, 'patient_detail.html', {
        'patient': patient, 
        'full_link': full_link
    })

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@never_cache  
def download_gate(request, unique_id):
    patient = get_object_or_404(Patient, unique_id=unique_id)
    
    if timezone.now() > patient.created_at + timedelta(days=30):
        return render(request, 'gate.html', {'error_msg': '⌛ مهلت دسترسی به این پرونده تمام شده است.'})

    user_ip = get_client_ip(request)
    cache_key = f"block_attempt_{unique_id}_{user_ip}"
    failed_attempts = cache.get(cache_key, 0)
    
    if failed_attempts >= 5:
        return render(request, 'gate.html', {'error_msg': '⛔ دسترسی شما به دلیل تلاش بیش از حد مسدود شد. لطفاً ۱ ساعت دیگر تلاش کنید.'})

    error_msg = None

    if request.method == 'POST':
        input_code = request.POST.get('national_code')
        
        if input_code == patient.national_code:
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
            is_sent, sms_status_msg = send_sms_with_sms_ir(phone, msg)
            if is_sent:
                messages.success(request, f'✅ پیامک با موفقیت به {phone} ارسال شد.')
                return redirect('send_manual_sms') 
            else:
                messages.error(request, f'⛔ ارسال پیامک با خطا مواجه شد: {sms_status_msg}')
    else:
        form = ManualSMSForm()

    return render(request, 'manual_sms.html', {
        'form': form,
        'patients': patients, 
        'title': '📩 ارسال پیامک تکی'
    })