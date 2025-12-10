from django import forms
from .models import Activity, MentoringSession

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['ActivityName', 'ActivityType', 'Description', 'Date', 'StartTime', 'EndTime', 'Location']

class MentoringSessionForm(forms.ModelForm):
    class Meta:
        model = MentoringSession
        fields = ['session_type', 'topic', 'materials']