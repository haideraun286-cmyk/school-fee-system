from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from .models import Student
from .models import Fee
from .models import Attendance


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
            Attendance.objects.create(
                student=student,
                status='Present'
            )
            print(f"Sending WhatsApp to {student.parent_phone}")
            print(f"{student.name} has arrived at school.")

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
        
        # WhatsApp notification (hardcoded for now)
        print(f"Sending WhatsApp to {student.parent_phone}")
        print(f"{student.name} has arrived at school.")
        
        return JsonResponse({'success': True, 'message': f'{student.name} marked present'})
    
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    
def attendance_report(request):
    today = timezone.now().date()
    records = Attendance.objects.filter(date=today)
    return render(request, 'students/attendance.html', {
        'records': records,
        'today': today
    })
        
