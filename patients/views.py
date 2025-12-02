

from django.shortcuts import render, redirect
from .forms import UploadForm 
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q 
from .models import Patient
from django.contrib.auth.decorators import login_required
from django.urls import reverse

@login_required
def upload_patient_file(request):
    if request.method == 'POST':
        
        form = UploadForm(request.POST, request.FILES)
        if form.is_valid():
            new_patient = form.save()
            
            # حالا ریدایرکت می‌کنیم به صفحه جزئیات (با استفاده از ID بیمار جدید)
            return redirect('patient_detail', pk=new_patient.pk)
    else:
        
        form = UploadForm()

    return render(request, 'upload.html', {'form': form})

@login_required
def patient_list(request):
    query = request.GET.get('q') 
    if query:
        
        patients = Patient.objects.filter(
            Q(name__icontains=query) | Q(national_code__icontains=query)
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