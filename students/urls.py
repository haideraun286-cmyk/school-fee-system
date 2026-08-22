from django.urls import path
from . import views

urlpatterns = [
    path('', views.gate, name='gate'),
    path('scan/<str:student_id>/', views.scan_student, name='scan_student'),
    path('cashier/', views.cashier, name='cashier'),
    path('attendance/<str:student_id>/', views.mark_attendance, name='mark_attendance'),
    path('attendance/', views.attendance_report, name='attendance_report'),
    path('upload/', views.upload_students, name='upload_students'),
    path('reset-fees/', views.reset_fees, name='reset_fees'),
    path('assign-photos/', views.assign_photos_view, name='assign_photos'),
    path('generate-ids/', views.generate_id_cards, name='generate_id_cards'),
    path('generate-id/', views.generate_single_id_card, name='generate_single_id_card_post'),
    path('generate-id/<str:student_id>/', views.generate_single_id_card, name='generate_single_id_card'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
] 
