import time
import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import CustomUser, Mentee, Mentor, HeadofMentorMentee, Activity, Attendance, MentoringSession, ActivityReport, MentorMenteeAssignment
import re
from datetime import datetime, date, timedelta
from django.utils import timezone
from django.db import models  
from django.db.models import F, Q, Count
from django.db.models.functions import TruncMonth, TruncDay
from .forms import ActivityForm
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger  # ADD THIS IMPORT
import csv  # ADD THIS IMPORT FOR EXPORT FUNCTIONALITY
from django.http import HttpResponse  # ADD THIS IMPORT FOR EXPORT FUNCTIONALITY

def signup_view(request):
    """View for user registration - mentees and mentors only"""
    if request.method == 'POST':
        # Get form data with consistent naming
        identification_id = request.POST.get('identification_id', '').strip().upper()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')
        role = request.POST.get('role')
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        gender = request.POST.get('gender')
        
        # Validation
        errors = []
        
        # Check if role is valid (only mentee and mentor can sign up)
        if role not in ['mentee', 'mentor']:
            errors.append("Invalid role. Only mentees and mentors can sign up through this page.")
        
        # Check if passwords match
        if password != confirm_password:
            errors.append("Passwords do not match.")
        
        # Check password length
        if len(password) < 6:
            errors.append("Password must be at least 6 characters long.")
        
        # Check if full name is provided
        if not full_name or not full_name.strip():
            errors.append("Please enter your full name.")
        
        # Check if email is provided and valid
        if not email:
            errors.append("Please enter your email address.")
        elif CustomUser.objects.filter(email=email).exists():
            errors.append("This email address is already registered.")
        
        # Check gender is required only for mentees (not for mentors)
        if role == 'mentee' and not gender:
            errors.append("Please select your gender.")
        # Note: Gender is NOT required for mentors
        
        # Validate ID format based on role
        if role == 'mentee':
            # Updated regex to match mentee ID format
            mentee_id_regex = r'^(B(CS|DA|DB|LH)\d{4}-\d{3}|(IEP|CFAB)\d{4}-\d{3})$'
            if not re.match(mentee_id_regex, identification_id):
                errors.append(
                    "Student ID format is incorrect.\n\n"
                    "For diploma programs: B + Program + Year + Month + Number\n"
                    "Examples: BCS2311-017, BDA2307-123\n\n"
                    "For certificate/English: Program + Year + Month + Number\n"
                    "Examples: IEP2307-001, CFAB2307-001"
                )
            
            # REMOVED: No need to check if mentee exists in the system
            # Mentees can create their own accounts directly
            
        elif role == 'mentor':
            # Validate mentor ID format
            mentor_id_regex = r'^ST(A|B|C|D|GS)\d{3}$'
            if not re.match(mentor_id_regex, identification_id):
                errors.append(
                    "Staff ID format is incorrect.\n\n"
                    "Format: ST + Department Code + 3-digit number\n\n"
                    "Examples:\n"
                    "• STA001 (Accounting Department)\n"
                    "• STB015 (Business Studies Department)\n"
                    "• STC123 (Quantitative Science Department)\n"
                    "• STD045 (Landscape and Horticulture Department)\n"
                    "• STGS008 (General Studies)"
                )
            
            # REMOVED: Mentor can sign up without being pre-created by head
        
        # Check if ID already exists as username
        if CustomUser.objects.filter(username=identification_id).exists():
            errors.append("This ID is already registered. Please login with your existing account.")
        
        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, 'signup.html', {
                'preserved_data': {
                    'role': role,
                    'full_name': full_name,
                    'identification_id': identification_id,
                    'email': email,
                    'gender': gender,
                }
            })
        
        # Create user and role-specific profile
        try:
            # Create the user account
            user = CustomUser.objects.create_user(
                username=identification_id,
                password=password,
                role=role,
                first_name=full_name,
                email=email,
            )
            
            if role == 'mentee':
                # Create new mentee profile directly
                mentee = Mentee.objects.create(
                    user=user,
                    MenteeID=identification_id,
                    MenteeName=full_name,
                    MenteeEmail=email,
                    MenteeGender=gender,
                    MenteeJoinDate=date.today(),
                    Year=date.today().year,
                    # Extract course from ID
                    MenteeCourse=extract_course_from_id(identification_id),
                    # Set default values for other required fields
                    MenteeSemester=1,
                    MenteePhone="",
                    MenteeIC="",
                    MenteeAddress="",
                    MenteePostcode="",
                    MenteeCity="",
                    MenteeState="",
                    MenteeRace="",
                    MenteeReligion="",
                    MenteePreviousSchool="",
                    MenteeFatherName="",
                    MenteeFatherIC="",
                    MenteeFatherOccupation="",
                    MenteeFatherPhone="",
                    MenteeMotherName="",
                    MenteeMotherIC="",
                    MenteeMotherOccupation="",
                    MenteeMotherPhone="",
                )
                
            elif role == 'mentor':
                # Create new mentor profile (NO GENDER FIELD NEEDED)
                mentor_department = extract_department_from_mentor_id(identification_id)
                
                Mentor.objects.create(
                    user=user,
                    MentorID=identification_id,
                    MentorName=full_name,
                    MentorEmail=email,
                    MentorJoinDate=date.today(),
                    MentorDepartment=mentor_department,
                    # NO MentorGender field - not needed!
                    # Default values for other required fields
                    MentorPhone="",
                    MentorIC="",
                    MentorAddress="",
                    MentorPostcode="",
                    MentorCity="",
                    MentorState="",
                    MentorRace="",
                    MentorReligion="",
                    MaxMentees=5,
                )
            
            # SUCCESS message
            messages.success(request, f"Account created successfully! You can now login with your ID: {identification_id}")
            return redirect('login')
            
        except Exception as e:
            # If there's an error, delete the user if it was created
            if 'user' in locals():
                user.delete()
            messages.error(request, f"Error creating account: {str(e)}")
            return render(request, 'signup.html', {
                'preserved_data': {
                    'role': role,
                    'full_name': full_name,
                    'identification_id': identification_id,
                    'email': email,
                    'gender': gender,
                }
            })
    
    # For GET requests, only show mentee and mentor options
    return render(request, 'signup.html')

def extract_course_from_id(mentee_id):
    """Extract course name from mentee ID"""
    # Use the same mapping function
    program_mapping = {
        'CS': 'Diploma in Computer Science',
        'DA': 'Diploma in Accounting',
        'DB': 'Diploma in Business Studies',
        'LH': 'Diploma in Landscape Horticulture',
        'IEP': 'Intensive English Programme',
        'CFAB': 'Certificate in Finance, Accountancy and Business'
    }
    
    try:
        if mentee_id.startswith('B'):
            program_code = mentee_id[1:3]
            return program_mapping.get(program_code, "Unknown Course")
        elif mentee_id.startswith('IEP'):
            return program_mapping.get('IEP', "Intensive English Programme")
        elif mentee_id.startswith('CFAB'):
            return program_mapping.get('CFAB', "Certificate in Finance, Accountancy and Business")
        else:
            return "Unknown Course"
    except:
        return "Unknown Course"

def extract_department_from_mentor_id(mentor_id):
    """Extract department from mentor ID"""
    department_mapping = {
        'A': 'Accounting Department',
        'B': 'Business Studies Department',
        'C': 'Quantitative Science Department',
        'D': 'Landscape and Horticulture Department',
        'GS': 'General Studies'
    }
    
    try:
        if mentor_id.startswith('STGS'):
            department_code = mentor_id[2:4]
        elif mentor_id.startswith('ST'):
            department_code = mentor_id[2:3]
        else:
            return ""
        
        return department_mapping.get(department_code, "")
    except:
        return ""

def login_view(request):
    # Clear activity-related messages that shouldn't be on login page
    storage = messages.get_messages(request)
    messages_to_keep = []
    
    for message in storage:
        # Only keep messages that are relevant to login
        if "logged out" in message.message or "Invalid ID" in message.message:
            messages_to_keep.append(message)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to find user by role-specific IDs
        user = None
        
        # Check if it's a Mentee ID
        try:
            mentee = Mentee.objects.get(MenteeID=username)
            user = mentee.user
        except Mentee.DoesNotExist:
            pass
        
        # Check if it's a Mentor ID
        if not user:
            try:
                mentor = Mentor.objects.get(MentorID=username)
                user = mentor.user
            except Mentor.DoesNotExist:
                pass
        
        # Check if it's a Head ID
        if not user:
            try:
                head = HeadofMentorMentee.objects.get(HeadofMentorMenteeID=username)
                user = head.user
            except HeadofMentorMentee.DoesNotExist:
                pass
        
        # If no role-specific ID found, try as regular username
        if not user:
            try:
                user = CustomUser.objects.get(username=username)
            except CustomUser.DoesNotExist:
                user = None
        
        # Authenticate user
        if user:
            user = authenticate(request, username=user.username, password=password)
        
        if user is not None:
            # Login successful
            login(request, user)
            
            # Clear any remaining messages after successful login
            list(messages.get_messages(request))  # This consumes all messages
            
            # Redirect based on user role
            if user.role == 'mentee':
                return redirect('mentee_homepage')
            elif user.role == 'mentor':
                return redirect('mentor_homepage')
            elif user.role == 'head':
                return redirect('head_homepage')
            else:
                return redirect('mentee_homepage')  # Default fallback
                
        else:
            # Login failed
            messages.error(request, 'Invalid ID or password.')
    
    return render(request, 'login.html')

def is_head(user):
    return user.role == 'head'

@login_required
@user_passes_test(is_head)
def reset_user_password(request, user_id):
    if request.method == 'POST':
        try:
            user = CustomUser.objects.get(id=user_id)
            new_password = request.POST.get('new_password')
            user.set_password(new_password)
            user.save()
            messages.success(request, f"Password reset successfully for {user.username}")
        except CustomUser.DoesNotExist:
            messages.error(request, "User not found")
    
    return redirect('user_management')  # Create this view for user management

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('login')

# ===== MENTEE VIEWS =====
@login_required
def mentee_homepage(request):
    # Get mentee data
    try:
        mentee = request.user.mentee
    except:
        # If mentee profile doesn't exist, create a placeholder
        from .models import Mentee
        from datetime import date
        mentee, created = Mentee.objects.get_or_create(
            user=request.user,
            defaults={
                'MenteeID': request.user.username,
                'MenteeName': request.user.username,
                'MenteeEmail': f"{request.user.username}@student.edu",
                'MenteeJoinDate': date.today(),
                # Add other required fields with blank values
                'MenteeCourse': '',
                'MenteeSemester': 1,
                'Year': date.today().year,
                'MenteePhone': '',
                'MenteeIC': '',
                'MenteeAddress': '',
                'MenteePostcode': '',
                'MenteeCity': '',
                'MenteeState': '',
                'MenteeRace': '',
                'MenteeReligion': '',
                'MenteePreviousSchool': '',
                'MenteeFatherName': '',
                'MenteeFatherIC': '',
                'MenteeFatherOccupation': '',
                'MenteeFatherPhone': '',
                'MenteeMotherName': '',
                'MenteeMotherIC': '',
                'MenteeMotherOccupation': '',
                'MenteeMotherPhone': '',
            }
        )
    
    # Calculate real statistics
    today = timezone.now().date()
    
    # Get upcoming sessions (activities where mentee is assigned and date is today or future)
    # FIXED: Changed 'Mentor' to 'PrimaryMentor'
    upcoming_sessions = Activity.objects.filter(
        Q(attendance__mentee=mentee) | Q(PrimaryMentor=mentee.assigned_mentor),
        Date__gte=today,
        IsMentoringSession=True
    ).distinct().count()
    
    # Get completed activities (past activities)
    # FIXED: Changed 'Mentor' to 'PrimaryMentor'
    completed_activities = Activity.objects.filter(
        Q(attendance__mentee=mentee) | Q(PrimaryMentor=mentee.assigned_mentor),
        Date__lt=today
    ).distinct().count()
    
    # Calculate progress rate (based on attendance)
    total_attended = Attendance.objects.filter(
        mentee=mentee,
        attended=True
    ).count()
    
    total_invited = Attendance.objects.filter(mentee=mentee).count()
    
    if total_invited > 0:
        progress_rate = int((total_attended / total_invited) * 100)
    else:
        progress_rate = 0
    
    # Get achievements (completed mentoring sessions with materials)
    achievements = MentoringSession.objects.filter(
        activity__attendance__mentee=mentee,
        activity__attendance__attended=True,
        completed=True
    ).distinct().count()
    
    # NEW: Calculate upcoming activities count for notification badge
    # This includes both mentoring sessions and general activities
    if mentee.assigned_mentor:
        # Get activities where mentee is specifically invited or general activities
        mentoring_activities = Activity.objects.filter(
            IsMentoringSession=True,
            PrimaryMentor=mentee.assigned_mentor,
            Date__gte=today
        )
        
        # Get general activities (not mentoring sessions)
        general_activities = Activity.objects.filter(
            IsMentoringSession=False,
            Date__gte=today
        )
        
        # Combine both types of activities and count
        upcoming_activities_count = (mentoring_activities.count() + general_activities.count())
    else:
        # If no mentor assigned, only show general activities
        upcoming_activities_count = Activity.objects.filter(
            IsMentoringSession=False,
            Date__gte=today
        ).count()
    
    context = {
        'user': request.user,
        'mentee': mentee,
        'upcoming_sessions': upcoming_sessions,
        'completed_activities': completed_activities,
        'progress_rate': progress_rate,
        'achievements': achievements,
        'upcoming_activities_count': upcoming_activities_count,  # NEW: For notification badge
    }
    return render(request, 'homepage_mentee.html', context)

