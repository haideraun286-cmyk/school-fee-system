from django.contrib import admin
from django import forms
from .models import Student,Fee,Attendance,FeeRecord

admin.site.register(Student)
admin.site.register(Fee)
admin.site.register(Attendance)
admin.site.register(FeeRecord)

class StudentAdminForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'type': 'date',
                'min': '1990-01-01',
                'max': '2020-12-31',
            }
        ),
        required=False
    )
    
    class Meta:
        model = Student
        fields = '__all__'

class StudentAdmin(admin.ModelAdmin):
    form = StudentAdminForm
