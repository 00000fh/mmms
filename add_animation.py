import os
import re

templates_dir = r'c:\Users\User\Documents\GitHub\mmms\system\templates'

# Animation CSS to add
animation_css = '''            overflow: hidden;
            white-space: nowrap;
            width: 0;
            animation: typing 8s ease-in-out infinite;
        }

        @keyframes typing {
            0% {
                width: 0
            }

            30% {
                width: 95px
            }

            80% {
                width: 95px
            }

            100% {
                width: 0
            }
        }'''

# All files to process (excluding login, signup, homepage_head)
all_files = [
    'view_mentees.html', 'view_activity_report.html', 'view_activity.html',
    'quick_assign.html', 'head_view_mentor.html', 'head_view_mentee.html',
    'edit_mentor.html', 'edit_mentee.html', 'edit_activity_report.html',
    'edit_activity.html', 'create_session.html', 'create_activity_report.html',
    'create_activity.html', 'assign_mentees_bulk.html', 'assign_mentees.html',
    'assignment_history.html', 'add_mentor.html', 'add_mentee.html',
    'activity_schedule.html', 'activity_report.html'
]

updated_count = 0
already_done_count = 0
error_count = 0

for filename in all_files:
    filepath = os.path.join(templates_dir, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has animation
        if '@keyframes typing' in content:
            print(f'✓ {filename} - already has animation')
            already_done_count += 1
            continue
        
        # Replace .logo-text block
        pattern = r'(\.logo-text\s*\{\s*font-size:\s*22px;\s*\})'
        replacement = f'.logo-text {{\n            font-size: 22px;\n{animation_css}'
        
        if re.search(pattern, content):
            content = re.sub(pattern, replacement, content)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            updated_count += 1
            print(f'✓ Updated {filename}')
        else:
            print(f'⚠ Pattern not found in {filename}')
            error_count += 1
    except Exception as e:
        print(f'✗ Error with {filename}: {e}')
        error_count += 1

print(f'\n=== Summary ===')
print(f'Already had animation: {already_done_count}')
print(f'Newly updated: {updated_count}')
print(f'Errors/Not found: {error_count}')
print(f'Total processed: {len(all_files)}')
