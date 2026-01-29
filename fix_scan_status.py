#!/usr/bin/env python3
"""Fix the Scan Status card in index.html"""

with open('templates/index.html', 'r') as f:
    content = f.read()

# Replace the Scan Status card
old_card = '''            <div class="price-card">
                <h3>Scan Status</h3>
                <div class="value">
                    {% if is_scanning %}
                        <span class="loading"></span>
                    {% else %}
                        &#10003;
                    {% endif %}
                </div>
                <div class="subtext">
                    {% if is_scanning %}
                        Scanning...
                    {% else %}
                        Ready
                    {% endif %}
                </div>
            </div>'''

new_card = '''            <div class="price-card">
                <h3>Scan Status</h3>
                <div class="value">
                    {% if is_scanning %}
                        <span class="loading"></span>
                    {% elif scan_details %}
                        {{ scan_details.duration or 'N/A' }}
                    {% else %}
                        N/A
                    {% endif %}
                </div>
                <div class="subtext">
                    {% if is_scanning %}
                        Scanning...
                    {% elif scan_details %}
                        {{ scan_details.items_scanned }} items checked
                    {% else %}
                        Ready
                    {% endif %}
                </div>
            </div>'''

content = content.replace(old_card, new_card)

with open('templates/index.html', 'w') as f:
    f.write(content)

print("✅ Scan Status card updated successfully")