@login_required
def update_personal_info(request):
    mentee = get_object_or_404(Mentee, user=request.user)
    
    # Function to get full course name from MenteeID
    def get_course_full_name_from_id(mentee_id):
        course_mapping = {
            'CS': 'Diploma in Computer Science',
            'DA': 'Diploma in Accounting',
            'DB': 'Diploma in Business Studies',
            'LH': 'Diploma in Landscape Horticulture',
            'IEP': 'Intensive English Programme',
            'CFAB': 'Certificate in Finance, Accountancy and Business'
        }
        
        if mentee_id.startswith('B'):
            program_code = mentee_id[1:3]
            return course_mapping.get(program_code, mentee.MenteeCourse)
        elif mentee_id.startswith('IEP'):
            return course_mapping.get('IEP', mentee.MenteeCourse)
        elif mentee_id.startswith('CFAB'):
            return course_mapping.get('CFAB', mentee.MenteeCourse)
        else:
            return mentee.MenteeCourse

    display_course = get_course_full_name_from_id(mentee.MenteeID)
    
    if request.method == 'POST':
        try:
            print("DEBUG: Form submitted with CSRF token")
            print(f"DEBUG: Files in request: {list(request.FILES.keys())}")
            
            # Update all personal information fields
            mentee.MenteeName = request.POST.get('MenteeName', mentee.MenteeName)
            mentee.MenteeEmail = request.POST.get('MenteeEmail', mentee.MenteeEmail)
            mentee.MenteePhone = request.POST.get('MenteePhone', mentee.MenteePhone)
            mentee.MenteeIC = request.POST.get('MenteeIC', mentee.MenteeIC)
            mentee.MenteeGender = request.POST.get('MenteeGender', mentee.MenteeGender)
            mentee.MenteeSemester = request.POST.get('MenteeSemester', mentee.MenteeSemester)
            mentee.MenteeRace = request.POST.get('MenteeRace', mentee.MenteeRace)
            mentee.MenteeReligion = request.POST.get('MenteeReligion', mentee.MenteeReligion)
            mentee.MenteePreviousSchool = request.POST.get('MenteePreviousSchool', mentee.MenteePreviousSchool)
            mentee.MenteeAddress = request.POST.get('MenteeAddress', mentee.MenteeAddress)
            mentee.MenteePostcode = request.POST.get('MenteePostcode', mentee.MenteePostcode)
            mentee.MenteeCity = request.POST.get('MenteeCity', mentee.MenteeCity)
            mentee.MenteeState = request.POST.get('MenteeState', mentee.MenteeState)
            
            # Update parent information
            mentee.MenteeFatherName = request.POST.get('MenteeFatherName', mentee.MenteeFatherName)
            mentee.MenteeFatherIC = request.POST.get('MenteeFatherIC', mentee.MenteeFatherIC)
            mentee.MenteeFatherOccupation = request.POST.get('MenteeFatherOccupation', mentee.MenteeFatherOccupation)
            mentee.MenteeFatherPhone = request.POST.get('MenteeFatherPhone', mentee.MenteeFatherPhone)
            mentee.MenteeMotherName = request.POST.get('MenteeMotherName', mentee.MenteeMotherName)
            mentee.MenteeMotherIC = request.POST.get('MenteeMotherIC', mentee.MenteeMotherIC)
            mentee.MenteeMotherOccupation = request.POST.get('MenteeMotherOccupation', mentee.MenteeMotherOccupation)
            mentee.MenteeMotherPhone = request.POST.get('MenteeMotherPhone', mentee.MenteeMotherPhone)
            
            # Update academic information
            mentee.MenteeCourse = request.POST.get('MenteeCourse', mentee.MenteeCourse)
            mentee.MenteeSemester = request.POST.get('MenteeSemester', mentee.MenteeSemester)
            mentee.Year = request.POST.get('Year', mentee.Year)
            
            # Handle date field - preserve existing value if empty
            join_date = request.POST.get('MenteeJoinDate')
            if join_date and join_date.strip():
                mentee.MenteeJoinDate = join_date
            # else: keep existing mentee.MenteeJoinDate
            
            mentee.MenteeStatus = request.POST.get('MenteeStatus', mentee.MenteeStatus)
            mentee.MenteePreviousSchool = request.POST.get('MenteePreviousSchool', mentee.MenteePreviousSchool)
            
            # Helper function to convert GPA values (empty strings to None for DecimalField)
            # Uses fallback to preserve existing value if form field is empty
            def parse_gpa(value, fallback=None):
                if value is None or value == '':
                    return fallback  # Preserve existing value
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return fallback
            
            # Update GPA fields with proper None handling for DecimalFields
            # Pass existing values as fallback to preserve them if form field is empty
            mentee.Sem1TargetGPA = parse_gpa(request.POST.get('MenteeSem1TargetGPA'), mentee.Sem1TargetGPA)
            mentee.Sem1ActualGPA = parse_gpa(request.POST.get('MenteeSem1ActualGPA'), mentee.Sem1ActualGPA)
            mentee.Sem2TargetGPA = parse_gpa(request.POST.get('MenteeSem2TargetGPA'), mentee.Sem2TargetGPA)
            mentee.Sem2ActualGPA = parse_gpa(request.POST.get('MenteeSem2ActualGPA'), mentee.Sem2ActualGPA)
            mentee.Sem3TargetGPA = parse_gpa(request.POST.get('MenteeSem3TargetGPA'), mentee.Sem3TargetGPA)
            mentee.Sem3ActualGPA = parse_gpa(request.POST.get('MenteeSem3ActualGPA'), mentee.Sem3ActualGPA)
            mentee.Sem4TargetGPA = parse_gpa(request.POST.get('MenteeSem4TargetGPA'), mentee.Sem4TargetGPA)
            mentee.Sem4ActualGPA = parse_gpa(request.POST.get('MenteeSem4ActualGPA'), mentee.Sem4ActualGPA)
            mentee.Sem5TargetGPA = parse_gpa(request.POST.get('MenteeSem5TargetGPA'), mentee.Sem5TargetGPA)
            mentee.Sem5ActualGPA = parse_gpa(request.POST.get('MenteeSem5ActualGPA'), mentee.Sem5ActualGPA)
            mentee.Sem6TargetGPA = parse_gpa(request.POST.get('MenteeSem6TargetGPA'), mentee.Sem6TargetGPA)
            mentee.Sem6ActualGPA = parse_gpa(request.POST.get('MenteeSem6ActualGPA'), mentee.Sem6ActualGPA)
            mentee.TargetCGPA = parse_gpa(request.POST.get('TargetCGPA'), mentee.TargetCGPA)
            mentee.CurrentCGPA = parse_gpa(request.POST.get('CurrentCGPA'), mentee.CurrentCGPA)
            
            mentee.MenteeAcademicGoals = request.POST.get('MenteeAcademicGoals', mentee.MenteeAcademicGoals)
            mentee.MenteeStudyHabits = request.POST.get('MenteeStudyHabits', mentee.MenteeStudyHabits)
            mentee.MenteeSubjects = request.POST.get('MenteeSubjects', mentee.MenteeSubjects)
            mentee.MenteeExtracurricular = request.POST.get('MenteeExtracurricular', mentee.MenteeExtracurricular)
            mentee.AcademicSupportNeeds = request.POST.get('AcademicSupportNeeds', mentee.AcademicSupportNeeds)
            
            # FIXED: Profile picture handling - check both possible field names
            profile_picture = None
            if 'profile_picture' in request.FILES:
                profile_picture = request.FILES['profile_picture']
                print(f"DEBUG: Found profile_picture in FILES: {profile_picture.name}")
            elif 'profile_picture' in request.POST:
                print("DEBUG: profile_picture found in POST data")
            
            if profile_picture:
                print(f"DEBUG: Processing profile picture - Name: {profile_picture.name}, Size: {profile_picture.size}, Type: {profile_picture.content_type}")
                
                try:
                    # Enhanced file validation
                    if not profile_picture.content_type.startswith('image/'):
                        messages.error(request, 'Please upload a valid image file.')
                        return redirect('update_personal_info')
                    
                    # Check file size (15MB limit)
                    if profile_picture.size > 15 * 1024 * 1024:
                        messages.error(request, 'Image file too large ( > 15MB )')
                        return redirect('update_personal_info')
                    
                    # Check file type
                    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
                    if profile_picture.content_type not in allowed_types:
                        messages.error(request, 'Please upload a valid image file (JPEG, PNG, GIF, WEBP)')
                        return redirect('update_personal_info')
                    
                    # Check file extension
                    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                    file_extension = os.path.splitext(profile_picture.name)[1].lower()
                    if file_extension not in valid_extensions:
                        messages.error(request, 'Invalid file extension. Please upload JPG, PNG, GIF, or WEBP files.')
                        return redirect('update_personal_info')
                    
                    # Delete old profile picture if exists
                    if mentee.profile_picture:
                        try:
                            if os.path.isfile(mentee.profile_picture.path):
                                os.remove(mentee.profile_picture.path)
                                print("DEBUG: Old profile picture deleted")
                        except Exception as e:
                            print(f"DEBUG: Error deleting old profile picture: {str(e)}")
                            # Continue with new upload even if old file deletion fails
                    
                    # Generate unique filename
                    file_extension = os.path.splitext(profile_picture.name)[1].lower()
                    unique_filename = f"mentee_{mentee.MenteeID}_{int(time.time())}{file_extension}"
                    
                    # Save the profile picture
                    mentee.profile_picture.save(unique_filename, profile_picture, save=False)
                    print(f"DEBUG: Profile picture saved to mentee model: {mentee.profile_picture.name}")
                    
                    messages.success(request, 'Profile picture updated successfully!')
                    
                except Exception as e:
                    print(f"DEBUG: Error uploading profile picture: {str(e)}")
                    import traceback
                    print(f"DEBUG: Traceback: {traceback.format_exc()}")
                    messages.error(request, f'Error uploading profile picture: {str(e)}')
            else:
                print("DEBUG: No profile picture uploaded in this request")

            # Save all mentee changes (including profile picture if uploaded)
            mentee.save()
            print("DEBUG: Mentee profile saved successfully")
            
            # Debug information after save
            if mentee.profile_picture:
                print(f"DEBUG: Final profile picture path: {mentee.profile_picture.path}")
                print(f"DEBUG: Final profile picture URL: {mentee.profile_picture.url}")
                try:
                    file_exists = os.path.exists(mentee.profile_picture.path)
                    print(f"DEBUG: File exists: {file_exists}")
                except:
                    print("DEBUG: Could not check file existence")
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('update_personal_info')
            
        except Exception as e:
            print(f"DEBUG: Error saving profile: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            messages.error(request, f'Error updating profile: {str(e)}')
    
    # For GET requests, render the form with display course
    context = {
        'mentee': mentee,
        'display_course': display_course
    }
    return render(request, 'mentee_profile.html', context)

@login_required
def view_assigned_mentor(request):
    mentee = get_object_or_404(Mentee, user=request.user)
    return render(request, 'view_mentor.html', {'mentee': mentee})

@login_required
def view_activity_schedules(request):
    mentee = get_object_or_404(Mentee, user=request.user)
    
    # Get today's date
    today = timezone.now().date()
    
    # Get all activities that this mentee should attend
    if mentee.assigned_mentor:
        # Get activities where mentee is specifically invited or general activities
        mentoring_activities = Activity.objects.filter(
            IsMentoringSession=True,
            PrimaryMentor=mentee.assigned_mentor,
        ).order_by('Date', 'StartTime')
        
        # Get general activities (not mentoring sessions)
        general_activities = Activity.objects.filter(
            IsMentoringSession=False,
        ).order_by('Date', 'StartTime')
        
        # Combine both types of activities
        all_activities = list(mentoring_activities) + list(general_activities)
        all_activities.sort(key=lambda x: (x.Date, x.StartTime))
    else:
        # If no mentor assigned, only show general activities
        all_activities = Activity.objects.filter(
            IsMentoringSession=False,
        ).order_by('Date', 'StartTime')
    
    # PROPERLY CATEGORIZE ACTIVITIES
    # Upcoming activities: Future dates only
    upcoming_activities = [activity for activity in all_activities if activity.Date > today]
    
    # Completed activities: Past dates OR mentoring sessions that are explicitly marked as completed
    completed_activities = []
    for activity in all_activities:
        # For mentoring sessions, check if they are explicitly completed
        if activity.IsMentoringSession:
            try:
                mentoring_session = MentoringSession.objects.get(activity=activity)
                # Show in completed if session is marked as completed OR has materials uploaded
                if mentoring_session.completed or mentoring_session.materials:
                    completed_activities.append(activity)
                # Also include past mentoring sessions even if not explicitly completed
                elif activity.Date < today:
                    completed_activities.append(activity)
            except MentoringSession.DoesNotExist:
                # If no mentoring session record exists but date is past, include it
                if activity.Date < today:
                    completed_activities.append(activity)
        else:
            # For non-mentoring sessions, just use date comparison
            if activity.Date < today:
                completed_activities.append(activity)
    
    # Sort completed activities by date (most recent first)
    completed_activities.sort(key=lambda x: x.Date, reverse=True)
    
    context = {
        'mentee': mentee,
        'upcoming_activities': upcoming_activities,
        'completed_activities': completed_activities,
        'today': today,
    }
    
    return render(request, 'activity_schedule.html', context)

# ===== MENTOR VIEWS =====
@login_required
def mentor_homepage(request):
    # Get mentor data
    try:
        mentor = request.user.mentor
    except:
        # If mentor profile doesn't exist, create a placeholder
        from .models import Mentor
        from datetime import date
        mentor, created = Mentor.objects.get_or_create(
            user=request.user,
            defaults={
                'MentorID': request.user.username,
                'MentorName': request.user.username,
                'MentorEmail': f"{request.user.username}@staff.edu",
                'MentorJoinDate': date.today(),
                # Add other required fields with default values
                'MentorPhone': 'Not set',
                'MentorIC': 'Not set',
                'MentorAddress': 'Not set',
                'MentorPostcode': '00000',
                'MentorCity': 'Not set',
                'MentorState': 'Not set',
                'MentorRace': 'Not set',
                'MentorReligion': 'Not set',
                'MentorDeparment': 'Computer Science',
                'MaxMentees': 10,
            }
        )
    
    # Calculate real statistics
    today = timezone.now().date()
    
    # Get total assigned mentees (mentees where this mentor is assigned_mentor)
    assigned_mentees_count = Mentee.objects.filter(assigned_mentor=mentor).count()
    
    # Get total mentees in the entire system (not just assigned to this mentor)
    total_mentees_system = Mentee.objects.count()
    
    # Get system-wide assigned and pending mentees
    mentees_with_mentor = Mentee.objects.filter(assigned_mentor__isnull=False).count()
    mentees_pending = Mentee.objects.filter(assigned_mentor__isnull=True).count()
    
    # Get upcoming sessions (activities where mentor is primary mentor and date is today or future)
    upcoming_sessions = Activity.objects.filter(
        PrimaryMentor=mentor,
        Date__gte=today,
        IsMentoringSession=True
    ).count()
    
    # Get completed sessions (past mentoring sessions)
    completed_sessions = Activity.objects.filter(
        PrimaryMentor=mentor,
        Date__lt=today,
        IsMentoringSession=True
    ).count()
    
    # Calculate total sessions (upcoming + completed)
    total_sessions = upcoming_sessions + completed_sessions
    
    # Get pending reports (activities without completed mentoring sessions)
    pending_reports = Activity.objects.filter(
        PrimaryMentor=mentor,
        IsMentoringSession=True,
        Date__lt=today
    ).exclude(
        mentoringsession__completed=True
    ).count()
    
    # Calculate completion rate based on mentoring sessions
    total_past_sessions = Activity.objects.filter(
        PrimaryMentor=mentor,
        Date__lt=today,
        IsMentoringSession=True
    ).count()
    
    completed_sessions_with_materials = MentoringSession.objects.filter(
        activity__PrimaryMentor=mentor,
        activity__Date__lt=today,
        completed=True
    ).count()
    
    if total_past_sessions > 0:
        completion_rate = int((completed_sessions_with_materials / total_past_sessions) * 100)
    else:
        completion_rate = 0
    
    # Calculate monthly sessions for the current year (for graph)
    from django.db.models import Count
    from django.db.models.functions import ExtractMonth
    import json
    
    current_year = today.year
    monthly_sessions_query = Activity.objects.filter(
        PrimaryMentor=mentor,
        IsMentoringSession=True,
        Date__year=current_year
    ).annotate(
        month=ExtractMonth('Date')
    ).values('month').annotate(
        count=Count('ActivityID')
    ).order_by('month')
    
    # Create array of 12 months with counts
    monthly_sessions_data = [0] * 12  # Initialize with zeros for all 12 months
    for item in monthly_sessions_query:
        month_index = item['month'] - 1  # Convert 1-12 to 0-11 for array indexing
        monthly_sessions_data[month_index] = item['count']
    
    # Convert to JSON string for JavaScript
    monthly_sessions_json = json.dumps(monthly_sessions_data)
    
    context = {
        'user': request.user,
        'mentor': mentor,
        'assigned_mentees': assigned_mentees_count,
        'total_mentees_system': total_mentees_system,
        'mentees_with_mentor': mentees_with_mentor,
        'mentees_pending': mentees_pending,
        'total_sessions': total_sessions,
        'upcoming_sessions': upcoming_sessions,
        'pending_reports': pending_reports,
        'completion_rate': completion_rate,
        'monthly_sessions': monthly_sessions_json,
    }
    return render(request, 'homepage_mentor.html', context)


@login_required
def mentor_update_profile(request):
    """View for mentor to update their profile - FIXED VERSION"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    mentor = get_object_or_404(Mentor, user=request.user)
    
    if request.method == 'POST':
        try:
            print("DEBUG: Form submitted with CSRF token")
            print(f"DEBUG: Files in request: {list(request.FILES.keys())}")
            
            # Update mentor information
            mentor.MentorName = request.POST.get('MentorName')
            mentor.MentorEmail = request.POST.get('MentorEmail')
            mentor.MentorPhone = request.POST.get('MentorPhone')
            mentor.MentorAddress = request.POST.get('MentorAddress')
            mentor.MentorCity = request.POST.get('MentorCity')
            mentor.MentorState = request.POST.get('MentorState')
            mentor.MentorPostcode = request.POST.get('MentorPostcode')
            mentor.MentorRace = request.POST.get('MentorRace')
            mentor.MentorReligion = request.POST.get('MentorReligion')
            
            # FIXED: Enhanced profile picture handling for mentor
            if 'profile_picture' in request.FILES:
                profile_picture = request.FILES['profile_picture']
                print(f"DEBUG: Processing profile picture - Name: {profile_picture.name}, Size: {profile_picture.size}, Type: {profile_picture.content_type}")
                
                # Enhanced file validation
                try:
                    # Check if file is actually an image
                    if not profile_picture.content_type.startswith('image/'):
                        messages.error(request, 'Please upload a valid image file.')
                        return redirect('mentor_update_profile')
                    
                    # Check file size (15MB limit)
                    if profile_picture.size > 15 * 1024 * 1024:
                        messages.error(request, 'Image file too large ( > 15MB )')
                        return redirect('mentor_update_profile')
                    
                    # Check file type more thoroughly
                    allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
                    if profile_picture.content_type not in allowed_types:
                        messages.error(request, 'Please upload a valid image file (JPEG, PNG, GIF, WEBP)')
                        return redirect('mentor_update_profile')
                    
                    # Check file extension
                    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
                    file_extension = os.path.splitext(profile_picture.name)[1].lower()
                    if file_extension not in valid_extensions:
                        messages.error(request, 'Invalid file extension. Please upload JPG, PNG, GIF, or WEBP files.')
                        return redirect('mentor_update_profile')
                    
                    # Delete old profile picture if exists
                    if mentor.profile_picture:
                        try:
                            old_file_path = mentor.profile_picture.path
                            if os.path.isfile(old_file_path):
                                os.remove(old_file_path)
                                print("DEBUG: Old profile picture deleted")
                        except Exception as e:
                            print(f"DEBUG: Error deleting old profile picture: {str(e)}")
                            # Continue with new upload even if old file deletion fails
                    
                    # Generate unique filename
                    file_extension = os.path.splitext(profile_picture.name)[1].lower()
                    unique_filename = f"mentor_{mentor.MentorID}_{int(time.time())}{file_extension}"
                    
                    # Save to mentor's profile_picture field
                    mentor.profile_picture.save(unique_filename, profile_picture, save=False)
                    print(f"DEBUG: Profile picture saved to mentor model: {mentor.profile_picture.name}")
                    
                    messages.success(request, 'Profile picture updated successfully!')
                    
                except Exception as e:
                    print(f"DEBUG: Error uploading profile picture: {str(e)}")
                    messages.error(request, f'Error uploading profile picture: {str(e)}')
            else:
                print("DEBUG: No profile picture in request")

            # Save mentor changes
            mentor.save()
            print("DEBUG: Mentor profile saved successfully")
            
            # Debug information after save
            if mentor.profile_picture:
                print(f"DEBUG: Final profile picture path: {mentor.profile_picture.path}")
                print(f"DEBUG: Final profile picture URL: {mentor.profile_picture.url}")
                print(f"DEBUG: File exists: {os.path.exists(mentor.profile_picture.path) if mentor.profile_picture else 'No file'}")
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('mentor_update_profile')
            
        except Exception as e:
            print(f"DEBUG: Error saving profile: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback: {traceback.format_exc()}")
            messages.error(request, f'Error updating profile: {str(e)}')
    
    return render(request, 'mentor_profile.html', {'mentor': mentor})

@login_required
def mentor_view_mentee(request, mentee_id):
    """View for mentor to see detailed information about a specific mentee - UPDATED TO ALLOW VIEWING ALL MENTEES"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    mentor = get_object_or_404(Mentor, user=request.user)
    
    try:
        # REMOVED THE assigned_mentor FILTER - allow viewing any mentee
        mentee = get_object_or_404(Mentee, MenteeID=mentee_id)
        
        # Check if this mentee is assigned to the current mentor
        is_assigned_to_me = mentee.assigned_mentor == mentor
        
        # Calculate statistics for this mentee
        today = timezone.now().date()
        
        # Get session count (activities where mentee attended)
        # Only count sessions relevant to this mentor if not assigned
        if is_assigned_to_me:
            session_count = Attendance.objects.filter(
                mentee=mentee,
                attended=True,
                activity__IsMentoringSession=True
            ).count()
        else:
            # For mentees not assigned to this mentor, only show sessions they conducted
            session_count = Attendance.objects.filter(
                mentee=mentee,
                attended=True,
                activity__IsMentoringSession=True,
                activity__PrimaryMentor=mentor  # Only sessions conducted by this mentor
            ).count()
        
        # Calculate attendance rate
        if is_assigned_to_me:
            total_invited = Attendance.objects.filter(mentee=mentee).count()
        else:
            total_invited = Attendance.objects.filter(
                mentee=mentee,
                activity__PrimaryMentor=mentor  # Only sessions by this mentor
            ).count()
            
        if total_invited > 0:
            attendance_rate = int((session_count / total_invited) * 100)
        else:
            attendance_rate = 0
        
        # Calculate progress rate (placeholder - you can implement your own logic)
        progress_rate = min(attendance_rate + 30, 100)  # Example calculation
        
        # Get achievements count
        if is_assigned_to_me:
            achievements = MentoringSession.objects.filter(
                activity__attendance__mentee=mentee,
                activity__attendance__attended=True,
                completed=True
            ).distinct().count()
        else:
            achievements = MentoringSession.objects.filter(
                activity__attendance__mentee=mentee,
                activity__attendance__attended=True,
                completed=True,
                activity__PrimaryMentor=mentor  # Only achievements from this mentor's sessions
            ).distinct().count()
        
        context = {
            'mentor': mentor,
            'mentee': mentee,
            'is_assigned_to_me': is_assigned_to_me,  # Pass this flag to template
            'session_count': session_count,
            'attendance_rate': attendance_rate,
            'progress_rate': progress_rate,
            'achievements': achievements,
        }
        
        return render(request, 'mentor_view_mentee.html', context)
        
    except Mentee.DoesNotExist:
        messages.error(request, 'Mentee not found.')
        return redirect('view_assigned_mentees')

@login_required
def view_assigned_mentees(request):
    """View for mentor to see mentees with search functionality"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    mentor = get_object_or_404(Mentor, user=request.user)
    
    # Get assigned mentees for this mentor
    assigned_mentees = Mentee.objects.filter(assigned_mentor=mentor)
    
    # Get ALL mentees initially for stats and search capability
    all_mentees = Mentee.objects.all().select_related('assigned_mentor')
    
    # DEFAULT: Show only assigned mentees
    display_mentees = assigned_mentees
    
    # Handle search functionality
    search_query = request.GET.get('search', '')
    is_searching = False
    
    if search_query:
        is_searching = True
        # When searching, show ALL mentees that match the search
        display_mentees = all_mentees.filter(
            Q(MenteeID__icontains=search_query) |
            Q(MenteeName__icontains=search_query) |
            Q(MenteeCourse__icontains=search_query) |
            Q(assigned_mentor__MentorName__icontains=search_query)
        )
    
    # Handle status filter
    status_filter = request.GET.get('status', 'all')
    if status_filter != 'all':
        display_mentees = display_mentees.filter(MenteeStatus=status_filter)
    
    # Handle sort
    sort_by = request.GET.get('sort', 'name_asc')
    if sort_by == 'name_asc':
        display_mentees = display_mentees.order_by('MenteeName')
    elif sort_by == 'name_desc':
        display_mentees = display_mentees.order_by('-MenteeName')
    elif sort_by == 'id_asc':
        display_mentees = display_mentees.order_by('MenteeID')
    elif sort_by == 'id_desc':
        display_mentees = display_mentees.order_by('-MenteeID')
    elif sort_by == 'course_asc':
        display_mentees = display_mentees.order_by('MenteeCourse', 'MenteeName')
    
    # Calculate statistics (for assigned mentees only)
    active_mentees_count = assigned_mentees.filter(MenteeStatus='active').count()
    male_mentees_count = assigned_mentees.filter(MenteeGender='male').count()
    female_mentees_count = assigned_mentees.filter(MenteeGender='female').count()
    
    context = {
        'mentor': mentor,
        'assigned_mentees': assigned_mentees,  # For statistics
        'display_mentees': display_mentees,    # For display in table
        'active_mentees_count': active_mentees_count,
        'male_mentees_count': male_mentees_count,
        'female_mentees_count': female_mentees_count,
        'search_query': search_query,
        'status_filter': status_filter,
        'sort_by': sort_by,
        'is_searching': is_searching,
        'total_mentees_count': all_mentees.count(),  # Total in system
        'assigned_count': assigned_mentees.count(),  # Count of assigned mentees
    }
    
    return render(request, 'view_mentees.html', context)

@login_required
def mentoring_schedule(request):
    """View for mentor to manage their mentoring schedule"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    mentor = get_object_or_404(Mentor, user=request.user)
    today = timezone.now().date()
    
    # Get time filter from request, default to 'all'
    time_filter = request.GET.get('time_filter', 'all')
    
    # FIXED: Proper filtering logic for mentoring sessions
    if time_filter == 'completed':
        # Show ONLY sessions that are explicitly marked as completed
        mentoring_activities = Activity.objects.filter(
            IsMentoringSession=True,
            PrimaryMentor=mentor,
            mentoringsession__completed=True  # Only explicitly completed sessions
        ).distinct().order_by('-Date', 'StartTime')
    
    elif time_filter == 'upcoming':
        # Show ONLY sessions that are NOT completed AND have future dates
        mentoring_activities = Activity.objects.filter(
            IsMentoringSession=True,
            PrimaryMentor=mentor,
        ).exclude(
            mentoringsession__completed=True  # Exclude any completed sessions
        ).filter(
            Date__gte=today  # Only future or today's dates
        ).distinct().order_by('Date', 'StartTime')
    
    elif time_filter == 'today':
        # Show today's sessions that are NOT completed
        mentoring_activities = Activity.objects.filter(
            IsMentoringSession=True,
            PrimaryMentor=mentor,
            Date=today,
        ).exclude(
            mentoringsession__completed=True  # Exclude completed sessions
        ).distinct().order_by('StartTime')
    
    else:  # 'all' (default)
        # Show all sessions regardless of status
        mentoring_activities = Activity.objects.filter(
            IsMentoringSession=True,
            PrimaryMentor=mentor,
        ).distinct().order_by('-Date', 'StartTime')
    
    # Get mentoring session details for each activity
    sessions_data = []
    completed_count = 0
    upcoming_count = 0
    
    for activity in mentoring_activities:
        try:
            mentoring_session = MentoringSession.objects.get(activity=activity)
            
            # Count completed vs upcoming for context
            if mentoring_session.completed:
                completed_count += 1
            else:
                upcoming_count += 1
                
            sessions_data.append({
                'activity': activity,
                'mentoring_session': mentoring_session,
                'attendance': Attendance.objects.filter(activity=activity)
            })
        except MentoringSession.DoesNotExist:
            continue
    
    context = {
        'mentor': mentor,
        'sessions_data': sessions_data,
        'time_filter': time_filter,
        'today': today,
        'completed_count': completed_count,
        'upcoming_count': upcoming_count,
        'total_sessions': len(sessions_data),
        'assigned_mentees_count': mentor.mentee_set.count(),
    }
    
    return render(request, 'mentoring_schedule.html', context)

@login_required
def create_mentoring_session(request):
    """View for mentor to create a new mentoring session"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    mentor = get_object_or_404(Mentor, user=request.user)
    
    if request.method == 'POST':
        try:
            # Generate unique ActivityID in S00001 format
            # Find the highest existing session ID
            last_session = Activity.objects.filter(
                ActivityID__startswith='S'
            ).order_by('-ActivityID').first()
            
            if last_session and last_session.ActivityID.startswith('S'):
                # Extract number and increment
                try:
                    last_number = int(last_session.ActivityID[1:])
                    next_number = last_number + 1
                except ValueError:
                    next_number = 1
            else:
                # Start from 1 if no sessions exist
                next_number = 1
            
            # Format as S00001, S00002, etc.
            activity_id = f"S{next_number:05d}"
            
            # Create the activity first
            activity = Activity.objects.create(
                ActivityID=activity_id,
                ActivityName=request.POST.get('session_topic'),
                ActivityType='mentoring',
                Description=request.POST.get('session_description', ''),
                Date=request.POST.get('session_date'),
                StartTime=request.POST.get('session_start_time'),
                EndTime=request.POST.get('session_end_time'),
                Location=request.POST.get('session_location', 'Mentor Office'),
                CreatedBy=request.user,
                IsMentoringSession=True,
                PrimaryMentor=mentor,
            )
            
            # Create the mentoring session
            mentoring_session = MentoringSession.objects.create(
                activity=activity,
                session_type=request.POST.get('session_type', 'individual'),
                topic=request.POST.get('session_topic'),
            )
            
            # Handle attendees for group sessions
            session_type = request.POST.get('session_type')
            
            if session_type == 'group':
                # Get all selected attendees
                attendee_ids = request.POST.getlist('attendees')
                print(f"DEBUG: Selected attendees for group session: {attendee_ids}")
                
                if not attendee_ids:
                    messages.error(request, 'Please select at least one mentee for group session.')
                    return redirect('create_mentoring_session')
                
                for mentee_id in attendee_ids:
                    try:
                        mentee = Mentee.objects.get(MenteeID=mentee_id)
                        Attendance.objects.create(
                            activity=activity,
                            mentee=mentee,
                            attended=False
                        )
                        print(f"DEBUG: Added {mentee.MenteeName} to group session")
                    except Mentee.DoesNotExist:
                        messages.warning(request, f'Mentee with ID {mentee_id} not found.')
                        continue
                    
            else:  # Individual session
                mentee_id = request.POST.get('mentee')
                if mentee_id:
                    mentee = Mentee.objects.get(MenteeID=mentee_id)
                    Attendance.objects.create(
                        activity=activity,
                        mentee=mentee,
                        attended=False
                    )
            
            messages.success(request, f'Mentoring session created successfully! Session ID: {activity_id}')
            return redirect('mentoring_schedule')
            
        except Exception as e:
            messages.error(request, f'Error creating session: {str(e)}')
            # Debug information
            import traceback
            print(f"ERROR: {str(e)}")
            print(traceback.format_exc())
    
    # If GET request, show form
    assigned_mentees = Mentee.objects.filter(assigned_mentor=mentor)
    return render(request, 'create_session.html', {
        'mentor': mentor,
        'assigned_mentees': assigned_mentees,
        'today': timezone.now().date()
    })

@login_required
def complete_mentoring_session(request, activity_id):
    """View for mentor to mark a session as completed and upload materials - UPDATED FOR AJAX"""
    if request.user.role != 'mentor':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Access denied. Mentor role required.'}, status=403)
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    # FIXED: Use PrimaryMentor instead of Mentor
    activity = get_object_or_404(Activity, ActivityID=activity_id, PrimaryMentor__user=request.user)
    mentoring_session = get_object_or_404(MentoringSession, activity=activity)
    
    if request.method == 'POST':
        try:
            # Handle file upload
            if 'session_materials' in request.FILES:
                mentoring_session.materials = request.FILES['session_materials']
                # Auto-mark as completed when materials are uploaded
                mentoring_session.completed = True
                mentoring_session.completion_date = timezone.now()
                mentoring_session.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Materials uploaded and session marked as completed!'})
            
            # Original form submission (mark as completed with materials)
            mentoring_session.completed = True
            mentoring_session.completion_date = timezone.now()
            
            # Handle file upload
            if 'session_materials' in request.FILES:
                mentoring_session.materials = request.FILES['session_materials']
            
            # Update attendance
            attendance_records = Attendance.objects.filter(activity=activity)
            for attendance in attendance_records:
                attended_field = f'attended_{attendance.mentee.MenteeID}'
                if attended_field in request.POST:
                    attendance.attended = True
                    attendance.save()
            
            mentoring_session.save()
            
            messages.success(request, 'Session marked as completed successfully!')
            return redirect('mentoring_schedule')
            
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': f'Error uploading materials: {str(e)}'}, status=500)
            messages.error(request, f'Error completing session: {str(e)}')
    
    # Get attendance for this session
    attendance = Attendance.objects.filter(activity=activity)
    
    return render(request, 'complete_session.html', {
        'activity': activity,
        'mentoring_session': mentoring_session,
        'attendance': attendance
    })

@login_required
def delete_mentoring_session(request, activity_id):
    """View for mentor to delete a mentoring session - FIXED VERSION"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    # FIXED: Use PrimaryMentor instead of Mentor
    activity = get_object_or_404(Activity, ActivityID=activity_id, PrimaryMentor__user=request.user)
    
    if request.method == 'POST':
        activity.delete()
        messages.success(request, 'Session deleted successfully!')
    
    return redirect('mentoring_schedule')

@login_required
def activity_report(request):
    """View for mentor to manage activity reports"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    mentor = get_object_or_404(Mentor, user=request.user)
    
    # Get activities that can have reports (completed mentoring sessions)
    # FIXED: Use PrimaryMentor instead of Mentor
    reportable_activities = Activity.objects.filter(
        IsMentoringSession=True,
        PrimaryMentor=mentor,  # Changed from Mentor to PrimaryMentor
        mentoringsession__completed=True
    ).order_by('-Date')
    
    # Get existing reports with attendance statistics
    existing_reports = []
    reports = ActivityReport.objects.filter(
        activity__in=reportable_activities
    ).select_related('activity')
    
    for report in reports:
        # Calculate attendance statistics for each report
        attendance_records = Attendance.objects.filter(activity=report.activity)
        total_attendees = attendance_records.count()
        present_count = attendance_records.filter(attended=True).count()
        
        # Add statistics to the report object
        report.total_attendees = total_attendees
        report.present_count = present_count
        existing_reports.append(report)
    
    # Activities without reports
    activities_without_reports = reportable_activities.exclude(
        activityreport__isnull=False
    )
    
    context = {
        'mentor': mentor,
        'existing_reports': existing_reports,
        'activities_without_reports': activities_without_reports,
    }
    
    return render(request, 'activity_report.html', context)

@login_required
def create_activity_report(request, activity_id):
    """View for mentor to create a new activity report - UPDATED VERSION WITH DEBUGGING"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    # Get mentor with profile picture
    mentor = get_object_or_404(Mentor, user=request.user)
    
    # Get activity and mentoring session
    activity = get_object_or_404(Activity, ActivityID=activity_id, PrimaryMentor=mentor)
    mentoring_session = get_object_or_404(MentoringSession, activity=activity)
    
    # Check if report already exists
    if hasattr(activity, 'activityreport'):
        messages.info(request, 'A report already exists for this activity.')
        return redirect('activity_report')
    
    if request.method == 'POST':
        try:
            # DEBUG: Print all POST data to see what's being submitted
            print("=== DEBUG: CREATE ACTIVITY REPORT POST DATA ===")
            print(f"Activity: {activity.ActivityID} - {activity.ActivityName}")
            for key, value in request.POST.items():
                if 'attended' in key or 'summary' in key:
                    print(f"  {key}: {value}")
            print("=== END DEBUG ===")
            
            # Create the activity report
            activity_report = ActivityReport.objects.create(
                activity=activity,
                summary=request.POST.get('report_summary', ''),
            )
            
            # Handle file upload
            if 'report_file' in request.FILES:
                activity_report.report_file = request.FILES['report_file']
                activity_report.save()
            
            # Update attendance based on form submission - WITH ENHANCED DEBUGGING
            attendance_records = Attendance.objects.filter(activity=activity)
            print(f"DEBUG: Processing {attendance_records.count()} attendance records")
            
            present_count = 0
            absent_count = 0
            
            for attendance in attendance_records:
                attended_field = f'attended_{attendance.mentee.MenteeID}'
                # Check if the checkbox was submitted for this mentee
                if attended_field in request.POST:
                    attendance.attended = True
                    present_count += 1
                    print(f"DEBUG: ✅ {attendance.mentee.MenteeName} - MARKED AS PRESENT (checkbox found in POST)")
                else:
                    attendance.attended = False
                    absent_count += 1
                    print(f"DEBUG: ❌ {attendance.mentee.MenteeName} - MARKED AS ABSENT (checkbox NOT found in POST)")
                attendance.save()
            
            print(f"DEBUG: FINAL ATTENDANCE - Present: {present_count}, Absent: {absent_count}, Total: {attendance_records.count()}")
            
            messages.success(request, 'Activity report created successfully!')
            return redirect('activity_report')
            
        except Exception as e:
            messages.error(request, f'Error creating report: {str(e)}')
            print(f"ERROR creating report: {str(e)}")
            import traceback
            print(f"TRACEBACK: {traceback.format_exc()}")
    
    # Get attendance for this activity
    attendance = Attendance.objects.filter(activity=activity).select_related('mentee')
    
    # DEBUG: Print current attendance status
    print(f"=== DEBUG: CURRENT ATTENDANCE STATUS FOR ACTIVITY {activity_id} ===")
    for record in attendance:
        print(f"  {record.mentee.MenteeName}: attended={record.attended}")
    print(f"Total attendees: {attendance.count()}")
    print("=== END DEBUG ===")
    
    # FIXED: Ensure mentor is passed to template with profile picture
    return render(request, 'create_activity_report.html', {
        'mentor': mentor,  # This is crucial for the sidebar profile picture
        'activity': activity,
        'mentoring_session': mentoring_session,
        'attendance': attendance
    })

@login_required
def view_activity_report(request, activity_id):
    """View for mentor to view an existing activity report"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    # Get mentor with profile picture
    mentor = get_object_or_404(Mentor, user=request.user)
    
    activity = get_object_or_404(Activity, ActivityID=activity_id, PrimaryMentor=mentor)
    activity_report = get_object_or_404(ActivityReport, activity=activity)
    attendance = Attendance.objects.filter(activity=activity).select_related('mentee')
    
    return render(request, 'view_activity_report.html', {
        'mentor': mentor,  # This is crucial for the sidebar
        'activity': activity,
        'activity_report': activity_report,
        'attendance': attendance
    })

@login_required
def edit_activity_report(request, activity_id):
    """View for mentor to edit an existing activity report"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    # Get mentor with profile picture
    mentor = get_object_or_404(Mentor, user=request.user)
    
    activity = get_object_or_404(Activity, ActivityID=activity_id, PrimaryMentor=mentor)
    activity_report = get_object_or_404(ActivityReport, activity=activity)
    
    if request.method == 'POST':
        try:
            activity_report.summary = request.POST.get('report_summary', '')
            
            # Handle file upload
            if 'report_file' in request.FILES:
                activity_report.report_file = request.FILES['report_file']
            
            activity_report.save()
            
            # Update attendance
            attendance_records = Attendance.objects.filter(activity=activity)
            for attendance in attendance_records:
                attended_field = f'attended_{attendance.mentee.MenteeID}'
                if attended_field in request.POST:
                    attendance.attended = True
                else:
                    attendance.attended = False
                attendance.save()
            
            messages.success(request, 'Activity report updated successfully!')
            return redirect('activity_report')
            
        except Exception as e:
            messages.error(request, f'Error updating report: {str(e)}')
    
    attendance = Attendance.objects.filter(activity=activity).select_related('mentee')
    
    return render(request, 'edit_activity_report.html', {
        'mentor': mentor,  # This is crucial for the sidebar
        'activity': activity,
        'activity_report': activity_report,
        'attendance': attendance
    })

@login_required
def delete_activity_report(request, activity_id):
    """View for mentor to delete an activity report"""
    if request.user.role != 'mentor':
        messages.error(request, 'Access denied. Mentor role required.')
        return redirect('homepage')
    
    activity = get_object_or_404(Activity, ActivityID=activity_id, PrimaryMentor__user=request.user)
    activity_report = get_object_or_404(ActivityReport, activity=activity)
    
    if request.method == 'POST':
        activity_report.delete()
        messages.success(request, 'Activity report deleted successfully!')
    
    return redirect('activity_report')

# ===== HEAD VIEWS =====
@login_required
def head_homepage(request):
    """Head of Mentor Mentee homepage with system overview"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    # Get actual statistics
    total_mentors = Mentor.objects.count()
    total_mentees = Mentee.objects.count()
    
    # Calculate session statistics
    today = timezone.now().date()
    
    # Count completed sessions (past) - ALL activities
    completed_sessions = Activity.objects.filter(
        Date__lt=today
    ).count()
    
    # Count upcoming sessions (future) - ALL activities
    upcoming_sessions = Activity.objects.filter(
        Date__gt=today
    ).count()
    
    # Count today's sessions - ALL activities
    today_sessions = Activity.objects.filter(
        Date=today
    ).count()
    
    # Total sessions for display
    total_sessions = completed_sessions + upcoming_sessions + today_sessions

    
    # Calculate system usage (percentage of mentors with mentees)
    mentors_with_mentees = Mentor.objects.filter(CurrentMentees__gt=0).count()
    system_usage = int((mentors_with_mentees / total_mentors * 100)) if total_mentors > 0 else 0


    # --- GRAPH DATA PREPARATION ---
    
    # 1. Department Distribution (Pie Chart)
    dept_data = Mentor.objects.values('MentorDepartment').annotate(count=Count('MentorID')).order_by('-count')
    dept_labels = [item['MentorDepartment'] for item in dept_data]
    dept_counts = [item['count'] for item in dept_data]
    
    # 2. Activity Trends (Line Chart) - Last 6 months
    six_months_ago = timezone.now().date() - timedelta(days=180)
    activity_trend = Activity.objects.filter(
        Date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('Date')
    ).values('month').annotate(
        count=Count('ActivityID')
    ).order_by('month')
    
    activity_labels = [item['month'].strftime('%b %Y') for item in activity_trend]
    activity_data = [item['count'] for item in activity_trend]

    # 3. Mentee Intake Distribution (Bar Chart)
    intake_data = Mentee.objects.values('Year').annotate(count=Count('MenteeID')).order_by('Year')
    intake_labels = [str(item['Year']) for item in intake_data]
    intake_counts = [item['count'] for item in intake_data]

    # 4. Recent System Activities (for list)
    # Use CreatedAt if available (it is in Activity model)
    recent_activities_list = Activity.objects.all().order_by('-CreatedAt')[:5]

    context = {
        'user': request.user,
        'total_mentors': total_mentors,
        'total_mentees': total_mentees,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'upcoming_sessions': upcoming_sessions,
        'today_sessions': today_sessions,
        'system_usage': system_usage,
        
        # Graph Data
        'dept_labels': dept_labels,
        'dept_counts': dept_counts,
        'activity_labels': activity_labels,
        'activity_data': activity_data,
        'intake_labels': intake_labels,
        'intake_counts': intake_counts,
        
        'recent_activities': recent_activities_list,
    }
    
    return render(request, 'homepage_head.html', context)

@login_required
def manage_mentees(request):
    """View for managing mentees with proper data, normalized course names, and pagination"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    # Function to get full course name from course code
    def get_course_full_name(course_code):
        course_mapping = {
            'CS': 'Diploma in Computer Science',
            'DA': 'Diploma in Accounting',
            'DB': 'Diploma in Business Studies',
            'LH': 'Diploma in Landscape Horticulture',
            'IEP': 'Intensive English Programme',
            'CFAB': 'Certificate in Finance, Accountancy and Business',
            'Diploma in Computer Science': 'Diploma in Computer Science',
            'Diploma in Accounting': 'Diploma in Accounting',
            'Diploma in Business Studies': 'Diploma in Business Studies',
            'Diploma in Landscape Horticulture': 'Diploma in Landscape Horticulture',
            'Intensive English Programme': 'Intensive English Programme',
            'Certificate in Finance, Accountancy and Business': 'Certificate in Finance, Accountancy and Business'
        }
        return course_mapping.get(course_code, course_code)
    
    # Get all mentees with related mentor data
    mentees = Mentee.objects.all().select_related('assigned_mentor').order_by('MenteeID')
    
    # Calculate statistics (before filtering for pagination)
    active_mentees_count = mentees.filter(MenteeStatus='active').count()
    unassigned_mentees_count = mentees.filter(assigned_mentor__isnull=True).count()
    male_count = mentees.filter(MenteeGender='male').count()
    female_count = mentees.filter(MenteeGender='female').count()
    
    # Handle search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        mentees = mentees.filter(
            Q(MenteeID__icontains=search_query) |
            Q(MenteeName__icontains=search_query) |
            Q(MenteeCourse__icontains=search_query) |
            Q(assigned_mentor__MentorName__icontains=search_query)
        )
    
    # Add display course to each mentee
    for mentee in mentees:
        mentee.display_course = get_course_full_name(mentee.MenteeCourse)
    
    # PAGINATION - Get records per page from request
    per_page = request.GET.get('per_page', 10)  # Default to 10 per page
    
    try:
        per_page = int(per_page)
        # Validate per_page value
        valid_per_page_values = [10, 25, 50, 100]
        if per_page not in valid_per_page_values:
            per_page = 10
    except ValueError:
        per_page = 10
    
    # Create paginator
    paginator = Paginator(mentees, per_page)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.get_page(page_number)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page
        page_obj = paginator.page(1)
    except EmptyPage:
        # If page is out of range, deliver last page
        page_obj = paginator.page(paginator.num_pages)
    
    # Calculate upcoming sessions for sidebar badge
    today = timezone.now().date()
    upcoming_sessions = Activity.objects.filter(Date__gt=today).count()
    
    context = {
        'mentees': page_obj,  # Use page_obj instead of queryset
        'page_obj': page_obj,  # For template pagination controls
        'active_mentees_count': active_mentees_count,
        'unassigned_mentees_count': unassigned_mentees_count,
        'male_count': male_count,
        'female_count': female_count,
        'search_query': search_query,
        'per_page': per_page,  # Pass per_page value to template
        'upcoming_sessions': upcoming_sessions,
    }
    
    return render(request, 'manage_mentees.html', context)

