from django.shortcuts import render
from django.http import JsonResponse
from .models import Student
from .models import Fee

def gate(request):
    return render(request, 'students/gate.html')

def scan_student(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
        fee = Fee.objects.get(student=student)

        data = {
            'name': student.name,
            'class_name': student.class_name,
            'fee_status': fee.status,
            'fee_amount_due':fee.amount_due,
            'due_date':str(fee.due_date)

        }
        return JsonResponse(data)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Fee.DoesNotExist:
        return JsonResponse({'error: Fee record not found'},status=404)
    
def cashier(request):
    student = None
    fee = None
    message = None
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        try:
            student = Student.objects.get(student_id=student_id)
            fee = Fee.objects.get(student=student)
            fee.status = request.POST.get('status')
            fee.deferred_date = request.POST.get('deferred_date') or None
            fee.save()
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