#!/usr/bin/env python3
"""Add missing form element to settings.html"""

with open('templates/settings.html', 'r') as f:
    content = f.read()

# Find the settings-page div and add the form after it
old_section = '''        <div class="settings-page">
            <h1>&#9881;&#65039; Scanner Settings</h1>'''

new_section = '''        <div class="settings-page">
            <form id="settings-form" method="POST" action="/api/settings">
            <h1>&#9881;&#65039; Scanner Settings</h1>'''

content = content.replace(old_section, new_section)

# Find the section before the action buttons and close the form
old_actions = '''            <!-- Action Buttons -->
            <div class="settings-actions">
                <button type="submit" form="settings-form" class="btn btn-primary">'''

new_actions = '''            <!-- Action Buttons -->
            <div class="settings-actions">
                <button type="submit" class="btn btn-primary">'''

content = content.replace(old_actions, new_actions)

# Close the form after the Configuration Status section
old_status_end = '''                {% endif %}
            </section>
        </div>
    </main>'''

new_status_end = '''                {% endif %}
            </section>
            </form>
        </div>
    </main>'''

content = content.replace(old_status_end, new_status_end)

with open('templates/settings.html', 'w') as f:
    f.write(content)

print("✅ Settings form added successfully")