import re

file_path = "Cogs/Modules/moderation.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix indentation for commands
fixed_lines = []
for line in lines:
    # If line starts with exactly 12 spaces (not more), unindent by 4
    if line.startswith('            ') and not line.startswith('                ') and len(line) - len(line.lstrip()) == 12:
        fixed_lines.append(line[4:])
    else:
        fixed_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("Fixed indentation")
