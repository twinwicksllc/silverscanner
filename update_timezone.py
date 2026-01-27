#!/usr/bin/env python3
"""Update timeago filter with timezone support"""

import re

# Read the file
with open('app.py', 'r') as f:
    content = f.read()

# Find and replace the timeago function
old_function = '''def timeago_filter(date_string):
    """Convert datetime string to 'X time ago' format"""
    if not date_string:
        return 'Never'
    
    try:
        date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        now = datetime.now(date.tzinfo)
        diff = now - date
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            return f'{int(seconds // 60)} minute{" " if int(seconds // 60) == 1 else "s"} ago'
        elif seconds < 86400:
            return f'{int(seconds // 3600)} hour{" " if int(seconds // 3600) == 1 else "s"} ago'
        elif seconds < 604800:
            return f'{int(seconds // 86400)} day{" " if int(seconds // 86400) == 1 else "s"} ago'
        else:
            return f'{int(seconds // 604800)} week{" " if int(seconds // 604800) == 1 else "s"} ago'
    except:
        return 'Unknown''''

new_function = '''def timeago_filter(date_string):
    """Convert datetime string to 'X time ago' format using user's timezone"""
    if not date_string:
        return 'Never'
    
    try:
        # Parse the datetime string (assume UTC if no timezone)
        if 'Z' in date_string or '+' in date_string:
            date = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        else:
            date = datetime.fromisoformat(date_string)
            date = date.replace(tzinfo=timezone.utc)
        
        # Get user's timezone from config
        user_tz = pytz.timezone(Config.USER_TIMEZONE)
        
        # Convert to user's timezone
        now = datetime.now(user_tz)
        date_local = date.astimezone(user_tz)
        
        diff = now - date_local
        
        seconds = diff.total_seconds()
        
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            return f'{int(seconds // 60)} minute{" " if int(seconds // 60) == 1 else "s"} ago'
        elif seconds < 86400:
            return f'{int(seconds // 3600)} hour{" " if int(seconds // 3600) == 1 else "s"} ago'
        elif seconds < 604800:
            return f'{int(seconds // 86400)} day{" " if int(seconds // 86400) == 1 else "s"} ago'
        else:
            return f'{int(seconds // 604800)} week{" " if int(seconds // 604800) == 1 else "s"} ago'
    except:
        return 'Unknown''''

content = content.replace(old_function, new_function)

# Write the file
with open('app.py', 'w') as f:
    f.write(content)

print("✓ Updated timeago filter with timezone support")