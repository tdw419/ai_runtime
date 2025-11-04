#!/usr/bin/env python3

import sys
import os
import subprocess

def launch_gui():
    """Launch the AI Daemon GUI"""
    try:
        # Add the current directory to Python path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        sys.path.insert(0, current_dir)
        
        from gui_dashboard import main
        print("🚀 Launching AI Daemon GUI...")
        main()
    except ImportError as e:
        print(f"Error: {e}")
        print("Make sure all dependencies are installed:")
        print("pip install psutil")
        sys.exit(1)

if __name__ == "__main__":
    launch_gui()
