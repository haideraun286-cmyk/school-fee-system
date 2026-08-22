import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schoolsystem.settings')
django.setup()

from students.models import Student
from django.core.files import File

PHOTOS_DIR = os.path.join(os.path.dirname(__file__), 'bulk_photos')

students = Student.objects.all()
matched = 0
not_found = 0

for student in students:
    for ext in ['jpg', 'jpeg', 'png', 'JPG', 'JPEG', 'PNG']:
        photo_path = os.path.join(PHOTOS_DIR, f'{student.student_id}.{ext}')
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as f:
                student.photo.save(
                    f'{student.student_id}.{ext}',
                    File(f),
                    save=True
                )
            print(f"Photo assigned: {student.name}")
            matched += 1
            break
    else:
        print(f"No photo found: {student.name} ({student.student_id})")
        not_found += 1

print(f"\nDone — {matched} matched, {not_found} not found")