@login_required
def add_mentee(request):
    """View for adding new mentee with user account creation"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    if request.method == 'POST':
        try:
            # Extract data from POST request
            mentee_id = request.POST.get('MenteeID')
            name = request.POST.get('MenteeName')
            course_code = request.POST.get('MenteeCourse')  # This is the short code like 'CS', 'DA', etc.
            semester = request.POST.get('MenteeSemester')
            intake_year = request.POST.get('IntakeYear')
            intake_month = request.POST.get('IntakeMonth')
            running_number = request.POST.get('RunningNumber')
            gender = request.POST.get('MenteeGender')
            email = request.POST.get('MenteeEmail')
            ic_number = request.POST.get('MenteeIC')
            
            # Validate required fields
            required_fields = {
                'MenteeID': mentee_id,
                'MenteeName': name,
                'MenteeCourse': course_code,
                'MenteeSemester': semester,
                'IntakeYear': intake_year,
                'IntakeMonth': intake_month,
                'RunningNumber': running_number,
                'MenteeGender': gender,
                'MenteeEmail': email,
                'MenteeIC': ic_number,
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            if missing_fields:
                messages.error(request, f'Missing required fields: {", ".join(missing_fields)}')
                return render(request, 'add_mentee.html')
            
            # Check if MenteeID already exists
            if Mentee.objects.filter(MenteeID=mentee_id).exists():
                messages.error(request, 'This Mentee ID already exists.')
                return render(request, 'add_mentee.html')
            
            # Check if email already exists
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'This email address is already registered.')
                return render(request, 'add_mentee.html')
            
            # Create user account
            username = mentee_id.lower()
            password = ic_number  # Use IC number as initial password
            
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                role='mentee',
                first_name=name,
                email=email,
            )
            
            # CONVERT COURSE CODE TO FULL COURSE NAME
            course_full_name = get_course_full_name(course_code)
            
            # Create mentee profile with FULL course name
            mentee = Mentee.objects.create(
                user=user,
                MenteeID=mentee_id,
                MenteeName=name,
                MenteeEmail=email,
                MenteeIC=ic_number,
                MenteeGender=gender,
                MenteeCourse=course_full_name,  # Store FULL course name, not code
                MenteeSemester=semester,
                MenteeJoinDate=date.today(),
                Year=date.today().year,
                # Set default values for other required fields
                MenteePhone="",
                MenteeAddress="",
                MenteePostcode="",
                MenteeCity="",
                MenteeState="",
                MenteeRace="",
                MenteeReligion="",
                MenteePreviousSchool="",
                MenteeFatherName="",
                MenteeFatherIC="",
                MenteeFatherOccupation="",
                MenteeFatherPhone="",
                MenteeMotherName="",
                MenteeMotherIC="",
                MenteeMotherOccupation="",
                MenteeMotherPhone="",
            )
            
            messages.success(request, f'Mentee {name} added successfully!')
            return redirect('manage_mentees')
            
        except Exception as e:
            messages.error(request, f'Error adding mentee: {str(e)}')
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error adding mentee: {str(e)}")
    
    # For GET requests, render the form
    return render(request, 'add_mentee.html')

@login_required
def view_mentee(request, mentee_id):
    """View for viewing mentee details"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    # Get the specific mentee
    mentee = get_object_or_404(Mentee, MenteeID=mentee_id)
    
    context = {
        'mentee': mentee,
    }
    
    return render(request, 'head_view_mentee.html', context)

