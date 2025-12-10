from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Mentee, Mentor, HeadofMentorMentee, Activity, Attendance, MentoringSession, ActivityReport

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'is_staff', 'profile_picture')
    list_filter = ('role', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Role Information', {'fields': ('role', 'profile_picture')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Role Information', {'fields': ('role', 'profile_picture')}),
    )

@admin.register(Mentee)
class MenteeAdmin(admin.ModelAdmin):
    list_display = ('MenteeID', 'MenteeName', 'MenteeCourse', 'MenteeSemester', 'MenteeGender', 'MenteeStatus', 'assigned_mentor')
    list_filter = ('MenteeCourse', 'MenteeSemester', 'MenteeGender', 'MenteeStatus', 'assigned_mentor')
    search_fields = ('MenteeID', 'MenteeName', 'MenteeEmail')
    readonly_fields = ('user',)

@admin.register(Mentor)
class MentorAdmin(admin.ModelAdmin):
    list_display = ('MentorID', 'MentorName', 'MentorDepartment', 'MaxMentees', 'CurrentMentees', 'has_vacancy', 'vacancy_count')
    list_filter = ('MentorDepartment',)
    search_fields = ('MentorID', 'MentorName', 'MentorEmail')
    readonly_fields = ('user', 'has_vacancy', 'vacancy_count')

@admin.register(HeadofMentorMentee)
class HeadofMentorMenteeAdmin(admin.ModelAdmin):
    list_display = ('HeadofMentorMenteeID', 'HeadofMentorMenteeName', 'HeadofMentorMenteeDepartment')
    search_fields = ('HeadofMentorMenteeID', 'HeadofMentorMenteeName')
    readonly_fields = ('user',)

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('ActivityID', 'ActivityName', 'ActivityType', 'Date', 'StartTime', 'Location', 'IsMentoringSession', 'primary_mentor_display', 'additional_mentors_count', 'CreatedBy')
    list_filter = ('ActivityType', 'Date', 'IsMentoringSession', 'PrimaryMentor')  # Changed 'Mentor' to 'PrimaryMentor'
    search_fields = ('ActivityID', 'ActivityName', 'Location', 'Description')
    date_hierarchy = 'Date'
    readonly_fields = ('CreatedBy', 'CreatedAt')
    
    def primary_mentor_display(self, obj):
        """Display primary mentor in list view"""
        return obj.PrimaryMentor.MentorName if obj.PrimaryMentor else "No Primary Mentor"
    primary_mentor_display.short_description = 'Primary Mentor'
    
    def additional_mentors_count(self, obj):
        """Display count of additional mentors"""
        return obj.AdditionalMentors.count()
    additional_mentors_count.short_description = 'Additional Mentors'
    
    # Optional: If you want to filter by additional mentors too
    def get_list_filter(self, request):
        return ('ActivityType', 'Date', 'IsMentoringSession', 'PrimaryMentor')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('activity', 'mentee', 'attended')
    list_filter = ('attended', 'activity', 'mentee')
    search_fields = ('activity__ActivityName', 'mentee__MenteeName')

@admin.register(MentoringSession)
class MentoringSessionAdmin(admin.ModelAdmin):
    list_display = ('activity', 'session_type', 'topic', 'completed', 'completion_date')
    list_filter = ('session_type', 'completed')
    search_fields = ('topic', 'activity__ActivityName')
    readonly_fields = ('completion_date',)

@admin.register(ActivityReport)
class ActivityReportAdmin(admin.ModelAdmin):
    list_display = ('activity', 'created_at', 'updated_at')
    search_fields = ('activity__ActivityName', 'summary')
    readonly_fields = ('created_at', 'updated_at')