

from django.urls import path
from . import views  
from django.contrib.auth import views as auth_views

urlpatterns = [
    
    path('upload/', views.upload_patient_file, name='upload_patient'),
    path('', views.patient_list, name='patient_list'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('patient/<int:pk>/', views.patient_detail, name='patient_detail'),
    path('download/<uuid:unique_id>/', views.download_gate, name='secure_download'),
    path('patient/<int:pk>/update/', views.update_patient, name='update_patient'),
    path('patient/<int:pk>/delete/', views.delete_patient, name='delete_patient'),
    path('send-sms/', views.send_manual_sms, name='send_manual_sms'),
]