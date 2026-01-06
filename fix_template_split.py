import re

# Read the file
file_path = r'c:\Users\User\Documents\GitHub\mmms\system\templates\assignment_history.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix ALL patterns where {% endif %} is split across lines
# Pattern 1: {%\nendif %}
content = re.sub(r'{%\s*\n\s*endif\s*%}', '{% endif %}', content)

# Pattern 2: {% endif\n%}
content = re.sub(r'{%\s*endif\s*\n\s*%}', '{% endif %}', content)

# Pattern 3: </i>{%\nendif %}
content = re.sub(r'</i>{%\s*\n\s*endif\s*%}', '</i>{% endif %}', content)

# Pattern 4: ></i>{%\nendif %}  
content = re.sub(r'></i>{%\s*\n\s*endif\s*%}', '></i>{% endif %}', content)

# Pattern 5: This catches the exact pattern showing in the file
content = re.sub(
    r'<i class="fas fa-check" style="margin-left: auto;"></i>{%\s*\n\s*endif %}',
    '<i class="fas fa-check" style="margin-left: auto;"></i>{% endif %}',
    content
)

# Pattern 6: icon tag split across lines (more general)
content = re.sub(
    r'<i class="fas fa-check"\s*\n\s*style="margin-left: auto;"></i>{% endif %}',
    '<i class="fas fa-check" style="margin-left: auto;"></i>{% endif %}',
    content
)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed all split template tags!")

# Find any remaining issues
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("\nChecking for remaining unclosed if tags...")
for i, line in enumerate(lines, 1):
    if '{%' in line and 'endif' not in line and 'endfor' not in line:
        # Check if the tag is complete on this line
        if line.count('{%') != line.count('%}'):
            print(f"  Line {i}: {line.strip()[:80]}")