@login_required
def edit_mentee(request, mentee_id):
    """View for editing mentee"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    mentee = get_object_or_404(Mentee, MenteeID=mentee_id)
    
    if request.method == 'POST':
        # Update mentee with form data
        try:
            mentee.MenteeName = request.POST.get('MenteeName')
            
            # Get course code from POST and convert to full name
            course_code = request.POST.get('MenteeCourse')
            course_full_name = get_course_full_name(course_code)
            mentee.MenteeCourse = course_full_name  # Store full name
            
            mentee.MenteeSemester = request.POST.get('MenteeSemester')
            mentee.MenteeGender = request.POST.get('MenteeGender')
            mentee.MenteeEmail = request.POST.get('MenteeEmail')
            mentee.MenteeStatus = request.POST.get('MenteeStatus')
            
            # Handle mentor assignment
            mentor_id = request.POST.get('assigned_mentor')
            if mentor_id:
                mentor = get_object_or_404(Mentor, MentorID=mentor_id)
                mentee.assigned_mentor = mentor
            else:
                mentee.assigned_mentor = None
            
            mentee.save()
            
            messages.success(request, f'Mentee {mentee.MenteeName} updated successfully!')
            return redirect('manage_mentees')
            
        except Exception as e:
            messages.error(request, f'Error updating mentee: {str(e)}')
    
    # Get all available mentors for the dropdown
    available_mentors = Mentor.objects.filter(CurrentMentees__lt=models.F('MaxMentees'))
    
    # Get current course code for the dropdown (convert full name back to code for form)
    current_course_code = mentee.get_course_code()
    
    context = {
        'mentee': mentee,
        'available_mentors': available_mentors,
        'current_course_code': current_course_code,
    }
    
    return render(request, 'edit_mentee.html', context)

@login_required
def delete_mentee(request, mentee_id):
    """View for deleting mentee along with associated user account and related records"""
    if request.user.role != 'head':
        messages.error(request, "Access denied. Head role required.")
        return redirect('homepage')
    
    try:
        mentee = get_object_or_404(Mentee, MenteeID=mentee_id)
        mentee_name = mentee.MenteeName
        user = mentee.user
        
        # Check if there are any related records that need to be handled
        # (Optional: You might want to handle attendance records, etc.)
        
        # Store the email for logging/messaging
        mentee_email = mentee.MenteeEmail
        
        # Delete mentee first (this won't cascade to user due to OneToOne)
        mentee.delete()
        
        # Then delete the user
        if user:
            user.delete()
            messages.success(request, f'Mentee {mentee_name} (Email: {mentee_email}) deleted successfully!')
        else:
            messages.warning(request, f'Mentee {mentee_name} deleted, but no associated user account found.')
        
    except Exception as e:
        messages.error(request, f'Error deleting mentee: {str(e)}')
        import traceback
        print(f"Error deleting mentee: {traceback.format_exc()}")
    
    return redirect('manage_mentees')

@login_required
def manage_mentors(request):
    """View for head to manage mentor records - FIXED VERSION"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    mentors = Mentor.objects.all().order_by('MentorDepartment', 'MentorID')
    
    # FIXED: Calculate current assignments using assignment model
    for mentor in mentors:
        # Get current active assignments count
        current_assignments = MentorMenteeAssignment.objects.filter(
            mentor=mentor, 
            assignment_status='active'
        ).count()
        mentor.current_assignments_count = current_assignments
        mentor.available_slots = mentor.MaxMentees - current_assignments
    
    # FIXED: Calculate statistics AFTER updating mentor objects
    mentors_with_vacancy = [m for m in mentors if m.available_slots > 0]
    total_vacancy = sum(m.available_slots for m in mentors_with_vacancy)
    
    # Calculate other statistics
    departments = Mentor.objects.values_list('MentorDepartment', flat=True).distinct()
    departments_count = departments.count()
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        mentors = mentors.filter(
            Q(MentorID__icontains=search_query) |
            Q(MentorName__icontains=search_query) |
            Q(MentorDepartment__icontains=search_query)
        )
    
    # Calculate upcoming sessions for sidebar badge
    today = timezone.now().date()
    upcoming_sessions = Activity.objects.filter(Date__gt=today).count()
    
    context = {
        'mentors': mentors,
        'search_query': search_query,
        'mentors_with_vacancy': mentors_with_vacancy,
        'total_vacancy': total_vacancy,
        'departments': departments,
        'departments_count': departments_count,
        'upcoming_sessions': upcoming_sessions,
    }
    
    return render(request, 'manage_mentors.html', context)
    
