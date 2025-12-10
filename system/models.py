from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import os

def user_profile_picture_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/profile_pictures/user_<id>/<filename>
    return f'profile_pictures/user_{instance.user.id}/{filename}'

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('mentee', 'Mentee'),
        ('mentor', 'Mentor'),
        ('head', 'Head of Mentor Mentee'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    profile_picture = models.ImageField(upload_to=user_profile_picture_path, blank=True, null=True)
    email = models.EmailField(unique=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class Mentee(models.Model):
    STATUS_CHOICES = (
        ('active', 'Continue Study'),
        ('inactive', 'Not Continuing'),
        ('graduated', 'Graduated'),
    )
    
    GENDER_CHOICES = (
        ('male', 'Male'),
        ('female', 'Female'),
    )
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='mentee_profile_pictures/', null=True, blank=True)
    MenteeID = models.CharField(max_length=12, primary_key=True)
    MenteeName = models.CharField(max_length=100)
    MenteeCourse = models.CharField(max_length=100)
    MenteeSemester = models.IntegerField()
    Year = models.IntegerField()
    MenteeJoinDate = models.DateField()
    MenteeEmail = models.EmailField()
    MenteePhone = models.CharField(max_length=15)
    MenteeIC = models.CharField(max_length=15)
    MenteeAddress = models.CharField(max_length=255)
    MenteePostcode = models.CharField(max_length=10)
    MenteeCity = models.CharField(max_length=50)
    MenteeState = models.CharField(max_length=50)
    MenteeRace = models.CharField(max_length=50)
    MenteeReligion = models.CharField(max_length=50)
    MenteeGender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='male')
    MenteeStatus = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    MenteePreviousSchool = models.CharField(max_length=100)
    MenteeFatherName = models.CharField(max_length=100)
    MenteeFatherIC = models.CharField(max_length=15)
    MenteeFatherOccupation = models.CharField(max_length=100)
    MenteeFatherPhone = models.CharField(max_length=15)
    MenteeMotherName = models.CharField(max_length=100)
    MenteeMotherIC = models.CharField(max_length=15)
    MenteeMotherOccupation = models.CharField(max_length=100)
    MenteeMotherPhone = models.CharField(max_length=15)

    Sem1TargetGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem1ActualGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem2TargetGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem2ActualGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem3TargetGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem3ActualGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem4TargetGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem4ActualGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem5TargetGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem5ActualGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem6TargetGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    Sem6ActualGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    TargetCGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    CurrentCGPA = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    MenteeAcademicGoals = models.TextField(blank=True)
    MenteeStudyHabits = models.TextField(blank=True)
    MenteeSubjects = models.TextField(blank=True)
    MenteeExtracurricular = models.TextField(blank=True)
    AcademicSupportNeeds = models.TextField(blank=True)
    
    # Mentor assignment
    assigned_mentor = models.ForeignKey('Mentor', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.MenteeName

    def get_required_department(self):
        """Map mentee course to required mentor department"""
        course_mapping = {
            'Diploma in Computer Science': 'Quantitative Science',
            'Diploma in Science Computer': 'Quantitative Science',
            'Diploma in Business Studies': 'Business Studies',
            'Diploma in Accounting': 'Accounting',
            'Diploma in Landscape and Horticulture': 'Landscape & Horticulture',
            'Certificate in Finance, Accounting and Business': 'Accounting',
            'Intensive English Program': 'General Studies',
            # Add more mappings as needed
        }
        return course_mapping.get(self.MenteeCourse, 'General Studies')

    @property
    def current_assignment(self):
        try:
            return self.assignments.get(assignment_status='active')
        except MentorMenteeAssignment.DoesNotExist:
            return None
    
    # Add this method to assign to a mentor
    def assign_to_mentor(self, mentor, assigned_by=None):
        """Assign mentee to mentor using the assignment model"""
        # Deactivate any existing active assignments
        self.assignments.filter(assignment_status='active').update(assignment_status='completed')
        
        # Create new assignment
        assignment = MentorMenteeAssignment.objects.create(
            mentor=mentor,
            mentee=self,
            assigned_by=assigned_by,
            assignment_status='active'
        )
        return assignment
    
    def get_course_full_name(self):
        """Return the full course name based on course code"""
        course_mapping = {
            'CS': 'Diploma in Computer Science',
            'DA': 'Diploma in Accounting',
            'DB': 'Diploma in Business Studies',
            'LH': 'Diploma in Landscape Horticulture',
            'IEP': 'Intensive English Programme',
            'CFAB': 'Certificate in Finance, Accountancy and Business'
        }
        return course_mapping.get(self.MenteeCourse, self.MenteeCourse)

    def get_course_code(self):
        """Extract course code from full course name for form display"""
        # Simplified mapping without the complex logic
        course_to_code = {
            'Diploma in Computer Science': 'CS',
            'Diploma in Science Computer': 'CS',
            'Diploma in Accounting': 'DA',
            'Diploma in Business Studies': 'DB',
            'Diploma in Landscape Horticulture': 'LH',
            'Diploma in Landscape and Horticulture': 'LH',
            'Intensive English Programme': 'IEP',
            'Intensive English Program': 'IEP',
            'Certificate in Finance, Accountancy and Business': 'CFAB',
            'Certificate in Finance, Accounting and Business': 'CFAB'
        }
        
        return course_to_code.get(self.MenteeCourse, self.MenteeCourse)

class Mentor(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to='mentor_profile_pictures/', null=True, blank=True)
    MentorID = models.CharField(max_length=12, primary_key=True)
    MentorName = models.CharField(max_length=100)
    MentorEmail = models.EmailField()
    MentorPhone = models.CharField(max_length=15)
    MentorIC = models.CharField(max_length=15)
    MentorAddress = models.CharField(max_length=255)
    MentorPostcode = models.CharField(max_length=10)
    MentorCity = models.CharField(max_length=50)
    MentorState = models.CharField(max_length=50)
    MentorRace = models.CharField(max_length=50)
    MentorReligion = models.CharField(max_length=50)
    MentorDepartment = models.CharField(max_length=100)
    MaxMentees = models.IntegerField(default=20)
    CurrentMentees = models.IntegerField(default=0)
    MentorJoinDate = models.DateField()

    def __str__(self):
        return self.MentorName
    
    # FIXED: Remove duplicate methods and properties
    @property
    def has_vacancy(self):
        return self.current_mentees_count < self.MaxMentees
    
    @property
    def vacancy_count(self):
        return self.MaxMentees - self.current_mentees_count

    def get_ideal_gender_distribution(self, num_slots):
        """Calculate ideal gender distribution for given number of slots"""
        current_dist = self.get_mentee_gender_distribution()
        current_total = current_dist['male'] + current_dist['female']
        
        # Target is 50/50 gender ratio
        target_total = current_total + num_slots
        target_male = target_total // 2
        target_female = target_total // 2
        
        # If total is odd, add one extra to the gender that currently has fewer
        if target_total % 2 == 1:
            if current_dist['male'] <= current_dist['female']:
                target_male += 1
            else:
                target_female += 1
        
        # Calculate how many of each gender we need
        male_needed = max(0, target_male - current_dist['male'])
        female_needed = max(0, target_female - current_dist['female'])
        
        # Adjust if needed slots exceed available
        total_needed = male_needed + female_needed
        if total_needed > num_slots:
            ratio = num_slots / total_needed
            male_needed = int(male_needed * ratio)
            female_needed = int(female_needed * ratio)
            
            # Add remaining slots to whichever gender needs them
            remaining = num_slots - (male_needed + female_needed)
            if remaining > 0:
                if male_needed >= female_needed:
                    male_needed += remaining
                else:
                    female_needed += remaining
        
        return {
            'male': male_needed,
            'female': female_needed
        }

    def get_male_mentees_count(self):
        """Get count of male mentees using assignment model"""
        return self.assignments.filter(
            assignment_status='active',
            mentee__MenteeGender='male'
        ).count()
    
    def get_female_mentees_count(self):
        """Get count of female mentees using assignment model"""
        return self.assignments.filter(
            assignment_status='active',
            mentee__MenteeGender='female'
        ).count()
    
    def save(self, *args, **kwargs):
        # Auto-update CurrentMentees count when saving
        if self.MentorID:  # Only if mentor already exists
            actual_count = self.current_mentees_count
            if actual_count != self.CurrentMentees:
                self.CurrentMentees = actual_count
        self.clean()
        super().save(*args, **kwargs)

    def get_mentee_gender_distribution(self):
        """Get current gender distribution of mentees using assignment model"""
        male_count = self.get_male_mentees_count()
        female_count = self.get_female_mentees_count()
        return {'male': male_count, 'female': female_count}
    
    def get_ideal_gender_distribution(self, num_mentees):
        """Calculate ideal gender distribution for new assignments"""
        current_dist = self.get_mentee_gender_distribution()
        total_current = current_dist['male'] + current_dist['female']
        total_new = total_current + num_mentees
        
        # Aim for roughly equal distribution
        target_male = round((total_new) / 2)
        target_female = total_new - target_male
        
        needed_male = max(0, target_male - current_dist['male'])
        needed_female = max(0, target_female - current_dist['female'])
        
        return {'male': needed_male, 'female': needed_female}
    
    def clean(self):
        # Remove duplicate "Department" from department names
        if self.MentorDepartment and 'Department Department' in self.MentorDepartment:
            self.MentorDepartment = self.MentorDepartment.replace('Department Department', 'Department')
        super().clean()

    @property
    def current_assignments(self):
        """Get all active assignments"""
        return self.assignments.filter(assignment_status='active')
    
    @property
    def current_mentees_count(self):
        """Count of currently assigned mentees using assignment model"""
        return self.assignments.filter(assignment_status='active').count()
    
    def assign_mentee(self, mentee, assigned_by=None):
        """Assign a mentee to this mentor using assignment model"""
        if not self.has_vacancy:
            raise ValueError(f"Mentor {self.MentorName} has no available slots")
        
        # Check if mentee already has active assignment
        active_assignment = MentorMenteeAssignment.objects.filter(
            mentee=mentee, 
            assignment_status='active'
        ).first()
        
        if active_assignment:
            raise ValueError(f"Mentee {mentee.MenteeName} is already assigned to {active_assignment.mentor.MentorName}")
        
        # Create new assignment
        assignment = MentorMenteeAssignment.objects.create(
            mentor=self,
            mentee=mentee,
            assigned_by=assigned_by,
            assignment_status='active'
        )
        
        # Update the mentor's CurrentMentees count
        self.CurrentMentees = self.current_mentees_count
        self.save()
        
        return assignment

class HeadofMentorMentee(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    HeadofMentorMenteeID = models.CharField(max_length=12, primary_key=True)
    HeadofMentorMenteeName = models.CharField(max_length=100)
    HeadofMentorMenteeEmail = models.EmailField()
    HeadofMentorMenteePhone = models.CharField(max_length=15)
    HeadofMentorMenteeIC = models.CharField(max_length=15)
    HeadofMentorMenteeAddress = models.CharField(max_length=255)
    HeadofMentorMenteePostcode = models.CharField(max_length=10)
    HeadofMentorMenteeCity = models.CharField(max_length=50)
    HeadofMentorMenteeState = models.CharField(max_length=50)
    HeadofMentorMenteeRace = models.CharField(max_length=50)
    HeadofMentorMenteeReligion = models.CharField(max_length=50)
    HeadofMentorMenteeDepartment = models.CharField(max_length=100)

    def __str__(self):
        return self.HeadofMentorMenteeName

class Activity(models.Model):
    ACTIVITY_TYPES = (
        ('mentoring', 'Mentoring Session'),
        ('workshop', 'Workshop'),
        ('seminar', 'Seminar'),
        ('meeting', 'Meeting'),
        ('other', 'Other'),
    )
    
    ActivityID = models.CharField(max_length=20, primary_key=True)
    ActivityName = models.CharField(max_length=200)
    ActivityType = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    Description = models.TextField(blank=True)
    Date = models.DateField()
    StartTime = models.TimeField()
    EndTime = models.TimeField()
    Location = models.CharField(max_length=200)
    CreatedBy = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    CreatedAt = models.DateTimeField(auto_now_add=True)
    
    # For mentoring sessions
    IsMentoringSession = models.BooleanField(default=False)
    
    # Primary mentor (single) - keep this for backward compatibility
    PrimaryMentor = models.ForeignKey('Mentor', on_delete=models.CASCADE, null=True, blank=True, 
                                     related_name='primary_activities')
    
    # Additional mentors (multiple)
    AdditionalMentors = models.ManyToManyField('Mentor', blank=True, 
                                              related_name='additional_activities')
    
    Attendees = models.ManyToManyField(Mentee, through='Attendance')
    
    def __str__(self):
        return f"{self.ActivityName} ({self.Date})"
    
    @property
    def all_mentors(self):
        """Get all mentors (primary + additional)"""
        mentors = []
        if self.PrimaryMentor:
            mentors.append(self.PrimaryMentor)
        mentors.extend(self.AdditionalMentors.all())
        return mentors
    
    @property
    def Mentor(self):
        """Backward compatibility property - returns primary mentor"""
        return self.PrimaryMentor

class Attendance(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    mentee = models.ForeignKey(Mentee, on_delete=models.CASCADE)
    attended = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['activity', 'mentee']

class MentoringSession(models.Model):
    SESSION_TYPES = (
        ('individual', 'Individual'),
        ('group', 'Group'),
    )
    
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE)
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES, default='individual')
    topic = models.CharField(max_length=200)
    materials = models.FileField(upload_to='session_materials/', blank=True, null=True)
    completed = models.BooleanField(default=False)
    completion_date = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.topic} - {self.activity.Date}"

