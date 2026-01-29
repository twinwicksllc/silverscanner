#!/usr/bin/env python3
"""
Script to insert the hidden_columns migration endpoint into app.py
"""
import os

# Read the migration endpoint
with open('migration_endpoint.py', 'r') as f:
    migration_code = f.read()

# Read the existing app.py
with open('app.py', 'r') as f:
    app_content = f.read()

# Find the position before @app.errorhandler(500)
marker = '@app.errorhandler(500)'

if marker in app_content:
    # Insert the migration code before the error handler
    parts = app_content.split(marker)
    new_content = parts[0] + '\n\n' + migration_code + '\n\n' + marker + parts[1]
    
    # Write the updated content
    with open('app.py', 'w') as f:
        f.write(new_content)
    
    print("✓ Migration endpoint inserted into app.py")
else:
    print("✗ Could not find @app.errorhandler(500) marker")
    exit(1)