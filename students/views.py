from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from functools import wraps
from datetime import datetime
import os
import io
import zipfile
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from .models import Student, Fee, Attendance, FeeRecord, UserProfile
from .sms_service import send_sms
from generate_ids import make_barcode, generate_card


def is_admin_user(user):
    return user.is_authenticated and (
        user.is_superuser or 
        user.is_staff or 
        user.groups.filter(name='Admin').exists()
    )

def is_cashier_user(user):
    return user.is_authenticated and (
        is_admin_user(user) or 
        user.groups.filter(name='Cashier').exists() or 
        user.username == 'cashier'
    )

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/students/login/?next={request.path}")
        if hasattr(request.user, 'profile') and request.user.profile.must_change_password:
            return redirect('change_password')
        if not is_admin_user(request.user):
            return render(request, 'students/login.html', {
                'message': 'Access Denied: Admin privileges required.',
                'alert_type': 'error'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

def cashier_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/students/login/?next={request.path}")
        if hasattr(request.user, 'profile') and request.user.profile.must_change_password:
            return redirect('change_password')
        if not is_cashier_user(request.user):
            return render(request, 'students/login.html', {
                'message': 'Access Denied: Cashier or Admin account required.',
                'alert_type': 'error'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return wrapper

def ensure_default_accounts():
    cashier_group, _ = Group.objects.get_or_create(name='Cashier')
    admin_group, _ = Group.objects.get_or_create(name='Admin')
    
    cashier_user, created = User.objects.get_or_create(
        username='cashier',
        defaults={'is_staff': False, 'is_superuser': False}
    )
    if created:
        cashier_user.set_password('AlHaider#Cashier2026!')
        cashier_user.save()
        cashier_user.groups.add(cashier_group)
        UserProfile.objects.get_or_create(user=cashier_user, defaults={'must_change_password': False})
    else:
        if not cashier_user.groups.filter(name='Cashier').exists():
            cashier_user.groups.add(cashier_group)
        UserProfile.objects.get_or_create(user=cashier_user, defaults={'must_change_password': False})

    for u in User.objects.filter(is_superuser=True):
        UserProfile.objects.get_or_create(user=u, defaults={'must_change_password': False})

def login_view(request):
    ensure_default_accounts()
    message = None
    alert_type = 'error'
    next_url = request.GET.get('next') or request.POST.get('next') or ''

    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.must_change_password:
            return redirect('change_password')
        if next_url:
            return redirect(next_url)
        return redirect('admin_panel' if is_admin_user(request.user) else 'cashier')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            profile, _ = UserProfile.objects.get_or_create(user=user)
            if profile.must_change_password:
                return redirect('change_password')
            if next_url:
                return redirect(next_url)
            if is_admin_user(user):
                return redirect('admin_panel')
            else:
                return redirect('cashier')
        else:
            message = 'Invalid username or password.'

    return render(request, 'students/login.html', {
        'message': message,
        'alert_type': alert_type,
        'next_url': next_url
    })

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def change_password_view(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    is_forced = profile.must_change_password
    message = None
    alert_type = 'error'

    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not is_forced and not request.user.check_password(old_password):
            message = 'Incorrect current password.'
        elif new_password != confirm_password:
            message = 'New passwords do not match.'
        elif len(new_password) < 8:
            message = 'Password must be at least 8 characters long.'
        else:
            request.user.set_password(new_password)
            request.user.save()
            profile.must_change_password = False
            profile.save()
            update_session_auth_hash(request, request.user)
            
            if is_admin_user(request.user):
                return redirect('admin_panel')
            else:
                return redirect('cashier')

    return render(request, 'students/change_password.html', {
        'is_forced': is_forced,
        'message': message,
        'alert_type': alert_type
    })



def gate(request):
    today = timezone.now().date()
    total_students = Student.objects.count()
    checked_in_today = Attendance.objects.filter(date=today, status='Present').values('student').distinct().count()
    return render(request, 'students/gate.html', {
        'total_students': total_students,
        'checked_in_today': checked_in_today,
    })

def gate_stats_api(request):
    today = timezone.now().date()
    total_students = Student.objects.count()
    checked_in_today = Attendance.objects.filter(date=today, status='Present').values('student').distinct().count()
    return JsonResponse({
        'total_students': total_students,
        'checked_in_today': checked_in_today,
    })

def scan_student(request, student_id):
    run_monthly_fee_reset()
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

        total_students = Student.objects.count()
        checked_in_today = Attendance.objects.filter(date=today, status='Present').values('student').distinct().count()

        data = {
            'name': student.name,
            'class_name': student.class_name,
            'fee_status': fee.status,
            'fee_amount_due': str(fee.amount_due),
            'due_date': str(fee.due_date),
            'deferred_until': str(fee.deffered_date) if fee.deffered_date else None,
            'photo_url': student.photo.url if student.photo else None,
            'total_students': total_students,
            'checked_in_today': checked_in_today,
        }
        return JsonResponse(data)

    except Student.DoesNotExist:
        return JsonResponse({'error': 'Student not found'}, status=404)
    except Fee.DoesNotExist:
        return JsonResponse({'error': 'No fee record found'}, status=404)
    
@cashier_required
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
    
@cashier_required
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

@admin_required
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

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@admin_required
@require_POST
def reset_fees(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    students = Student.objects.all()
    updated = 0
    
    for student in students:
        monthly_fee = settings.FEE_STRUCTURE.get(student.class_name, 3200)
        
        try:
            fee = Fee.objects.get(student=student)
            
            if fee.status == 'Unpaid':
               
                fee.amount_due += monthly_fee
            elif fee.status == 'Deferred':
                
                fee.amount_due += monthly_fee
            else:
                
                fee.amount_due = monthly_fee
                fee.status = 'Unpaid'
            
            fee.due_date = timezone.now().date().replace(day=5)
            fee.deffered_date = None
            fee.save()
            
        except Fee.DoesNotExist:
            
            Fee.objects.create(
                student=student,
                amount_due=monthly_fee,
                due_date=timezone.now().date().replace(day=5),
                status='Unpaid'
            )
        
        updated += 1
    
    return JsonResponse({'success': True, 'message': f'Fee reset for {updated} students'})

@admin_required
@require_POST
def generate_id_cards(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        students = list(Student.objects.all())
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for student in students:
                barcode_path = make_barcode(student.student_id)
                card_path = generate_card(student)
                
                if card_path and os.path.exists(card_path):
                    zip_file.write(
                        card_path,
                        f'{student.student_id}_{student.name}.png'
                    )
        
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="id_cards.zip"'
        return response
        
    except Exception as e:
        import traceback
        return JsonResponse({'success': False, 'message': str(e), 'trace': traceback.format_exc()})

@admin_required
def generate_single_id_card(request, student_id=None):
    if not student_id:
        student_id = request.POST.get('student_id') or request.GET.get('student_id')
    
    if not student_id:
        return JsonResponse({'error': 'Student ID is required'}, status=400)
    
    student_id = str(student_id).strip()

    if request.GET.get('check') == '1':
        exists = Student.objects.filter(student_id=student_id).exists()
        if exists:
            return JsonResponse({'exists': True})
        else:
            return JsonResponse({'exists': False}, status=404)
        
    try:
        student = Student.objects.get(student_id=student_id)
        card_path = generate_card(student)
        if card_path and os.path.exists(card_path):
            with open(card_path, 'rb') as f:
                content = f.read()
            response = HttpResponse(content, content_type='image/png')
            response['Content-Disposition'] = f'attachment; filename="{student.student_id}_{student.name}_id_card.png"'
            return response
        else:
            return JsonResponse({'error': 'Failed to generate card image'}, status=500)
    except Student.DoesNotExist:
        return JsonResponse({'error': f'Student with ID "{student_id}" does not exist.'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@admin_required
def assign_photos_view(request):
    message = None
    results = []
    
    if request.method == 'POST' and request.FILES.get('photo_zip'):
        # 1. Read the file into memory as bytes
        uploaded_file = request.FILES['photo_zip']
        file_bytes = io.BytesIO(uploaded_file.read())
        
        matched = 0
        not_found = 0
        
        try:
            # 2. Open the byte stream with ZipFile
            with zipfile.ZipFile(file_bytes, 'r') as z:
                for filename in z.namelist():
                    # 3. Skip system folders and hidden files (e.g., __MACOSX, .DS_Store)
                    if '__MACOSX' in filename or filename.startswith('.') or filename.endswith('/'):
                        continue
                        
                    name_without_ext = os.path.splitext(os.path.basename(filename))[0]
                    
                    if not name_without_ext:
                        continue
                    
                    try:
                        student = Student.objects.get(student_id=name_without_ext)
                        img_data = z.read(filename)
                        
                        ext = os.path.splitext(filename)[1]
                        student.photo.save(
                            f'{student.student_id}{ext}',
                            ContentFile(img_data),
                            save=True
                        )
                        results.append(f" {student.name} ({student.student_id})")
                        matched += 1
                        
                    except Student.DoesNotExist:
                        results.append(f" No student matches ID: {name_without_ext}")
                        not_found += 1
                        
            message = f'{matched} photos assigned, {not_found} not matched'
            
        except zipfile.BadZipFile:
            message = "Error: The uploaded file is corrupted or is not a valid ZIP archive."
            
    return render(request, 'students/assign_photos.html', {
        'message': message,
        'results': results
    })

@admin_required
def admin_panel(request):
    from django.db.models import Q
    message = None
    alert_type = 'success'
    
    # Handle Single Student Creation & Card Generation
    if request.method == 'POST' and request.POST.get('action') in ['add_student', 'add_and_generate_id']:
        action = request.POST.get('action')
        student_id = request.POST.get('student_id', '').strip()
        name = request.POST.get('name', '').strip()
        father_name = request.POST.get('father_name', '').strip()
        class_name = request.POST.get('class_name', '').strip()
        section = request.POST.get('section', '').strip()
        phone = request.POST.get('phone', '').strip()
        parent_phone = request.POST.get('parent_phone', '').strip()
        date_of_birth = request.POST.get('date_of_birth') or None
        address = request.POST.get('address', '').strip()
        fee_amount = request.POST.get('fee_amount', 0)
        due_date = request.POST.get('due_date') or timezone.now().date()
        photo = request.FILES.get('photo')

        student = Student.objects.filter(student_id=student_id).first()
        if not student:
            student = Student.objects.create(
                student_id=student_id,
                name=name,
                father_name=father_name,
                class_name=class_name,
                section=section,
                phone=phone,
                parent_phone=parent_phone,
                date_of_birth=date_of_birth,
                address=address,
                photo=photo
            )
            Fee.objects.create(
                student=student,
                amount_due=fee_amount,
                due_date=due_date,
                status='Unpaid'
            )
            message = f"Student '{name}' ({student_id}) created successfully!"
            alert_type = 'success'
        else:
            if action == 'add_student':
                message = f"Error: Student ID '{student_id}' already exists."
                alert_type = 'error'

        if action == 'add_and_generate_id' and student:
            card_path = generate_card(student)
            if card_path and os.path.exists(card_path):
                with open(card_path, 'rb') as f:
                    content = f.read()
                response = HttpResponse(content, content_type='image/png')
                response['Content-Disposition'] = f'attachment; filename="{student.student_id}_{student.name}_id_card.png"'
                return response

    # Handle Delete Student
    elif request.method == 'POST' and request.POST.get('action') == 'delete_student':
        delete_id = request.POST.get('delete_id')
        try:
            st = Student.objects.get(student_id=delete_id)
            st.delete()
            message = f"Student '{delete_id}' deleted successfully."
            alert_type = 'success'
        except Student.DoesNotExist:
            message = "Student not found."
            alert_type = 'error'

    # Search & Listing
    query = request.GET.get('q', '').strip()
    if query:
        students = Student.objects.filter(
            Q(name__icontains=query) | 
            Q(student_id__icontains=query) |
            Q(class_name__icontains=query)
        ).order_by('-id')
    else:
        students = Student.objects.all().order_by('-id')[:50]

    total_count = Student.objects.count()

    return render(request, 'students/admin_panel.html', {
        'students': students,
        'query': query,
        'total_count': total_count,
        'message': message,
        'alert_type': alert_type
    })    

from django.conf import settings

def run_monthly_fee_reset():
    from datetime import date
    from django.core.cache import cache
    
    today = date.today()
    if today.day != 5:
        return
    
    cache_key = f'fee_reset_{today.year}_{today.month}'
    if cache.get(cache_key):
        return
    
    students = Student.objects.all()
    
    for student in students:
        monthly_fee = settings.FEE_STRUCTURE.get(student.class_name, 3200)
        
        # Get previous month's unpaid amount
        prev_month = today.month - 1 if today.month > 1 else 12
        prev_year = today.year if today.month > 1 else today.year - 1
        
        carried_amount = 0
        try:
            prev_record = FeeRecord.objects.get(
                student=student,
                month=prev_month,
                year=prev_year
            )
            if prev_record.status in ['Unpaid', 'Deferred']:
                carried_amount = prev_record.total_due
        except FeeRecord.DoesNotExist:
            pass
        
        # Create this month's record
        FeeRecord.objects.get_or_create(
            student=student,
            month=today.month,
            year=today.year,
            defaults={
                'amount_due': monthly_fee,
                'amount_carried': carried_amount,
                'status': 'Unpaid'
            }
        )
    
    cache.set(cache_key, True, 60*60*24*2)
    print(f"Monthly fee reset done: {today.month}/{today.year}")