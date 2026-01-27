"""
SuperNinja Silver Deal Scanner - Application Launcher
Convenience script to run the application
"""

import sys
import os

# Add the silver_scanner directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == '__main__':
    print("🥈 SuperNinja Silver Deal Scanner Starting...")
    print("=" * 50)
    print("Dashboard will be available at: http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)