@login_required
def add_mentor(request):
    """View for head to add a new mentor"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    if request.method == 'POST':
        try:
            # Get form data
            mentor_id = request.POST.get('MentorID')
            mentor_name = request.POST.get('MentorName')
            mentor_email = request.POST.get('MentorEmail')
            mentor_phone = request.POST.get('MentorPhone')
            mentor_ic = request.POST.get('MentorIC')
            mentor_department = request.POST.get('MentorDepartment')
            max_mentees = request.POST.get('MaxMentees', 20)
            
            # Validation
            errors = []
            
            # Check if MentorID already exists
            if Mentor.objects.filter(MentorID=mentor_id).exists():
                errors.append("This Mentor ID already exists.")
            
            # Check if email already exists
            if CustomUser.objects.filter(email=mentor_email).exists():
                errors.append("This email address is already registered.")
            
            # Check if IC number already exists
            if Mentor.objects.filter(MentorIC=mentor_ic).exists():
                errors.append("This IC number is already registered.")
            
            if errors:
                for error in errors:
                    messages.error(request, error)
                return render(request, 'add_mentor.html')
            
            # Use mentor ID as username and IC as password
            username = mentor_id.lower()
            password = mentor_ic  # Use IC number as initial password
            
            # Create user account
            user = CustomUser.objects.create_user(
                username=username,
                password=password,
                role='mentor',
                first_name=mentor_name,
                email=mentor_email,
            )
            
            # Create mentor profile
            mentor = Mentor.objects.create(
                user=user,
                MentorID=mentor_id,
                MentorName=mentor_name,
                MentorEmail=mentor_email,
                MentorPhone=mentor_phone,
                MentorIC=mentor_ic,
                MentorDepartment=mentor_department,
                MaxMentees=max_mentees,
                MentorJoinDate=date.today(),
                # Set default values for other fields
                MentorAddress="",
                MentorPostcode="",
                MentorCity="",
                MentorState="",
                MentorRace="",
                MentorReligion="",
                CurrentMentees=0,
            )
            
            messages.success(request, 'Mentor Successfully Added!')
            return redirect('manage_mentors')
            
        except Exception as e:
            messages.error(request, f'Error adding mentor: {str(e)}')
            return render(request, 'add_mentor.html')
    
    return render(request, 'add_mentor.html')

@login_required
def view_mentor(request, mentor_id):
    """View for head to view mentor details"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        mentor = Mentor.objects.get(MentorID=mentor_id)
        assigned_mentees = Mentee.objects.filter(assigned_mentor=mentor)
        
        # Calculate statistics
        male_mentees = assigned_mentees.filter(MenteeGender='male').count()
        female_mentees = assigned_mentees.filter(MenteeGender='female').count()
        vacancy_rate = int((mentor.vacancy_count / mentor.MaxMentees) * 100) if mentor.MaxMentees > 0 else 0
        
        context = {
            'mentor': mentor,
            'assigned_mentees': assigned_mentees,
            'male_mentees_count': male_mentees,
            'female_mentees_count': female_mentees,
            'vacancy_rate': vacancy_rate,
        }
        
        return render(request, 'head_view_mentor.html', context)
        
    except Mentor.DoesNotExist:
        messages.error(request, f'Mentor with ID {mentor_id} not found.')
        return redirect('manage_mentors')

@login_required
def edit_mentor(request, mentor_id):
    """View for head to edit mentor details"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        mentor = Mentor.objects.get(MentorID=mentor_id)
        
        if request.method == 'POST':
            try:
                # Update mentor information
                mentor.MentorName = request.POST.get('MentorName')
                mentor.MentorEmail = request.POST.get('MentorEmail')
                mentor.MentorPhone = request.POST.get('MentorPhone')
                mentor.MentorIC = request.POST.get('MentorIC')
                mentor.MentorDepartment = request.POST.get('MentorDepartment')
                mentor.MaxMentees = request.POST.get('MaxMentees')
                mentor.MentorAddress = request.POST.get('MentorAddress')
                mentor.MentorPostcode = request.POST.get('MentorPostcode')
                mentor.MentorCity = request.POST.get('MentorCity')
                mentor.MentorState = request.POST.get('MentorState')
                mentor.MentorRace = request.POST.get('MentorRace')
                mentor.MentorReligion = request.POST.get('MentorReligion')
                
                mentor.save()
                
                # Also update the user account
                user = mentor.user
                user.first_name = mentor.MentorName
                user.email = mentor.MentorEmail
                user.save()
                
                messages.success(request, f'Mentor {mentor.MentorName} updated successfully!')
                return redirect('manage_mentors')
                
            except Exception as e:
                messages.error(request, f'Error updating mentor: {str(e)}')
        
        return render(request, 'edit_mentor.html', {'mentor': mentor})
        
    except Mentor.DoesNotExist:
        messages.error(request, f'Mentor with ID {mentor_id} not found.')
        return redirect('manage_mentors')

@login_required
def delete_mentor(request, mentor_id):
    """View for head to delete a mentor"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    if request.method == 'POST':
        try:
            mentor = Mentor.objects.get(MentorID=mentor_id)
            mentor_name = mentor.MentorName
            
            # Check if mentor has assigned mentees
            if mentor.mentee_set.exists():
                messages.error(request, f'Cannot delete {mentor_name} because they have assigned mentees. Please reassign mentees first.')
                return redirect('manage_mentors')
            
            # Delete the user account and mentor profile
            user = mentor.user
            mentor.delete()
            user.delete()
            
            messages.success(request, f'Mentor {mentor_name} deleted successfully!')
            
        except Mentor.DoesNotExist:
            messages.error(request, f'Mentor with ID {mentor_id} not found.')
    
    return redirect('manage_mentors')

    context = {
        'mentors': mentors,
        'search_query': search_query,
        'mentors_with_vacancy': mentors_with_vacancy,
        'total_vacancy': total_vacancy,
        'departments': departments,
        'departments_count': departments_count,
    }
    
    return render(request, 'manage_mentors.html', context)

