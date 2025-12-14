

from django.shortcuts import render, redirect
from .forms import UploadForm, ManualSMSForm
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q 
from .models import Patient
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import requests
from django.contrib import messages  # این برای نوتیفیکیشن‌هاست
from django.conf import settings

def send_sms_with_sms_ir(phone_number, text_message):
    try:
        # اطلاعات محرمانه (از کدی که دادی برداشتم)
        url = f"{settings.SMS_BASE_URL}send/bulk"
        
        headers = {
            "X-API-KEY": settings.SMS_API_KEY,  # <--- خواندن از تنظیمات
            "Content-Type": "application/json",
            "Accept": "text/plain"
        }
        
        payload = {
            "lineNumber": settings.SMS_LINE_NUMBER, # <--- خواندن از تنظیمات
            "messageText": text_message,
            "mobiles": [phone_number],
            "sendDateTime": None
        }

        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200 and response.json().get('status') == 1:
            print(f"✅ SMS sent via Line {settings.SMS_LINE_NUMBER}")
            return True
        else:
            print(f"❌ SMS Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return False

@login_required
def upload_patient_file(request):
    if request.method == 'POST':
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            new_patient = form.save()
            
            # --- شروع ماجرای پیامک ---
            
            # الف) ساخت لینک کامل (همراه با https و دامنه سایت)
            # اینجا از اسم 'secure_download' یا هر اسمی که تو urls.py برای اون ویوی گیت گذاشتی استفاده کن
            # اگه اسم ویوی دانلودت چیز دیگه‌س، اینجا عوضش کن
            full_link = request.build_absolute_uri(
                reverse('download_gate', args=[new_patient.unique_id])
            )
            
            # ب) ارسال پیامک (اگر شماره داشت)
            if new_patient.phone_number:
                msg = f"بیمار گرامی {new_patient.name}،\nنقشه مغزی شما آماده است.\nلینک دریافت:\n{full_link}\nOFF11"
                
                is_sent = send_sms_with_sms_ir(new_patient.phone_number, msg)
                
                if is_sent:
                    messages.success(request, f'✅ پرونده ذخیره و پیامک برای {new_patient.name} ارسال شد.')
                else:
                    messages.warning(request, '⚠️ پرونده ذخیره شد اما پیامک ارسال نشد (مشکل پنل).')
            else:
                messages.success(request, '✅ پرونده با موفقیت ذخیره شد (بدون شماره موبایل).')

            # --- پایان ماجرا ---

            return redirect('patient_detail', pk=new_patient.pk)
    else:
        form = UploadForm()

    return render(request, 'upload.html', {'form': form})

# ==========================================
# 3. لیست بیماران (با قابلیت جستجوی شماره)
# ==========================================
@login_required
def patient_list(request):
    query = request.GET.get('q') 
    if query:
        patients = Patient.objects.filter(
            Q(name__icontains=query) | 
            Q(national_code__icontains=query) |
            Q(phone_number__icontains=query) # <--- این خط جدید اضافه شد
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

# views.py

def download_gate(request, unique_id):
    # بیمار رو با اون کد عجیب (UUID) پیدا کن
    patient = get_object_or_404(Patient, unique_id=unique_id)
    
    error_msg = None

    if request.method == 'POST':
        input_code = request.POST.get('national_code')
        
        # چک کردن رمز (کد ملی)
        if input_code == patient.national_code:
            # اگه درست بود، بفرستش سمت فایل اصلی
            return redirect(patient.file.url)
        else:
            error_msg = '⛔ کد ملی اشتباه است!'

    return render(request, 'gate.html', {'error_msg': error_msg})

@login_required
def update_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        # نکته مهم: instance=patient یعنی داریم روی همون قبلی می‌نویسیم
        form = UploadForm(request.POST, request.FILES, instance=patient)
        if form.is_valid():
            form.save()
            # بعد از ویرایش برگرد به صفحه جزئیات همون بیمار
            return redirect('patient_detail', pk=patient.pk)
    else:
        # فرم رو با اطلاعات قبلی پر کن که منشی ببینه
        form = UploadForm(instance=patient)

    # از همون قالب آپلود استفاده می‌کنیم (چون شبیه همن)
    return render(request, 'upload.html', {
        'form': form, 
        'title': '✏️ ویرایش پرونده' # اینو می‌فرستیم که تیتر صفحه عوض شه
    })

# این تابع برای حذف
@login_required
def delete_patient(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    
    if request.method == 'POST':
        # فقط اگه درخواست POST بود (یعنی دکمه رو زد) پاک کن
        patient.delete()
        return redirect('patient_list')
        
    return render(request, 'confirm_delete.html', {'patient': patient})

@login_required
def send_manual_sms(request):
    # لیست بیماران رو می‌گیریم برای پیشنهاد دادن شماره
    patients = Patient.objects.filter(phone_number__isnull=False).values('name', 'phone_number')
    
    if request.method == 'POST':
        form = ManualSMSForm(request.POST)
        if form.is_valid():
            phone = form.cleaned_data['phone_number']
            msg = form.cleaned_data['message']
            
            # استفاده از همون تابع کمکی که قبلا نوشتیم
            is_sent = send_sms_with_sms_ir(phone, msg)
            
            if is_sent:
                messages.success(request, f'✅ پیامک با موفقیت به {phone} ارسال شد.')
                return redirect('send_manual_sms') # رفرش صفحه
            else:
                messages.error(request, '⛔ ارسال پیامک با خطا مواجه شد. اعتبار یا اینترنت را چک کنید.')
    else:
        form = ManualSMSForm()

    return render(request, 'manual_sms.html', {
        'form': form,
        'patients': patients, # اینو می‌فرستیم برای دیتالیست
        'title': '📩 ارسال پیامک تکی'
    })