from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('logout/', views.logout_view, name='logout'),

    # Password reset URLs
    path('password-reset/', auth_views.PasswordResetView.as_view(template_name='password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),

    # Homepage URLs
    path('homepage/mentee/', views.mentee_homepage, name='mentee_homepage'),
    path('homepage/mentor/', views.mentor_homepage, name='mentor_homepage'),
    path('homepage/head/', views.head_homepage, name='head_homepage'),

    # Mentee URLs
    path('mentee/mentor/', views.view_assigned_mentor, name='view_assigned_mentor'),
    path('mentee/schedule/', views.view_activity_schedules, name='view_activity_schedules'),
    path('mentee/profile/', views.update_personal_info, name='update_personal_info'),

    # Mentor URLs
    path('mentor/mentees/', views.view_assigned_mentees, name='view_assigned_mentees'),
    path('mentor/mentees/view/<str:mentee_id>/', views.mentor_view_mentee, name='mentor_view_mentee'),
    path('mentor/schedule/', views.mentoring_schedule, name='mentoring_schedule'),
    path('mentor/session/create/', views.create_mentoring_session, name='create_mentoring_session'),
    path('mentor/session/<str:activity_id>/complete/', views.complete_mentoring_session, name='complete_mentoring_session'),
    path('mentor/session/<str:activity_id>/delete/', views.delete_mentoring_session, name='delete_mentoring_session'),
    path('mentor/reports/', views.activity_report, name='activity_report'),
    path('mentor/reports/create/<str:activity_id>/', views.create_activity_report, name='create_activity_report'),
    path('mentor/reports/view/<str:activity_id>/', views.view_activity_report, name='view_activity_report'),
    path('mentor/reports/edit/<str:activity_id>/', views.edit_activity_report, name='edit_activity_report'),
    path('mentor/reports/delete/<str:activity_id>/', views.delete_activity_report, name='delete_activity_report'),
    path('mentor/profile/', views.mentor_update_profile, name='mentor_update_profile'), 

    # Head URLs - Mentee Management
    path('head/mentees/', views.manage_mentees, name='manage_mentees'),
    path('head/mentees/add/', views.add_mentee, name='add_mentee'),
    path('head/mentees/view/<str:mentee_id>/', views.view_mentee, name='view_mentee'),
    path('head/mentees/edit/<str:mentee_id>/', views.edit_mentee, name='edit_mentee'),
    path('head/mentees/delete/<str:mentee_id>/', views.delete_mentee, name='delete_mentee'),

    # Head URLs - Mentor Management
    path('head/mentors/', views.manage_mentors, name='manage_mentors'),
    path('head/mentors/add/', views.add_mentor, name='add_mentor'),
    path('head/mentors/view/<str:mentor_id>/', views.view_mentor, name='view_mentor'),
    path('head/mentors/edit/<str:mentor_id>/', views.edit_mentor, name='edit_mentor'),
    path('head/mentors/delete/<str:mentor_id>/', views.delete_mentor, name='delete_mentor'),

    # Head URLs - Assignment Management
    path('head/assignments/', views.mentor_assignments, name='mentor_assignments'),
    path('head/assignments/history/', views.assignment_history, name='assignment_history'),
    path('head/assignments/history/<str:mentor_id>/', views.assignment_history, name='assignment_history_mentor'),
    path('head/assignments/details/<int:assignment_id>/', views.assignment_details, name='assignment_details'),
    path('head/assignments/transfer/<int:assignment_id>/', views.transfer_assignment, name='transfer_assignment'),
    path('head/assignments/delete/<int:assignment_id>/', views.delete_assignment, name='delete_assignment'),
    path('head/assignments/mentors/', views.assignment_mentors_list, name='assignment_mentors_list'),
    path('head/assignments/mentees/', views.assignment_mentees_list, name='assignment_mentees_list'),
    path('head/assignments/assign/<str:mentor_id>/', views.assign_mentees_to_mentor, name='assign_mentees_to_mentor'),
    path('head/assignments/quick-assign/<str:mentee_id>/', views.quick_assign, name='quick_assign'),
    path('head/assignments/bulk-reassign/', views.bulk_reassign_mentees, name='bulk_reassign'),
    path('head/assignments/get-mentor-data/<str:mentor_id>/', views.get_mentor_assignment_data, name='get_mentor_data'),
    
    # Head URLs - Activity Management
    path('head/activities/', views.mentor_mentee_activities, name='mentor_mentee_activities'),
    path('head/activities/create/', views.create_activity, name='create_activity'),
    path('head/activities/view/<str:activity_id>/', views.view_activity, name='view_activity'),
    path('head/activities/edit/<str:activity_id>/', views.edit_activity, name='edit_activity'),
    path('head/activities/delete/<str:activity_id>/', views.delete_activity, name='delete_activity'),  
    path('head/activities/get-next-id/', views.get_next_activity_id, name='get_next_activity_id'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)