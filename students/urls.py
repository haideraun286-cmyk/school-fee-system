from django.urls import path
from . import views
urlpatterns = [
    path('', views.gate, name='gate'),
    path('scan/<str:student_id>/', views.scan_student, name='scan_student'),
    path('cashier/', views.cashier, name='cashier'),
] 
