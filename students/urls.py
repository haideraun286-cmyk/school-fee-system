from django.urls import path
from . import views
urlpatterns = [
    path('', views.gate, name='gate'),
    path('scan/<str:student_id>/', views.scan_student, name='scan_student'),
    path('cashier/', views.cashier, name='cashier'),
    path('attendance/<str:student_id>/', views.mark_attendance, name='mark_attendance'),
    path('attendance/', views.attendance_report, name='attendance_report'),
    
] 