@login_required
def mentor_assignments(request):
    """Main assignment dashboard with corrected counts"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    mentors = Mentor.objects.all().order_by('MentorDepartment')
    
    # Get unassigned mentees using assignment model
    assigned_mentee_ids = MentorMenteeAssignment.objects.filter(
        assignment_status='active'
    ).values_list('mentee_id', flat=True)
    unassigned_mentees = Mentee.objects.exclude(MenteeID__in=assigned_mentee_ids)
    
    # Calculate statistics with correct assignment-based counts
    mentors_with_vacancy = []
    total_vacancy = 0
    
    for mentor in mentors:
        # Get current assignments count using assignment model
        current_assignments = MentorMenteeAssignment.objects.filter(
            mentor=mentor, 
            assignment_status='active'
        ).count()
        
        # Update mentor object with correct counts
        mentor.current_assignments_count = current_assignments
        mentor.available_slots = mentor.MaxMentees - current_assignments
        
        if current_assignments < mentor.MaxMentees:
            mentors_with_vacancy.append(mentor)
            total_vacancy += mentor.available_slots
    
    # Count balanced assignments
    balanced_assignments = 0
    for mentor in mentors:
        gender_dist = mentor.get_mentee_gender_distribution()
        if gender_dist['male'] > 0 and gender_dist['female'] > 0:
            balanced_assignments += 1
    
    # Handle automatic assignment - FIXED: Now stays on the same page
    if request.method == 'POST' and 'auto_assign_smart' in request.POST:
        # Pass the request to auto_assign_smart
        assigned_count = auto_assign_smart(request)
        if assigned_count > 0:
            messages.success(request, f'Smart auto-assignment completed! {assigned_count} mentees assigned with gender balance.')
        else:
            messages.info(request, 'No mentees could be assigned automatically.')
        # Stay on the same page (mentor_assignments)
        return redirect('mentor_assignments')
    
    if request.method == 'POST' and 'auto_assign' in request.POST:
        assigned_count = auto_assign_mentees()
        if assigned_count > 0:
            messages.success(request, f'Successfully auto-assigned {assigned_count} mentees to mentors!')
        else:
            messages.info(request, 'No mentees could be auto-assigned at this time.')
        # Stay on the same page (mentor_assignments)
        return redirect('mentor_assignments')
    
    # Calculate upcoming sessions for sidebar badge
    today = timezone.now().date()
    upcoming_sessions = Activity.objects.filter(Date__gt=today).count()
    
    context = {
        'mentors': mentors,
        'unassigned_mentees': unassigned_mentees,
        'mentors_with_vacancy': mentors_with_vacancy,
        'total_vacancy': total_vacancy,
        'balanced_assignments': balanced_assignments,
        'upcoming_sessions': upcoming_sessions,
    }
    
    return render(request, 'mentor_assignments.html', context)

@login_required
def assignment_mentors_list(request):
    """Page showing all mentors for assignment"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    mentors = Mentor.objects.all().order_by('MentorDepartment', 'MentorName')
    
    # Filter by department if specified
    department_filter = request.GET.get('department', '')
    if department_filter:
        mentors = mentors.filter(MentorDepartment__icontains=department_filter)
    
    # Get unique departments for filter
    departments = Mentor.objects.values_list('MentorDepartment', flat=True).distinct()
    
    context = {
        'mentors': mentors,
        'departments': departments,
        'selected_department': department_filter,
    }
    
    return render(request, 'assignment_mentors_list.html', context)

@login_required
def assignment_mentees_list(request):
    """Page showing all unassigned mentees for assignment"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    unassigned_mentees = Mentee.objects.filter(assigned_mentor__isnull=True).order_by('MenteeCourse', 'MenteeName')
    
    # Filter by course if specified
    course_filter = request.GET.get('course', '')
    if course_filter:
        unassigned_mentees = unassigned_mentees.filter(MenteeCourse__icontains=course_filter)
    
    # Get unique courses for filter
    courses = Mentee.objects.filter(assigned_mentor__isnull=True).values_list('MenteeCourse', flat=True).distinct()
    
    context = {
        'unassigned_mentees': unassigned_mentees,
        'courses': courses,
        'selected_course': course_filter,
    }
    
    return render(request, 'assignment_mentees_list.html', context)

@login_required
def assign_mentees_to_mentor(request, mentor_id):
    """Page for assigning multiple mentees to a specific mentor - FIXED VERSION"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        mentor = Mentor.objects.get(MentorID=mentor_id)
        
        print(f"=== DEBUG: Assigning to Mentor ===")
        print(f"Mentor: {mentor.MentorName}")
        print(f"Mentor Department: {mentor.MentorDepartment}")
        
        if request.method == 'POST':
            mentee_ids = request.POST.getlist('mentee_ids')
            assigned_count = 0
            
            for mentee_id in mentee_ids:
                try:
                    mentee = Mentee.objects.get(MenteeID=mentee_id)
                    
                    # Check if mentee already has active assignment
                    active_assignment = MentorMenteeAssignment.objects.filter(
                        mentee=mentee, 
                        assignment_status='active'
                    ).first()
                    
                    if active_assignment:
                        messages.warning(request, f"Mentee {mentee.MenteeName} is already assigned to {active_assignment.mentor.MentorName}")
                        continue
                    
                    # Use the new assignment method
                    mentor.assign_mentee(mentee, assigned_by=request.user)
                    assigned_count += 1
                    print(f"✅ Successfully assigned {mentee.MenteeName} to {mentor.MentorName}")
                    
                except (Mentee.DoesNotExist, ValueError) as e:
                    messages.warning(request, f"Could not assign mentee {mentee_id}: {str(e)}")
                    print(f"❌ Assignment failed for {mentee_id}: {str(e)}")
            
            if assigned_count > 0:
                messages.success(request, f'Successfully assigned {assigned_count} mentees to {mentor.MentorName}!')
            else:
                messages.warning(request, 'No mentees were assigned. They may already be assigned to other mentors.')
            return redirect('mentor_assignments')
        
        # FIXED: Get unassigned mentees using CONSISTENT logic
        print(f"=== DEBUG: Finding Unassigned Mentees ===")
        
        # Get ALL mentees first
        all_mentees = Mentee.objects.all()
        print(f"Total mentees in system: {all_mentees.count()}")
        
        # Find unassigned mentees by checking both assignment model AND direct assignment
        unassigned_mentees = []
        
        for mentee in all_mentees:
            # Check if mentee has active assignment in assignment model
            has_active_assignment = MentorMenteeAssignment.objects.filter(
                mentee=mentee,
                assignment_status='active'
            ).exists()
            
            # Check if mentee has direct mentor assignment
            has_direct_mentor = mentee.assigned_mentor is not None
            
            # If neither exists, mentee is unassigned
            if not has_active_assignment and not has_direct_mentor:
                unassigned_mentees.append(mentee)
                print(f"UNASSIGNED: {mentee.MenteeName} ({mentee.MenteeID}) - Course: {mentee.MenteeCourse}")
            else:
                assignment_source = "assignment model" if has_active_assignment else "direct field"
                print(f"ASSIGNED: {mentee.MenteeName} - via {assignment_source}")
        
        print(f"Total unassigned mentees found: {len(unassigned_mentees)}")
        
        # Find eligible mentees for this mentor with department matching
        eligible_mentees = []
        
        for mentee in unassigned_mentees:
            required_department = get_department_for_course(mentee.MenteeCourse)
            print(f"DEBUG: {mentee.MenteeName} - Course: '{mentee.MenteeCourse}' -> Department: '{required_department}'")
            
            # Department matching logic
            if required_department and mentor.MentorDepartment:
                # Clean and normalize department names for comparison
                mentor_dept_clean = mentor.MentorDepartment.lower().strip()
                required_dept_clean = required_department.lower().strip()
                
                # Multiple matching strategies
                match_found = (
                    # Exact match
                    required_dept_clean == mentor_dept_clean or
                    # Partial match
                    required_dept_clean in mentor_dept_clean or 
                    mentor_dept_clean in required_dept_clean or
                    # Word-based match
                    any(word in mentor_dept_clean for word in required_dept_clean.split()) or
                    any(word in required_dept_clean for word in mentor_dept_clean.split()) or
                    # Common department variations
                    check_department_variations(required_dept_clean, mentor_dept_clean)
                )
                
                if match_found:
                    eligible_mentees.append(mentee)
                    print(f"DEBUG: ✅ ELIGIBLE: {mentee.MenteeName} - {required_department} matches {mentor.MentorDepartment}")
                else:
                    print(f"DEBUG: ❌ NOT ELIGIBLE: {mentee.MenteeName} - needed: {required_department}, mentor has: {mentor.MentorDepartment}")
            else:
                print(f"DEBUG: ❌ NO DEPARTMENT MAPPING: {mentee.MenteeName} - course: '{mentee.MenteeCourse}' -> {required_department}")
        
        print(f"Final eligible mentees: {len(eligible_mentees)}")
        
        # Calculate available slots based on assignment model
        current_assignments_count = MentorMenteeAssignment.objects.filter(
            mentor=mentor, 
            assignment_status='active'
        ).count()
        available_slots = mentor.MaxMentees - current_assignments_count
        
        print(f"Current assignments: {current_assignments_count}, Max: {mentor.MaxMentees}, Available: {available_slots}")
        
        # Calculate gender needs
        current_gender_dist = mentor.get_mentee_gender_distribution()
        if available_slots > 0:
            ideal_dist = mentor.get_ideal_gender_distribution(available_slots)
            male_needed = ideal_dist['male']
            female_needed = ideal_dist['female']
        else:
            male_needed = 0
            female_needed = 0
        
        # Get all unique courses from eligible mentees for the filter
        eligible_courses = list(set([mentee.MenteeCourse for mentee in eligible_mentees]))
        
        context = {
            'mentor': mentor,
            'unassigned_mentees': eligible_mentees,
            'all_unassigned': unassigned_mentees,  # For debugging
            'all_unassigned_count': len(unassigned_mentees),  # For debugging
            'available_slots': available_slots,
            'current_assignments_count': current_assignments_count,
            'gender_needs': {
                'male': male_needed,
                'female': female_needed
            },
            'department_mapping': eligible_courses,
        }
        
        return render(request, 'assign_mentees_bulk.html', context)
        
    except Mentor.DoesNotExist:
        messages.error(request, 'Mentor not found.')
        return redirect('mentor_assignments')

def check_department_variations(required_dept, mentor_dept):
    """Check for common department naming variations"""
    variations = {
        'quantitative science': ['quantitative', 'science', 'computer science', 'cs'],
        'business studies': ['business', 'studies', 'bs'],
        'accounting': ['accounting', 'account', 'acc'],
        'landscape & horticulture': ['landscape', 'horticulture', 'garden', 'lh'],
        'general studies': ['general', 'studies', 'gs', 'english']
    }
    
    for base_department, aliases in variations.items():
        if required_dept == base_department:
            return any(alias in mentor_dept for alias in aliases)
        if mentor_dept == base_department:
            return any(alias in required_dept for alias in aliases)
    
    return False

def get_department_for_course(mentee_course):
    """Map mentee course to mentor department - IMPROVED VERSION"""
    if not mentee_course:
        return None
    
    course = str(mentee_course).strip().lower()
    print(f"DEBUG: Mapping course '{mentee_course}' -> '{course}'")
    
    # Enhanced mapping with better matching
    course_to_department = {
        # Computer Science -> Quantitative Science
        'diploma in computer science': 'Quantitative Science',
        'diploma in science computer': 'Quantitative Science',
        'computer science': 'Quantitative Science',
        'science computer': 'Quantitative Science',
        'cs': 'Quantitative Science',
        'bcs': 'Quantitative Science',
        
        # Accounting -> Accounting  
        'diploma in accounting': 'Accounting',
        'accounting': 'Accounting',
        'da': 'Accounting',
        
        # Business Studies -> Business Studies
        'diploma in business studies': 'Business Studies', 
        'business studies': 'Business Studies',
        'db': 'Business Studies',
        'business': 'Business Studies',
        
        # Landscape -> Landscape & Horticulture
        'diploma in landscape': 'Landscape & Horticulture',
        'diploma in landscape and horticulture': 'Landscape & Horticulture',
        'diploma in landscape horticulture': 'Landscape & Horticulture',
        'landscape and horticulture': 'Landscape & Horticulture',
        'landscape horticulture': 'Landscape & Horticulture',
        'landscape': 'Landscape & Horticulture',
        'horticulture': 'Landscape & Horticulture',
        'lh': 'Landscape & Horticulture',
        'dlh': 'Landscape & Horticulture',
        
        # Certificate FAB -> Accounting
        'certificate in finance, accounting and business': 'Accounting',
        'certificate in finance, accountancy and business': 'Accounting',
        'cfab': 'Accounting',
        'finance': 'Accounting',
        
        # English Programme -> General Studies
        'intensive english program': 'General Studies',
        'intensive english programme': 'General Studies',
        'english program': 'General Studies',
        'english programme': 'General Studies',
        'english': 'General Studies',
        'iep': 'General Studies',
        
        # Additional variations
        'quantitative science': 'Quantitative Science',
        'general studies': 'General Studies',
        'landscape & horticulture': 'Landscape & Horticulture',
    }
    
    # Exact match
    if course in course_to_department:
        result = course_to_department[course]
        print(f"DEBUG: Exact match found: {result}")
        return result
    
    # Try partial matches
    for key, value in course_to_department.items():
        if key in course:
            result = value
            print(f"DEBUG: Partial match found: '{key}' -> {value}")
            return result
    
    # Try word-based matching
    words = course.split()
    for word in words:
        for key, value in course_to_department.items():
            if word in key.split():
                result = value
                print(f"DEBUG: Word match found: '{word}' -> {value}")
                return result
    
    print(f"DEBUG: No department mapping found for: '{mentee_course}'")
    return None

def auto_assign_smart(request=None):
    """Smart auto-assignment with gender balance consideration using assignment model"""
    assigned_count = 0
    
    # Get mentees without active assignments
    assigned_mentee_ids = MentorMenteeAssignment.objects.filter(
        assignment_status='active'
    ).values_list('mentee_id', flat=True)
    
    unassigned_mentees = Mentee.objects.exclude(MenteeID__in=assigned_mentee_ids)
    
    print(f"=== SMART AUTO-ASSIGNMENT DEBUG ===")
    print(f"Unassigned mentees: {unassigned_mentees.count()}")
    
    if not unassigned_mentees:
        print("No unassigned mentees found.")
        return 0
    
    # Group mentees by required department and gender
    mentees_by_department_gender = {}
    
    for mentee in unassigned_mentees:
        dept = get_department_for_course(mentee.MenteeCourse)
        if dept:
            if dept not in mentees_by_department_gender:
                mentees_by_department_gender[dept] = {'male': [], 'female': []}
            
            if mentee.MenteeGender == 'male':
                mentees_by_department_gender[dept]['male'].append(mentee)
            else:
                mentees_by_department_gender[dept]['female'].append(mentee)
            print(f"Added {mentee.MenteeName} ({mentee.MenteeGender}) to {dept} department")
    
    # Process each department
    for dept, gender_groups in mentees_by_department_gender.items():
        print(f"Processing department: {dept}")
        print(f"  Male mentees: {len(gender_groups['male'])}")
        print(f"  Female mentees: {len(gender_groups['female'])}")
        
        # Get available mentors in this department
        available_mentors = []
        mentors_in_dept = Mentor.objects.filter(MentorDepartment__contains=dept)
        
        for mentor in mentors_in_dept:
            # Get current assignments count using assignment model
            current_assignments = MentorMenteeAssignment.objects.filter(
                mentor=mentor, 
                assignment_status='active'
            ).count()
            available_slots = mentor.MaxMentees - current_assignments
            
            if available_slots > 0:
                # Get current gender distribution
                gender_dist = mentor.get_mentee_gender_distribution()
                
                available_mentors.append({
                    'mentor': mentor,
                    'current_male': gender_dist['male'],
                    'current_female': gender_dist['female'],
                    'available_slots': available_slots,
                    'total_current': current_assignments
                })
                print(f"  Available mentor: {mentor.MentorName} (Slots: {available_slots}, Male: {gender_dist['male']}, Female: {gender_dist['female']})")
        
        print(f"  Total available mentors: {len(available_mentors)}")
        
        if not available_mentors:
            print(f"  No available mentors in {dept} department")
            continue
        
        # Sort mentors by how balanced they are (closer to 50/50 is better)
        available_mentors.sort(key=lambda x: abs(x['current_male'] - x['current_female']))
        
        # Assign mentees with gender balance
        male_mentees = gender_groups['male'][:]
        female_mentees = gender_groups['female'][:]
        
        # Continue until no more mentees or mentors have capacity
        while (male_mentees or female_mentees) and available_mentors:
            for mentor_data in available_mentors[:]:  # Use slice copy to avoid modification during iteration
                mentor = mentor_data['mentor']
                current_male = mentor_data['current_male']
                current_female = mentor_data['current_female']
                available_slots = mentor_data['available_slots']
                
                if available_slots <= 0:
                    available_mentors.remove(mentor_data)
                    continue
                
                # Decide which gender to assign for better balance
                mentee_to_assign = None
                
                if current_male <= current_female and male_mentees:
                    # Need more males for balance
                    mentee_to_assign = male_mentees.pop(0)
                elif female_mentees:
                    # Need more females for balance
                    mentee_to_assign = female_mentees.pop(0)
                elif male_mentees:
                    # Only males left
                    mentee_to_assign = male_mentees.pop(0)
                else:
                    # No mentees left for this mentor
                    continue
                
                try:
                    # Assign using assignment model - pass assigned_by if request is available
                    if request and hasattr(request, 'user'):
                        assignment = mentor.assign_mentee(mentee_to_assign, assigned_by=request.user)
                    else:
                        # For background tasks, try to get a head user to assign as
                        head_user = CustomUser.objects.filter(role='head').first()
                        if head_user:
                            assignment = mentor.assign_mentee(mentee_to_assign, assigned_by=head_user)
                        else:
                            assignment = mentor.assign_mentee(mentee_to_assign)
                    
                    assigned_count += 1
                    
                    # Update mentor data
                    mentor_data['available_slots'] -= 1
                    if mentee_to_assign.MenteeGender == 'male':
                        mentor_data['current_male'] += 1
                    else:
                        mentor_data['current_female'] += 1
                    
                    print(f"  ✅ Assigned {mentee_to_assign.MenteeName} ({mentee_to_assign.MenteeGender}) to {mentor.MentorName}")
                    
                except ValueError as e:
                    print(f"  ❌ Could not assign {mentee_to_assign.MenteeName}: {str(e)}")
                    # Put back in the appropriate list
                    if mentee_to_assign.MenteeGender == 'male':
                        male_mentees.insert(0, mentee_to_assign)
                    else:
                        female_mentees.insert(0, mentee_to_assign)
                    break
            
            # Re-sort mentors after assignments to maintain balance priority
            available_mentors.sort(key=lambda x: abs(x['current_male'] - x['current_female']))
            
            # Remove mentors with no available slots
            available_mentors = [m for m in available_mentors if m['available_slots'] > 0]
            
            # Break if no mentors left
            if not available_mentors:
                break
    
    print(f"TOTAL ASSIGNED IN SMART ASSIGNMENT: {assigned_count}")
    return assigned_count

