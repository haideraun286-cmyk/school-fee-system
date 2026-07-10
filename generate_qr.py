import os
import django
import qrcode

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schoolsystem.settings')
django.setup()

from students.models import Student

os.makedirs('qr_codes', exist_ok=True)

students = Student.objects.all()

for student in students:
    img = qrcode.make(student.student_id)
    img.save(f'qr_codes/{student.student_id}.png')
    print(f'QR generated for {student.name}')

print('All QR codes generated!')