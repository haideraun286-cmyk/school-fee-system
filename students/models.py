from django.db import models

class Student(models.Model):
    student_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    father_name = models.CharField(max_length=100)
    class_name = models.CharField(max_length=20)
    section = models.CharField(max_length=5)
    phone = models.CharField(max_length=15)
    photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.student_id}"
    
class Fee(models.Model):
    STATUS_CHOICES = [
    ('Paid', 'Paid'),
    ('Unpaid', 'Unpaid'),
    ('Deferred', 'Deferred'),
]
    student=models.ForeignKey(Student,on_delete=models.CASCADE)
    amount_due=models.DecimalField(max_digits=10,decimal_places=2)
    due_date=models.DateField()
    status=models.CharField(max_length=15,choices=STATUS_CHOICES)
    deffered_date=models.DateField(null=True,blank=True)
    paid=models.DateField(null=True,blank=True)
    