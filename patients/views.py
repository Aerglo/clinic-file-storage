

from django.shortcuts import render, redirect
from .forms import UploadForm, ManualSMSForm
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q 
from .models import Patient
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import requests
from django.contrib import messages  
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, FileResponse, Http404
from django.utils import timezone
from datetime import timedelta
from django.core.cache import cache
from django.views.decorators.cache import never_cache

def send_sms_with_sms_ir(phone_number, text_message):
    try:
        
        url = f"{settings.SMS_BASE_URL}send/bulk"
        
        headers = {
            "X-API-KEY": settings.SMS_API_KEY,  
            "Content-Type": "application/json",
            "Accept": "text/plain"
        }
        
        payload = {
            "lineNumber": settings.SMS_LINE_NUMBER, 
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
            
            
            
            
            
            
            full_link = request.build_absolute_uri(
                reverse('secure_download', args=[new_patient.unique_id])
            )
            
            
            if new_patient.phone_number:
                msg = f"بیمار گرامی {new_patient.name}،\nنقشه مغزی شما آماده است.\nلینک دریافت:\n{full_link}\nOFF11"
                
                is_sent = send_sms_with_sms_ir(new_patient.phone_number, msg)
                
                if is_sent:
                    messages.success(request, f'✅ پرونده ذخیره و پیامک برای {new_patient.name} ارسال شد.')
                else:
                    messages.warning(request, '⚠️ پرونده ذخیره شد اما پیامک ارسال نشد (مشکل پنل).')
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

    
    return render(request, 'upload.html', {
        'form': form, 
        'title': '✏️ ویرایش پرونده' 
    })


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
            
            
            is_sent = send_sms_with_sms_ir(phone, msg)
            
            if is_sent:
                messages.success(request, f'✅ پیامک با موفقیت به {phone} ارسال شد.')
                return redirect('send_manual_sms') 
            else:
                messages.error(request, '⛔ ارسال پیامک با خطا مواجه شد. اعتبار یا اینترنت را چک کنید.')
    else:
        form = ManualSMSForm()

    return render(request, 'manual_sms.html', {
        'form': form,
        'patients': patients, 
        'title': '📩 ارسال پیامک تکی'
    })