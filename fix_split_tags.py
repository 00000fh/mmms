import re

file_path = r'c:\Users\User\Documents\GitHub\mmms\system\templates\assignment_history.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all patterns where icon tags are split across lines
# Pattern: <i class="fas fa-check"\n...style="margin-left: auto;"></i>{% endif %}
content = re.sub(
    r'<i class="fas fa-check"\s*\n\s*style="margin-left: auto;"></i>{% endif %}',
    '<i class="fas fa-check" style="margin-left: auto;"></i>{% endif %}',
    content
)

# Pattern: </i>{%\n...endif %}
content = re.sub(
    r'</i>{%\s*\n\s*endif %}',
    '</i>{% endif %}',
    content
)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all split template tags!")