class ActivityReport(models.Model):
    activity = models.OneToOneField(Activity, on_delete=models.CASCADE)
    report_file = models.FileField(upload_to='activity_reports/', blank=True, null=True)
    summary = models.TextField(blank=True)
    attendance_summary = models.TextField(blank=True)  # Add attendance summary
    total_attendees = models.IntegerField(default=0)   # Add total attendees count
    present_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Report for {self.activity.ActivityName}"

    def save(self, *args, **kwargs):
        # Auto-calculate attendance statistics when saving
        if self.activity:
            attendance_records = Attendance.objects.filter(activity=self.activity)
            self.total_attendees = attendance_records.count()
            self.present_count = attendance_records.filter(attended=True).count()
            
            # Generate attendance summary
            present_mentees = attendance_records.filter(attended=True).select_related('mentee')
            absent_mentees = attendance_records.filter(attended=False).select_related('mentee')
            
            present_names = [f"{att.mentee.MenteeName} ({att.mentee.MenteeID})" for att in present_mentees]
            absent_names = [f"{att.mentee.MenteeName} ({att.mentee.MenteeID})" for att in absent_mentees]
            
            self.attendance_summary = f"Present ({self.present_count}/{self.total_attendees}): {', '.join(present_names) if present_names else 'None'}\n"
            self.attendance_summary += f"Absent ({self.total_attendees - self.present_count}/{self.total_attendees}): {', '.join(absent_names) if absent_names else 'None'}"
        
        super().save(*args, **kwargs)

class MentorMenteeAssignment(models.Model):
    """Model to manage mentor-mentee assignment relationships"""
    assignment_id = models.AutoField(primary_key=True)
    mentor = models.ForeignKey(Mentor, on_delete=models.CASCADE, related_name='assignments')
    mentee = models.ForeignKey(Mentee, on_delete=models.CASCADE, related_name='assignments')
    assigned_date = models.DateField(auto_now_add=True)
    assignment_status = models.CharField(
        max_length=20,
        choices=(
            ('active', 'Active'),
            ('completed', 'Completed'),
            ('transferred', 'Transferred'),
        ),
        default='active'
    )
    assigned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['mentor', 'mentee']
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.mentor.MentorName} - {self.mentee.MenteeName}"
    
    def save(self, *args, **kwargs):
        # Update the mentee's assigned_mentor field when assignment is created
        if self.assignment_status == 'active':
            self.mentee.assigned_mentor = self.mentor
            self.mentee.save()
        super().save(*args, **kwargs)