def auto_assign_mentees():
    """Automatically assign unassigned mentees to appropriate mentors using assignment model"""
    assigned_count = 0
    
    # Get mentees without active assignments
    unassigned_mentees = Mentee.objects.filter(
        assignments__assignment_status='active'
    ).exclude(
        assignments__isnull=False
    ).distinct()
    
    for mentee in unassigned_mentees:
        required_department = get_department_for_course(mentee.MenteeCourse)
        
        if not required_department:
            continue
            
        # Find suitable mentors with vacancy
        suitable_mentors = Mentor.objects.filter(
            MentorDepartment=required_department
        ).annotate(
            current_count=models.Count('assignments', filter=models.Q(assignments__assignment_status='active'))
        ).filter(
            current_count__lt=models.F('MaxMentees')
        ).order_by('current_count')
        
        if suitable_mentors:
            best_mentor = suitable_mentors.first()
            try:
                best_mentor.assign_mentee(mentee)
                assigned_count += 1
            except ValueError as e:
                print(f"Could not assign {mentee.MenteeName} to {best_mentor.MentorName}: {str(e)}")
    
    return assigned_count

@login_required
def assign_mentees_to_mentor(request, mentor_id):
    """Page for assigning multiple mentees to a specific mentor - FIXED VERSION"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        mentor = Mentor.objects.get(MentorID=mentor_id)
        
        print(f"=== DEBUG: Assigning to Mentor ===")
        print(f"Mentor: {mentor.MentorName}")
        print(f"Mentor Department: {mentor.MentorDepartment}")
        
        if request.method == 'POST':
            mentee_ids = request.POST.getlist('mentee_ids')
            assigned_count = 0
            assignment_ids = []  # Track assignment IDs
            
            for mentee_id in mentee_ids:
                try:
                    mentee = Mentee.objects.get(MenteeID=mentee_id)
                    # Use the new assignment method
                    assignment = mentor.assign_mentee(mentee, assigned_by=request.user)
                    assigned_count += 1
                    assignment_ids.append(assignment.assignment_id)  # Track the ID
                except (Mentee.DoesNotExist, ValueError) as e:
                    messages.warning(request, f"Could not assign mentee {mentee_id}: {str(e)}")
            
            if assigned_count > 0:
                messages.success(request, f'Successfully assigned {assigned_count} mentees to {mentor.MentorName}! Assignment IDs: {", ".join(map(str, assignment_ids))}')
            return redirect('mentor_assignments')
        
        # Get ALL unassigned mentees first
        assigned_mentee_ids = MentorMenteeAssignment.objects.filter(
            assignment_status='active'
        ).values_list('mentee_id', flat=True)
        
        unassigned_mentees = Mentee.objects.exclude(MenteeID__in=assigned_mentee_ids)
        print(f"Total unassigned mentees: {unassigned_mentees.count()}")
        
        # Find mentees that match this mentor's department
        eligible_mentees = []
        
        for mentee in unassigned_mentees:
            required_department = get_department_for_course(mentee.MenteeCourse)
            print(f"DEBUG: {mentee.MenteeName} - Course: '{mentee.MenteeCourse}' -> Department: '{required_department}'")
            
            if required_department and required_department in mentor.MentorDepartment:
                eligible_mentees.append(mentee)
                print(f"DEBUG: ✅ ELIGIBLE: {mentee.MenteeName} matches {mentor.MentorDepartment}")
            else:
                print(f"DEBUG: ❌ NOT ELIGIBLE: {mentee.MenteeName} - needed: {required_department}, mentor has: {mentor.MentorDepartment}")
        
        print(f"Final eligible mentees: {len(eligible_mentees)}")
        
        # Calculate available slots
        current_assignments = MentorMenteeAssignment.objects.filter(
            mentor=mentor,
            assignment_status='active'
        ).count()
        
        available_slots = mentor.MaxMentees - current_assignments
        
        if available_slots > 0:
            ideal_dist = mentor.get_ideal_gender_distribution(available_slots)
            male_needed = ideal_dist['male']
            female_needed = ideal_dist['female']
        else:
            male_needed = 0
            female_needed = 0
        
        # Get all unique courses from eligible mentees for the filter
        eligible_courses = list(set([mentee.MenteeCourse for mentee in eligible_mentees]))
        
        context = {
            'mentor': mentor,
            'suitable_mentees': eligible_mentees,  # Changed from 'unassigned_mentees' to 'suitable_mentees'
            'vacancy_count': available_slots,  # Changed from 'available_slots' to 'vacancy_count'
            'gender_needs': {
                'male': male_needed,
                'female': female_needed
            },
            'department_mapping': eligible_courses,
        }
        
        return render(request, 'assign_mentees.html', context)
        
    except Mentor.DoesNotExist:
        messages.error(request, 'Mentor not found.')
        return redirect('mentor_assignments')

@login_required
def quick_assign(request, mentee_id):
    """Quick assign a specific mentee to available mentors - FIXED VERSION"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        mentee = Mentee.objects.get(MenteeID=mentee_id)
        required_department = get_department_for_course(mentee.MenteeCourse)
        
        print(f"=== DEBUG QUICK ASSIGN ===")
        print(f"Mentee: {mentee.MenteeName}")
        print(f"Course: {mentee.MenteeCourse}")
        print(f"Required Department: {required_department}")
        
        if request.method == 'POST':
            mentor_id = request.POST.get('mentor_id')
            if mentor_id:
                try:
                    # Use the assignment model to assign mentee
                    mentor = Mentor.objects.get(MentorID=mentor_id)
                    mentor.assign_mentee(mentee, assigned_by=request.user)
                    messages.success(request, f'Mentee {mentee.MenteeName} assigned successfully to {mentor.MentorName}!')
                except (Mentor.DoesNotExist, ValueError) as e:
                    messages.error(request, f'Failed to assign mentee: {str(e)}')
            else:
                messages.error(request, 'Please select a mentor.')
            return redirect('mentor_assignments')
        
        # FIXED: Get available mentors using assignment model
        print(f"Finding available mentors for department: {required_department}")
        
        # Get all mentors in the required department
        department_mentors = Mentor.objects.filter(
            MentorDepartment__icontains=required_department
        ) if required_department else Mentor.objects.all()
        
        print(f"Mentors in department: {department_mentors.count()}")
        
        # Filter mentors with available capacity using assignment model
        available_mentors = []
        for mentor in department_mentors:
            # Get current active assignments count
            current_assignments = MentorMenteeAssignment.objects.filter(
                mentor=mentor, 
                assignment_status='active'
            ).count()
            
            available_slots = mentor.MaxMentees - current_assignments
            
            print(f"Mentor: {mentor.MentorName}, Current: {current_assignments}, Max: {mentor.MaxMentees}, Available: {available_slots}")
            
            if available_slots > 0:
                # Add current assignments count to mentor object for template
                mentor.CurrentMentees = current_assignments
                available_mentors.append(mentor)
        
        print(f"Available mentors found: {len(available_mentors)}")
        
        context = {
            'mentee': mentee,
            'available_mentors': available_mentors,
            'required_department': required_department,
        }
        
        return render(request, 'quick_assign.html', context)
        
    except Mentee.DoesNotExist:
        messages.error(request, 'Mentee not found.')
        return redirect('mentor_assignments')

