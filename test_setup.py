#!/usr/bin/env python3
"""
Test script to validate the Chrome Remote Control setup
"""

import sys
import subprocess
import shutil
from pathlib import Path

def test_python_requirements():
    """Test Python version and basic imports"""
    print("=== Testing Python Requirements ===")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    if sys.version_info < (3, 11):
        print("ERROR: Python 3.11+ is required")
        return False
    
    # Test imports
    try:
        import pychrome
        print(f"✓ pychrome imported successfully (version: {getattr(pychrome, '__version__', 'unknown')})")
    except ImportError as e:
        print(f"✗ Failed to import pychrome: {e}")
        print("  Fix: Install with 'uv add pychrome' or 'pip install pychrome'")
        return False
    
    try:
        import flask
        print(f"✓ flask imported successfully (version: {flask.__version__})")
    except ImportError as e:
        print(f"✗ Failed to import flask: {e}")
        print("  Fix: Install with 'uv add flask' or 'pip install flask'")
        return False
    
    return True

def test_chrome_availability():
    """Test Chrome/Chromium availability"""
    print("\n=== Testing Chrome/Chromium Availability ===")
    
    executables = [
        'chromium-browser',
        'chromium',
        'google-chrome',
        'google-chrome-stable',
    ]
    
    found_chrome = None
    for exe in executables:
        path = shutil.which(exe)
        if path:
            print(f"✓ Found {exe} at {path}")
            found_chrome = exe
            break
        else:
            print(f"✗ {exe} not found")
    
    if not found_chrome:
        print("\nERROR: No Chrome/Chromium executable found!")
        print("Install Chrome or Chromium:")
        print("  Ubuntu/Debian: sudo apt install chromium-browser")
        print("  Or: sudo apt install google-chrome-stable")
        return False
    
    return True

def test_display_environment():
    """Test display environment"""
    print("\n=== Testing Display Environment ===")
    
    import os
    display = os.environ.get('DISPLAY')
    if display:
        print(f"✓ DISPLAY environment variable set: {display}")
    else:
        print("⚠ DISPLAY environment variable not set")
        print("  This might be okay for headless setups")
    
    # Test specific displays for dual setup
    if shutil.which('xdpyinfo'):
        dual_displays = [':0.0', ':0.1']
        working_displays = []
        
        for test_display in dual_displays:
            try:
                result = subprocess.run(['xdpyinfo', '-display', test_display], 
                                      capture_output=True, timeout=5)
                if result.returncode == 0:
                    print(f"✓ Display {test_display} is accessible")
                    working_displays.append(test_display)
                else:
                    print(f"✗ Display {test_display} is not accessible")
            except Exception as e:
                print(f"⚠ Could not test display {test_display}: {e}")
        
        if len(working_displays) >= 2:
            print(f"✓ Dual display setup detected: {working_displays}")
        elif len(working_displays) == 1:
            print(f"⚠ Only single display detected: {working_displays[0]}")
            print("  Chrome instances will both use the same screen")
        else:
            print("⚠ No displays detected - Chrome may not start properly")
    else:
        print("⚠ xdpyinfo not available (install x11-utils to test displays)")
        print("  Will assume :0.0 and :0.1 are available")
    
    return True

def test_network_ports():
    """Test if required ports are available"""
    print("\n=== Testing Network Ports ===")
    
    import socket
    ports = [9222, 9223]
    
    for port in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                print(f"⚠ Port {port} is already in use")
            else:
                print(f"✓ Port {port} is available")
        except Exception as e:
            print(f"⚠ Could not test port {port}: {e}")
    
    return True

def main():
    """Run all tests"""
    print("Chrome Remote Control - Setup Validation")
    print("=" * 50)
    
    all_good = True
    
    all_good &= test_python_requirements()
    all_good &= test_chrome_availability()
    all_good &= test_display_environment()
    all_good &= test_network_ports()
    
    print("\n" + "=" * 50)
    if all_good:
        print("✓ All tests passed! The application should work.")
        print("\nTo run the application:")
        print("  python src/main.py")
    else:
        print("✗ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == '__main__':
    main()
