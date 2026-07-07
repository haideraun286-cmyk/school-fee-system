from django.shortcuts import render
from django.http import JsonResponse
from .models import Student

def gate(request):
    return render(request, 'students/gate.html')

def scan_student(request, student_id):
    try:
        student = Student.objects.get(student_id=student_id)
        data = {
            'name': student.name,
            'class_name': student.class_name,
            'fee_status': 'Cleared',  # hardcoded for now, we'll make this dynamic later
        }
        return JsonResponse(data)
    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)