@login_required
def bulk_reassign_mentees(request):
    """Bulk reassign mentees from one mentor to another"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('mentor_assignments')
    
    if request.method == 'POST':
        mentee_ids = request.POST.getlist('mentee_ids')
        new_mentor_id = request.POST.get('new_mentor_id')
        
        if not mentee_ids or not new_mentor_id:
            messages.error(request, 'Please select mentees and a new mentor.')
            return redirect('mentor_assignments')
        
        try:
            new_mentor = Mentor.objects.get(MentorID=new_mentor_id)
            mentees = Mentee.objects.filter(MenteeID__in=mentee_ids)
            
            # Check capacity
            if new_mentor.CurrentMentees + len(mentees) > new_mentor.MaxMentees:
                messages.error(request, f'New mentor can only accept {new_mentor.get_available_slots()} more mentees.')
                return redirect('mentor_assignments')
            
            # Reassign mentees
            for mentee in mentees:
                old_mentor = mentee.assigned_mentor
                mentee.assigned_mentor = new_mentor
                mentee.save()
                
                # Update old mentor count
                if old_mentor:
                    old_mentor.CurrentMentees = old_mentor.mentee_set.count()
                    old_mentor.save()
            
            # Update new mentor count
            new_mentor.CurrentMentees = new_mentor.mentee_set.count()
            new_mentor.save()
            
            messages.success(request, f'Successfully reassigned {len(mentees)} mentees to {new_mentor.MentorName}.')
            
        except Mentor.DoesNotExist:
            messages.error(request, 'Mentor not found.')
    
    return redirect('mentor_assignments')

@login_required
def get_mentor_assignment_data(request, mentor_id):
    """API endpoint to get mentor assignment data"""
    if request.user.role != 'head':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    try:
        mentor = Mentor.objects.get(MentorID=mentor_id)
        
        data = {
            'mentor_name': mentor.MentorName,
            'mentor_department': mentor.MentorDepartment,
            'current_mentees': mentor.CurrentMentees,
            'max_mentees': mentor.MaxMentees,
            'available_slots': mentor.get_available_slots(),
            'current_gender_distribution': mentor.get_mentee_gender_distribution(),
            'ideal_distribution': mentor.get_ideal_gender_distribution(mentor.get_available_slots())
        }
        
        return JsonResponse(data)
        
    except Mentor.DoesNotExist:
        return JsonResponse({'error': 'Mentor not found'}, status=404)

@login_required
def assignment_history(request, mentor_id=None):
    """View assignment history for a mentor or all mentors with enhanced functionality"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    print(f"DEBUG: User: {request.user}")
    print(f"DEBUG: User authenticated: {request.user.is_authenticated}")
    print(f"DEBUG: User username: {request.user.username}")
    
    # Get all assignments with related objects
    assignments = MentorMenteeAssignment.objects.all().select_related(
        'mentor', 'mentee', 'assigned_by'
    ).order_by('-assigned_date')
    
    # Apply filters
    mentor_filter = request.GET.get('mentor')
    status_filter = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if mentor_filter:
        assignments = assignments.filter(mentor__MentorID=mentor_filter)
    
    if status_filter:
        assignments = assignments.filter(assignment_status=status_filter)
    
    if date_from:
        assignments = assignments.filter(assigned_date__gte=date_from)
    
    if date_to:
        assignments = assignments.filter(assigned_date__lte=date_to)
    
    # Pagination
    paginator = Paginator(assignments, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistics
    total_assignments = assignments.count()
    active_assignments = assignments.filter(assignment_status='active').count()
    transferred_assignments = assignments.filter(assignment_status='transferred').count()
    completed_assignments = assignments.filter(assignment_status='completed').count()
    
    # Get all mentors for filter dropdown
    mentors = Mentor.objects.all().order_by('MentorName')
    
    # Get head user information
    try:
        head_user = HeadofMentorMentee.objects.get(user=request.user)
        print(f"DEBUG: Head user found: {head_user}")
    except HeadofMentorMentee.DoesNotExist:
        head_user = None
        print("DEBUG: Head user not found, creating one...")
        # Create head profile if it doesn't exist
        head_user = HeadofMentorMentee.objects.create(
            user=request.user,
            HeadofMentorMenteeID=request.user.username,
            HeadofMentorMenteeName=request.user.get_full_name() or "Head Administrator",
            HeadofMentorMenteeEmail=request.user.email or "head@example.com",
            HeadofMentorMenteePhone="",
            HeadofMentorMenteeIC="",
            HeadofMentorMenteeAddress="",
            HeadofMentorMenteePostcode="",
            HeadofMentorMenteeCity="",
            HeadofMentorMenteeState="",
            HeadofMentorMenteeRace="",
            HeadofMentorMenteeReligion="",
            HeadofMentorMenteeDepartment="",
        )
    
    context = {
        'assignments': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'is_paginated': paginator.num_pages > 1,
        'total_assignments': total_assignments,
        'active_assignments': active_assignments,
        'transferred_assignments': transferred_assignments,
        'completed_assignments': completed_assignments,
        'mentors': mentors,
        'selected_mentor': mentor_filter,
        'user': request.user,  # Ensure user is in context
        'head_user': head_user,
    }
    
    print(f"DEBUG: Context keys: {list(context.keys())}")
    return render(request, 'assignment_history.html', context)

@login_required
def assignment_details(request, assignment_id):
    """View detailed information about a specific assignment"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        assignment = MentorMenteeAssignment.objects.select_related(
            'mentor', 'mentee', 'assigned_by', 'transferred_to', 'transferred_by'
        ).get(assignment_id=assignment_id)
        
        # Get assignment history (previous assignments for this mentee)
        assignment_history = MentorMenteeAssignment.objects.filter(
            mentee=assignment.mentee
        ).exclude(id=assignment_id).order_by('-assigned_date')
        
        # Get activity statistics for this assignment
        activities_count = Activity.objects.filter(
            Mentor=assignment.mentor,
            attendance__mentee=assignment.mentee
        ).distinct().count()
        
        completed_activities = Activity.objects.filter(
            Mentor=assignment.mentor,
            attendance__mentee=assignment.mentee,
            attendance__attended=True
        ).distinct().count()
        
        attendance_rate = int((completed_activities / activities_count * 100)) if activities_count > 0 else 0
        
        context = {
            'assignment': assignment,
            'assignment_history': assignment_history,
            'activities_count': activities_count,
            'completed_activities': completed_activities,
            'attendance_rate': attendance_rate,
        }
        
        return render(request, 'assignment_details.html', context)
        
    except MentorMenteeAssignment.DoesNotExist:
        messages.error(request, 'Assignment not found.')
        return redirect('assignment_history')

@login_required
def transfer_assignment(request, assignment_id):
    """Transfer an assignment to a different mentor"""
    if request.user.role != 'head':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Access denied. Head role required.'}, status=403)
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        assignment = MentorMenteeAssignment.objects.get(assignment_id=assignment_id)
        
        if assignment.assignment_status != 'active':
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Only active assignments can be transferred.'}, status=400)
            messages.error(request, 'Only active assignments can be transferred.')
            return redirect('assignment_history')
        
        if request.method == 'POST':
            new_mentor_id = request.POST.get('new_mentor_id')
            transfer_notes = request.POST.get('transfer_notes', '')
            
            if not new_mentor_id:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Please select a new mentor.'}, status=400)
                messages.error(request, 'Please select a new mentor.')
                return redirect('transfer_assignment', assignment_id=assignment_id)
            
            try:
                new_mentor = Mentor.objects.get(MentorID=new_mentor_id)
                
                # Check if new mentor has capacity
                current_assignments = MentorMenteeAssignment.objects.filter(
                    mentor=new_mentor, 
                    assignment_status='active'
                ).count()
                
                if current_assignments >= new_mentor.MaxMentees:
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return JsonResponse({'error': f'{new_mentor.MentorName} has reached maximum capacity.'}, status=400)
                    messages.error(request, f'{new_mentor.MentorName} has reached maximum capacity.')
                    return redirect('transfer_assignment', assignment_id=assignment_id)
                
                # Create new assignment
                new_assignment = MentorMenteeAssignment.objects.create(
                    mentor=new_mentor,
                    mentee=assignment.mentee,
                    assigned_by=request.user,
                    assignment_status='active',
                    notes=f"Transferred from {assignment.mentor.MentorName}. {transfer_notes}"
                )
                
                # Mark old assignment as transferred
                assignment.assignment_status = 'transferred'
                assignment.transferred_to = new_mentor
                assignment.transferred_by = request.user
                assignment.transferred_date = timezone.now()
                assignment.notes = transfer_notes
                assignment.save()
                
                # Update mentee's assigned_mentor
                assignment.mentee.assigned_mentor = new_mentor
                assignment.mentee.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': f'Successfully transferred {assignment.mentee.MenteeName} from {assignment.mentor.MentorName} to {new_mentor.MentorName}'
                    })
                
                messages.success(request, 
                    f'Successfully transferred {assignment.mentee.MenteeName} from '
                    f'{assignment.mentor.MentorName} to {new_mentor.MentorName}'
                )
                return redirect('assignment_history')
                
            except Mentor.DoesNotExist:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': 'Selected mentor not found.'}, status=400)
                messages.error(request, 'Selected mentor not found.')
        
        # For GET requests, return available mentors data (for popup)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Get available mentors
            current_assignments_counts = MentorMenteeAssignment.objects.filter(
                assignment_status='active'
            ).values('mentor').annotate(count=models.Count('id'))
            
            mentor_capacity = {}
            for item in current_assignments_counts:
                mentor_capacity[item['mentor']] = item['count']
            
            available_mentors = []
            all_mentors = Mentor.objects.exclude(MentorID=assignment.mentor.MentorID)
            
            for mentor in all_mentors:
                current_count = mentor_capacity.get(mentor.id, 0)
                if current_count < mentor.MaxMentees:
                    available_mentors.append({
                        'id': mentor.MentorID,
                        'name': mentor.MentorName,
                        'department': mentor.MentorDepartment,
                        'available_slots': mentor.MaxMentees - current_count
                    })
            
            return JsonResponse({
                'assignment': {
                    'id': assignment.id,
                    'mentee_name': assignment.mentee.MenteeName,
                    'mentee_id': assignment.mentee.MenteeID,
                    'current_mentor_name': assignment.mentor.MentorName,
                    'current_mentor_id': assignment.mentor.MentorID,
                    'mentee_course': assignment.mentee.MenteeCourse,
                },
                'available_mentors': available_mentors
            })
        
        # Original GET request handling (for standalone page)
        # Get available mentors (excluding current mentor and those at capacity)
        current_assignments_counts = MentorMenteeAssignment.objects.filter(
            assignment_status='active'
        ).values('mentor').annotate(count=models.Count('id'))
        
        mentor_capacity = {}
        for item in current_assignments_counts:
            mentor_capacity[item['mentor']] = item['count']
        
        available_mentors = []
        all_mentors = Mentor.objects.exclude(MentorID=assignment.mentor.MentorID)
        
        for mentor in all_mentors:
            current_count = mentor_capacity.get(mentor.id, 0)
            if current_count < mentor.MaxMentees:
                available_mentors.append(mentor)
        
        context = {
            'assignment': assignment,
            'available_mentors': available_mentors,
        }
        
        return render(request, 'transfer_assignment.html', context)
        
    except MentorMenteeAssignment.DoesNotExist:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Assignment not found.'}, status=404)
        messages.error(request, 'Assignment not found.')
        return redirect('assignment_history')

@login_required
def delete_assignment(request, assignment_id):
    """View for head to delete an assignment record - ENHANCED VERSION"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    if request.method == 'POST':
        try:
            # Get the assignment
            assignment = MentorMenteeAssignment.objects.get(assignment_id=assignment_id)
            mentor_name = assignment.mentor.MentorName
            mentee_name = assignment.mentee.MenteeName
            assignment_status = assignment.assignment_status
            
            # Optional: Get deletion reason from form
            deletion_reason = request.POST.get('deletion_reason', 'No reason provided')
            
            # Handle mentee assignment cleanup for active assignments
            if assignment.assignment_status == 'active':
                if assignment.mentee.assigned_mentor == assignment.mentor:
                    assignment.mentee.assigned_mentor = None
                    assignment.mentee.save()
            
            # Optional: Log deletion details before deleting
            print(f"ASSIGNMENT DELETED: {mentor_name} - {mentee_name}")
            print(f"  Status: {assignment_status}")
            print(f"  Reason: {deletion_reason}")
            print(f"  Deleted by: {request.user}")
            print(f"  Deleted at: {timezone.now()}")
            
            # Delete the assignment
            assignment.delete()
            
            messages.success(request, 
                f'Assignment between {mentor_name} and {mentee_name} has been deleted.'
            )
            
        except MentorMenteeAssignment.DoesNotExist:
            messages.error(request, 'Assignment not found.')
        except Exception as e:
            messages.error(request, f'Error deleting assignment: {str(e)}')
    
    return redirect('assignment_history')

@login_required
def mentor_mentee_activities(request):
    """View for head to manage activities"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    # Get all activities ordered by date and time
    activities = Activity.objects.all().order_by('-Date', 'StartTime')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        activities = activities.filter(
            Q(ActivityID__icontains=search_query) |
            Q(ActivityName__icontains=search_query) |
            Q(ActivityType__icontains=search_query) |
            Q(Location__icontains=search_query)
        )
    
    # Calculate statistics for the dashboard
    total_activities = activities.count()
    
    # Get today's date for filtering
    today = timezone.now().date()
    
    # Count activities by status
    upcoming_activities = activities.filter(Date__gt=today).count()
    ongoing_activities = activities.filter(Date=today).count()
    past_activities = activities.filter(Date__lt=today).count()
    
    # Calculate total participants across all activities - FIXED: use attendance_set
    total_participants = 0
    for activity in activities:
        total_participants += activity.attendance_set.count()  # Changed from attendance to attendance_set
    
    context = {
        'activities': activities,
        'search_query': search_query,
        'total_activities': total_activities,
        'upcoming_activities': upcoming_activities,
        'ongoing_activities': ongoing_activities,
        'past_activities': past_activities,
        'total_participants': total_participants,
        'current_month': timezone.now().strftime('%B %Y'),
    }
    
    return render(request, 'mentor_mentee_activities.html', context)

@login_required
def create_activity(request):
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    mentors = Mentor.objects.all().order_by('MentorName')
    
    if request.method == 'POST':
        try:
            activity_id = request.POST.get('ActivityID')
            
            # Validate Activity ID format
            if not activity_id.startswith('A') or not activity_id[1:].isdigit() or len(activity_id) != 6:
                messages.error(request, 'Activity ID must be in format A followed by 5 digits (e.g., A00001)')
                return render(request, 'create_activity.html', {'mentors': mentors})
            
            if Activity.objects.filter(ActivityID=activity_id).exists():
                messages.error(request, f'Activity ID {activity_id} already exists. Please use a different ID.')
                return render(request, 'create_activity.html', {'mentors': mentors})
            
            # Get primary mentor (first selected) and additional mentors
            mentor_ids = request.POST.getlist('mentors')
            primary_mentor = None
            additional_mentors = []
            
            if mentor_ids:
                primary_mentor = Mentor.objects.filter(MentorID=mentor_ids[0]).first()
                if len(mentor_ids) > 1:
                    additional_mentors = Mentor.objects.filter(MentorID__in=mentor_ids[1:])
            
            # Create the activity
            activity = Activity.objects.create(
                ActivityID=activity_id,
                ActivityName=request.POST.get('ActivityName'),
                ActivityType=request.POST.get('ActivityType'),
                Description=request.POST.get('Description', ''),
                Date=request.POST.get('Date'),
                StartTime=request.POST.get('StartTime'),
                EndTime=request.POST.get('EndTime'),
                Location=request.POST.get('Location'),
                CreatedBy=request.user,
                IsMentoringSession=request.POST.get('IsMentoringSession') == 'on',
                PrimaryMentor=primary_mentor,  # Set primary mentor
            )
            
            # Add additional mentors
            if additional_mentors:
                activity.AdditionalMentors.set(additional_mentors)
            
            messages.success(request, f'Activity "{activity.ActivityName}" created successfully!')
            return redirect('mentor_mentee_activities')
            
        except Exception as e:
            messages.error(request, f'Error creating activity: {str(e)}')
    
    context = {
        'mentors': mentors,
    }
    
    return render(request, 'create_activity.html', context)

@login_required
def get_next_activity_id(request):
    """API endpoint to get the next available Activity ID"""
    if request.user.role != 'head':
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get the highest existing Activity ID
    last_activity = Activity.objects.order_by('-ActivityID').first()
    
    if last_activity:
        # Extract number from last ID and increment
        last_number = int(last_activity.ActivityID[1:])
        next_number = last_number + 1
    else:
        # Start from 1 if no activities exist
        next_number = 1
    
    # Format as A00001, A00002, etc.
    next_id = f"A{next_number:05d}"
    
    return JsonResponse({'next_id': next_id})

@login_required
def view_activity(request, activity_id):
    """View for head to view activity details"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        activity = Activity.objects.get(ActivityID=activity_id)
    except Activity.DoesNotExist:
        messages.error(request, f'Activity with ID {activity_id} not found.')
        return redirect('mentor_mentee_activities')
    
    # Get attendance records and statistics
    attendance_records = Attendance.objects.filter(activity=activity).select_related('mentee')
    total_participants = attendance_records.count()
    present_count = attendance_records.filter(attended=True).count()
    absent_count = total_participants - present_count
    attendance_rate = int((present_count / total_participants * 100)) if total_participants > 0 else 0
    
    # Get assigned mentors
    activity_mentors = []
    if activity.Mentor:
        activity_mentors = [activity.Mentor]
    
    context = {
        'activity': activity,
        'attendance_records': attendance_records,
        'total_participants': total_participants,
        'present_count': present_count,
        'absent_count': absent_count,
        'attendance_rate': attendance_rate,
        'activity_mentors': activity_mentors,
    }
    
    return render(request, 'view_activity.html', context)

@login_required
def edit_activity(request, activity_id):
    try:
        activity = Activity.objects.get(ActivityID=activity_id)
    except Activity.DoesNotExist:
        messages.error(request, f'Activity with ID {activity_id} not found.')
        return redirect('mentor_mentee_activities')
    
    if request.method == 'POST':
        try:
            # Update activity details
            activity.ActivityName = request.POST.get('ActivityName')
            activity.ActivityType = request.POST.get('ActivityType')
            activity.Description = request.POST.get('Description', '')
            activity.Date = request.POST.get('Date')
            activity.StartTime = request.POST.get('StartTime')
            activity.EndTime = request.POST.get('EndTime')
            activity.Location = request.POST.get('Location')
            activity.IsMentoringSession = request.POST.get('IsMentoringSession') == 'on'
            
            # Update mentor assignments
            mentor_ids = request.POST.getlist('mentors')
            primary_mentor = None
            additional_mentors = []
            
            if mentor_ids:
                primary_mentor = Mentor.objects.filter(MentorID=mentor_ids[0]).first()
                if len(mentor_ids) > 1:
                    additional_mentors = Mentor.objects.filter(MentorID__in=mentor_ids[1:])
            
            activity.PrimaryMentor = primary_mentor
            activity.save()
            
            # Update additional mentors
            activity.AdditionalMentors.set(additional_mentors)
            
            messages.success(request, f'Activity "{activity.ActivityName}" updated successfully!')
            return redirect('mentor_mentee_activities')
            
        except Exception as e:
            messages.error(request, f'Error updating activity: {str(e)}')
    
    mentors = Mentor.objects.all().order_by('MentorName')
    
    # Get currently assigned mentors
    all_mentors = activity.all_mentors
    
    context = {
        'activity': activity,
        'mentors': mentors,
        'activity_mentors': all_mentors,
    }
    
    return render(request, 'edit_activity.html', context)

@login_required
def delete_activity(request, activity_id):
    """View for head to delete an activity"""
    if request.user.role != 'head':
        messages.error(request, 'Access denied. Head role required.')
        return redirect('homepage')
    
    try:
        activity = Activity.objects.get(ActivityID=activity_id)
    except Activity.DoesNotExist:
        messages.error(request, f'Activity with ID {activity_id} not found.')
        return redirect('mentor_mentee_activities')
    
    if request.method == 'POST':
        try:
            activity_name = activity.ActivityName
            activity.delete()
            messages.success(request, f'Activity "{activity_name}" has been permanently deleted.')
            return redirect('mentor_mentee_activities')
        except Exception as e:
            messages.error(request, f'Error deleting activity: {str(e)}')
            return redirect('view_activity', activity_id=activity_id)
    
    # If it's a GET request, redirect to view activity page
    return redirect('view_activity', activity_id=activity_id)

def get_course_full_name(course_code):
    """Map course codes to full course names"""
    course_mapping = {
        'CS': 'Diploma in Computer Science',
        'DA': 'Diploma in Accounting', 
        'DB': 'Diploma in Business Studies',
        'LH': 'Diploma in Landscape Horticulture',
        'IEP': 'Intensive English Programme',
        'CFAB': 'Certificate in Finance, Accountancy and Business'
    }
    return course_mapping.get(course_code, course_code)