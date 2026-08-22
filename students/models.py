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
    parent_phone = models.CharField(max_length=15, blank=True, null=True)
    parent_name = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(null=True, blank=True)
    address = models.TextField(null=True, blank=True)

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
    
class Attendance(models.Model):
    STATUS_CHOICES = [
        ('Present', 'Present'),
        ('Absent', 'Absent'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Present')

class FeeRecord(models.Model):
    STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Deferred', 'Deferred'),
    ]
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    month = models.IntegerField()
    year = models.IntegerField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_carried = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='Unpaid')
    deffered_date = models.DateField(null=True, blank=True)
    paid_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['student', 'month', 'year']

    def __str__(self):
        return f"{self.student.name} - {self.month}/{self.year}"
    
    @property
    def total_due(self):
        return self.amount_due + self.amount_carried    

from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    must_change_password = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile for {self.user.username}"