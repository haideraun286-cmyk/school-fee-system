import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'schoolsystem.settings')
django.setup()

from students.models import Student
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

os.makedirs('id_cards', exist_ok=True)

students = Student.objects.all()

for student in students:
    filename = f'id_cards/{student.student_id}.pdf'
    c = canvas.Canvas(filename, pagesize=(8.5*cm, 5.4*cm))
    
    # School name at top
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(4.25*cm, 4.8*cm, "MY SCHOOL NAME")
    
    # Student name
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(4.25*cm, 4.2*cm, student.name)
    
    # Class and section
    c.setFont("Helvetica", 6)
    c.drawCentredString(4.25*cm, 3.7*cm, f"Class: {student.class_name} - {student.section}")
    
    # Student ID
    c.setFont("Helvetica", 6)
    c.drawCentredString(4.25*cm, 3.2*cm, f"ID: {student.student_id}")
    
    # QR code image
    qr_path = f'qr_codes/{student.student_id}.png'
    if os.path.exists(qr_path):
        c.drawImage(qr_path, 3.0*cm, 0.3*cm, 2.5*cm, 2.5*cm)
    
    c.save()
    print(f'ID card generated for {student.name}')

print('All ID cards generated!')