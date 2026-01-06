# Fix all Django template syntax errors in assignment_history.html
import re

file_path = r'c:\Users\User\Documents\GitHub\mmms\system\templates\assignment_history.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Add spaces around == for selected_mentor
content = content.replace('selected_mentor==mentor.MentorID', 'selected_mentor == mentor.MentorID')

# Fix 2: Add spaces around == for request.GET.status
content = content.replace("request.GET.status=='active'", "request.GET.status == 'active'")
content = content.replace("request.GET.status=='completed'", "request.GET.status == 'completed'")
content = content.replace("request.GET.status=='transferred'", "request.GET.status == 'transferred'")

# Fix 3: Merge split template tags (selected{% endif %} split across lines)
content = re.sub(
    r'\{%\s+if\s+selected_mentor\s*==\s*mentor\.MentorID\s*%\}selected\{%\s*\r?\n\s*endif\s*%\}',
    '{% if selected_mentor == mentor.MentorID %}selected{% endif %}',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('All Django template syntax errors fixed!')
