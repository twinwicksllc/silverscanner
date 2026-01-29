#!/usr/bin/env python3
"""Fix the Scan Status card in index.html"""

with open('templates/index.html', 'r') as f:
    lines = f.readlines()

# Find and replace lines 79-94
new_lines = []
i = 0
while i < len(lines):
    if i == 78 and 'Scan Status' in lines[i+1]:
        # Skip lines 79-94 (old card)
        i += 16
        # Add new card
        new_lines.extend([
            '            <div class="price-card">\n',
            '                <h3>Scan Status</h3>\n',
            '                <div class="value">\n',
            '                    {% if is_scanning %}\n',
            '                        <span class="loading"></span>\n',
            '                    {% elif scan_details %}\n',
            "                        {{ scan_details.duration or 'N/A' }}\n",
            '                    {% else %}\n',
            '                        N/A\n',
            '                    {% endif %}\n',
            '                </div>\n',
            '                <div class="subtext">\n',
            '                    {% if is_scanning %}\n',
            '                        Scanning...\n',
            '                    {% elif scan_details %}\n',
            "                        {{ scan_details.items_scanned }} items checked\n",
            '                    {% else %}\n',
            '                        Ready\n',
            '                    {% endif %}\n',
            '                </div>\n',
            '            </div>\n'
        ])
    else:
        new_lines.append(lines[i])
        i += 1

with open('templates/index.html', 'w') as f:
    f.writelines(new_lines)

print("✅ Scan Status card updated successfully")