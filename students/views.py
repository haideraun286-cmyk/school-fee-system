from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from .models import Student
from .models import Fee
from .models import Attendance
from .sms_service import send_sms
import openpyxl
from datetime import datetime


def gate(request):
    return render(request, 'students/gate.html')

def scan_student(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
        fee = Fee.objects.get(student=student)
        
        today = timezone.now().date()
        
        # Only mark attendance if not already marked today
        already_marked = Attendance.objects.filter(
            student=student,
            date=today
        ).exists()
        

        if not already_marked:
            Attendance.objects.create(student=student, status='Present')
        
        
        attendance_msg = f"Dear Parent, {student.name} has arrived at Al-Haider Educational World."

        if fee.status == 'Unpaid':

            attendance_msg +=f"Dear Parent, {student.name}'s fee of Rs.{fee.amount_due} is due. Please clear it. - Al-Haider"
        elif fee.status == 'Deferred':
            attendance_msg += f" Fee deferred until {fee.deffered_date}."
        send_sms(student.parent_phone, attendance_msg)

        data = {
            'name': student.name,
            'class_name': student.class_name,
            'fee_status': fee.status,
            'fee_amount_due': str(fee.amount_due),
            'due_date': str(fee.due_date),
            'deferred_until': str(fee.deffered_date) if fee.deffered_date else None,
        }
        return JsonResponse(data)

    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Fee.DoesNotExist:
        return JsonResponse({'error': 'No fee record found'}, status=404)
    
def cashier(request):
    student = None
    fee = None
    message = None

    view_id = request.GET.get('view_id')
    if view_id:
        try:
            student = Student.objects.get(student_id=view_id)
            fee = Fee.objects.get(student=student)
        except Student.DoesNotExist:
            message = 'Student not found'
        except Fee.DoesNotExist:
            message = 'No fee record found'

    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(student_id=student_id)
            fee = Fee.objects.get(student=student)
            print(f"BEFORE: status={fee.status}, deferred={fee.deffered_date}")
            fee.status = request.POST.get('status')
            fee.deffered_date = request.POST.get('deferred_date') or None
            print(f"AFTER: status={fee.status}, deferred={fee.deffered_date}")
            fee.save()
            print("SAVED")
            message = 'Fee status updated successfully'
        except Student.DoesNotExist:
            message = 'Student not found'
        except Fee.DoesNotExist:
            message = 'No fee record found'

    return render(request, 'students/cashier.html', {
        'student': student,
        'fee': fee,
        'message': message
    })

def mark_attendance(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
        
        Attendance.objects.create(
            student=student,
            status='Present'
        )
        
        print(f"Sending WhatsApp to {student.parent_phone}")
        print(f"{student.name} has arrived at school.")
        
        return JsonResponse({'success': True, 'message': f'{student.name} marked present'})
    
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    
def attendance_report(request):
    today = timezone.now().date()
    
    classes = Student.objects.values_list('class_name', flat=True).distinct().order_by('class_name')
    
    class_data = {}
    for class_name in classes:
        records = Attendance.objects.filter(
            date=today,
            student__class_name=class_name
        ).select_related('student')
        
        class_data[class_name] = {
            'records': records,
            'total_present': records.count(),
            'total_students': Student.objects.filter(class_name=class_name).count(),
        }
    
    return render(request, 'students/attendance.html', {
        'class_data': class_data,
        'today': today,
        'classes': classes,
    })
import openpyxl

def upload_students(request):
    message = None
    if request.method == 'POST' and request.FILES.get('excel_file'):
        excel_file = request.FILES['excel_file']
        wb = openpyxl.load_workbook(excel_file)
        ws = wb.active
        
        created = 0
        skipped = 0
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            student_id, name, father_name, class_name, section, phone, parent_phone, address,date_of_birth = row[:9]
            
            if not student_id:
                continue
                
            student, created_now = Student.objects.get_or_create(
                student_id=str(student_id),
                defaults={
                    'name': str(name or ''),
                    'father_name': str(father_name or ''),
                    'class_name': str(class_name or ''),
                    'section': str(section or ''),
                    'phone': str(phone or ''),
                    'parent_phone': str(parent_phone or ''),
                    'address': str(address or ''),
                    'date_of_birth':datetime.strptime(date_of_birth, "%Y-%m-%d").date() if isinstance(date_of_birth, str) else date_of_birth,
                }
            )
            
            if created_now:
                # Create fee record automatically
                Fee.objects.create(
                    student=student,
                    amount_due=0,
                    due_date=timezone.now().date(),
                    status='Unpaid'
                )
                created += 1
            else:
                skipped += 1
        
        message = f'{created} students created, {skipped} already existed'
    
    return render(request, 'students/upload_students.html', {'message': message})
        
