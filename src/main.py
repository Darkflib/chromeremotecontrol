#!/usr/bin/env python3
"""
Dual Display Controller for Raspberry Pi using Chrome Remote Debugging
Requires: pip install pychrome flask
"""

import subprocess
import time
import os
import signal
import sys
import shutil
from pathlib import Path

try:
    import pychrome
except ImportError:
    print("ERROR: pychrome not installed. Run: pip install pychrome")
    sys.exit(1)

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("ERROR: flask not installed. Run: pip install flask")
    sys.exit(1)

app = Flask(__name__)

class DisplayController:
    def __init__(self, force_displays=None):
        self.browsers = {}
        self.chrome_processes = {}
        self.chrome_executable = self._find_chrome_executable()
        self.force_displays = force_displays  # Allow manual override
        
    def _find_chrome_executable(self):
        """Find available Chrome/Chromium executable"""
        executables = [
            'chromium-browser',
            'chromium',
            'google-chrome',
            'google-chrome-stable',
            '/usr/bin/chromium-browser',
            '/usr/bin/chromium',
            '/usr/bin/google-chrome',
            '/snap/bin/chromium'
        ]
        
        for exe in executables:
            if shutil.which(exe):
                print(f"Found Chrome executable: {exe}")
                return exe
        
        raise RuntimeError("No Chrome/Chromium executable found. Please install Chrome or Chromium.")
    
    def _get_monitor_layout(self):
        """Get monitor layout information from xrandr"""
        monitors = []
        
        try:
            result = subprocess.run(['xrandr'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'connected' in line and '+' in line:
                        # Parse lines like: "HDMI-1 connected primary 1920x1080+1920+0"
                        parts = line.split()
                        if len(parts) >= 3:
                            name = parts[0]
                            if 'primary' in parts:
                                geometry = parts[3]  # Skip 'primary'
                            else:
                                geometry = parts[2]
                            
                            # Parse geometry: 1920x1080+1920+0
                            if 'x' in geometry and '+' in geometry:
                                try:
                                    # Split on '+' to get resolution and position
                                    res_pos = geometry.split('+')
                                    resolution = res_pos[0]  # 1920x1080
                                    x_offset = int(res_pos[1]) if len(res_pos) > 1 else 0
                                    y_offset = int(res_pos[2]) if len(res_pos) > 2 else 0
                                    
                                    width, height = map(int, resolution.split('x'))
                                    
                                    monitors.append({
                                        'name': name,
                                        'width': width,
                                        'height': height,
                                        'x': x_offset,
                                        'y': y_offset
                                    })
                                    print(f"Found monitor: {name} at {width}x{height}+{x_offset}+{y_offset}")
                                except (ValueError, IndexError) as e:
                                    print(f"Could not parse monitor geometry {geometry}: {e}")
                
            if not monitors:
                print("No monitors detected via xrandr, using default layout")
                # Default dual monitor layout
                monitors = [
                    {'name': 'default-1', 'width': 1920, 'height': 1080, 'x': 0, 'y': 0},
                    {'name': 'default-2', 'width': 1920, 'height': 1080, 'x': 1920, 'y': 0}
                ]
                
        except Exception as e:
            print(f"Error getting monitor layout: {e}")
            # Fallback to default
            monitors = [
                {'name': 'fallback-1', 'width': 1920, 'height': 1080, 'x': 0, 'y': 0},
                {'name': 'fallback-2', 'width': 1920, 'height': 1080, 'x': 1920, 'y': 0}
            ]
        
        print(f"Monitor layout: {monitors}")
        return monitors
    
    def _get_available_displays(self):
        """Check what displays are available"""
        # If displays are forced via configuration, use them
        if self.force_displays:
            print(f"Using forced display configuration: {self.force_displays}")
            return self.force_displays
        
        # For extended desktop setups, we use the same display but different positioning
        monitors = self._get_monitor_layout()
        
        if len(monitors) >= 2:
            print("Detected extended desktop with multiple monitors")
            print("Will use window positioning for dual display setup")
            return [':0', ':0']  # Same display, different positioning
        else:
            print("Single monitor detected or extended desktop mode")
            return [':0']
        
    def start_chrome_instances(self):
        """Start Chrome instances for each display"""
        try:
            # Kill any existing Chrome processes
            print("Cleaning up existing Chrome processes...")
            subprocess.run(['pkill', '-f', self.chrome_executable.split('/')[-1]], check=False)
            time.sleep(2)
            
            # Get available displays
            displays = self._get_available_displays()
            
            # Clean up temp directories
            temp_dirs = ['/tmp/chrome_display1', '/tmp/chrome_display2']
            for temp_dir in temp_dirs:
                if Path(temp_dir).exists():
                    subprocess.run(['rm', '-rf', temp_dir], check=False)
            
            # Get monitor layout for positioning
            if hasattr(self, '_manual_positions') and self._manual_positions:
                monitors = self._manual_positions
                print(f"Using manual monitor positions: {monitors}")
            else:
                monitors = self._get_monitor_layout()
            
            # Start Chrome instances - use positioning for extended desktop
            ports = [9222, 9223]
            display_ids = [1, 2]
            
            for i, (display_id, port) in enumerate(zip(display_ids, ports)):
                display = displays[i] if i < len(displays) else displays[0]
                
                # Get monitor positioning
                if i < len(monitors):
                    monitor = monitors[i]
                    window_pos_x = monitor['x']
                    window_pos_y = monitor['y']
                    window_width = monitor['width']
                    window_height = monitor['height']
                    monitor_name = monitor.get('name', f'monitor-{i+1}')
                else:
                    # Fallback positioning
                    window_pos_x = i * 1920
                    window_pos_y = 0
                    window_width = 1920
                    window_height = 1080
                    monitor_name = f"monitor-{i+1}"
                
                print(f"Starting Chrome instance {display_id} on {monitor_name}")
                print(f"  Display: {display}, Position: {window_pos_x},{window_pos_y}, Size: {window_width}x{window_height}")
                
                cmd = [
                    self.chrome_executable,
                    '--kiosk',
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-gpu',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-extensions',
                    '--disable-dev-shm-usage',
                    f'--window-position={window_pos_x},{window_pos_y}',
                    f'--window-size={window_width},{window_height}',
                    f'--remote-debugging-port={port}',
                    f'--user-data-dir=/tmp/chrome_display{display_id}',
                    f'--display={display}',
                    'about:blank'
                ]
                
                # Start Chrome process
                env = os.environ.copy()
                try:
                    process = subprocess.Popen(
                        cmd, 
                        env=env, 
                        stdout=subprocess.DEVNULL, 
                        stderr=subprocess.PIPE
                    )
                    self.chrome_processes[display_id] = process
                    print(f"Chrome process {display_id} started with PID {process.pid}")
                except Exception as e:
                    print(f"Failed to start Chrome instance {display_id}: {e}")
                    continue
            
            if not self.chrome_processes:
                raise RuntimeError("Failed to start any Chrome instances")
            
            # Wait for Chrome to start
            print("Waiting for Chrome instances to initialize...")
            time.sleep(5)
            
            # Connect to Chrome instances
            for display_id, port in zip(display_ids, ports):
                if display_id not in self.chrome_processes:
                    continue
                    
                try:
                    print(f"Connecting to Chrome instance {display_id} on port {port}")
                    browser = pychrome.Browser(url=f"http://127.0.0.1:{port}")
                    
                    # Wait for Chrome to be ready
                    max_retries = 10
                    for attempt in range(max_retries):
                        try:
                            tabs = browser.list_tab()
                            if tabs:
                                break
                        except Exception:
                            if attempt < max_retries - 1:
                                time.sleep(1)
                                continue
                            raise
                    
                    if not tabs:
                        raise RuntimeError(f"No tabs available for display {display_id}")
                    
                    # Get the first tab
                    tab = tabs[0]
                    
                    # Start the tab
                    tab.start()
                    
                    # Enable necessary domains
                    tab.Page.enable()
                    tab.Runtime.enable()
                    
                    self.browsers[display_id] = tab
                    print(f"Connected to Chrome instance {display_id} successfully")
                    
                except Exception as e:
                    print(f"Error connecting to Chrome instance {display_id}: {e}")
                    # Don't fail completely, continue with other instances
                    continue
            
            if not self.browsers:
                raise RuntimeError("Failed to connect to any Chrome instances")
            
            print(f"Successfully started {len(self.browsers)} Chrome instance(s)")
            
        except Exception as e:
            print(f"Error in start_chrome_instances: {e}")
            self.cleanup()
            raise
    
    def navigate_to_url(self, display_id, url):
        """Navigate a display to a specific URL"""
        try:
            if display_id not in self.browsers:
                return False, "Display not found"
            
            tab = self.browsers[display_id]
            tab.Page.navigate(url=url)
            return True, "Navigation successful"
            
        except Exception as e:
            return False, f"Navigation failed: {str(e)}"
    
    def refresh_display(self, display_id):
        """Refresh a display"""
        try:
            if display_id not in self.browsers:
                return False, "Display not found"
            
            tab = self.browsers[display_id]
            tab.Page.reload()
            return True, "Refresh successful"
            
        except Exception as e:
            return False, f"Refresh failed: {str(e)}"
    
    def get_current_url(self, display_id):
        """Get current URL of a display"""
        try:
            if display_id not in self.browsers:
                return None, "Display not found"
            
            tab = self.browsers[display_id]
            # Execute JavaScript to get current URL
            result = tab.Runtime.evaluate(expression="window.location.href")
            return result['result']['value'], "Success"
            
        except Exception as e:
            return None, f"Failed to get URL: {str(e)}"
    
    def cleanup(self):
        """Clean up Chrome processes"""
        if hasattr(self, '_cleaning_up') and self._cleaning_up:
            return  # Avoid recursion
        
        self._cleaning_up = True
        print("Cleaning up Chrome processes...")
        
        # Close browser connections
        for display_id, tab in self.browsers.items():
            try:
                print(f"Stopping tab for display {display_id}")
                tab.stop()
            except Exception as e:
                print(f"Error stopping tab {display_id}: {e}")
        
        # Kill Chrome processes
        for display_id, process in self.chrome_processes.items():
            try:
                if process.poll() is None:  # Process still running
                    print(f"Terminating Chrome process {display_id} (PID: {process.pid})")
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        print(f"Force killing Chrome process {display_id}")
                        process.kill()
                        try:
                            process.wait(timeout=2)
                        except subprocess.TimeoutExpired:
                            pass
            except Exception as e:
                print(f"Error stopping Chrome process {display_id}: {e}")
        
        # Additional cleanup - kill any remaining Chrome processes
        try:
            subprocess.run(['pkill', '-f', 'chrome'], check=False, timeout=5)
            subprocess.run(['pkill', '-f', 'chromium'], check=False, timeout=5)
        except Exception:
            pass
        
        # Clean up temp directories
        temp_dirs = ['/tmp/chrome_display1', '/tmp/chrome_display2']
        for temp_dir in temp_dirs:
            try:
                subprocess.run(['rm', '-rf', temp_dir], check=False, timeout=5)
            except Exception:
                pass
        
        # Clear internal state
        self.browsers.clear()
        self.chrome_processes.clear()
        print("Cleanup completed")
        self._cleaning_up = False

# Global controller instance
controller = None

@app.route('/start', methods=['POST'])
def start_displays():
    """Start the Chrome instances"""
    global controller
    try:
        if controller is None:
            # Use default dual display configuration if starting via API
            controller = DisplayController(force_displays=[':0.0', ':0.1'])
        controller.start_chrome_instances()
        return jsonify({'status': 'success', 'message': 'Displays started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/display/<int:display_id>/goto', methods=['POST'])
def goto_url(display_id):
    """Navigate display to URL"""
    global controller
    if controller is None:
        return jsonify({'status': 'error', 'message': 'Controller not initialized. Call /start first'}), 400
        
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': 'URL required'}), 400
    
    success, message = controller.navigate_to_url(display_id, data['url'])
    status_code = 200 if success else 500
    return jsonify({'status': 'success' if success else 'error', 'message': message}), status_code

@app.route('/display/<int:display_id>/refresh', methods=['POST'])
def refresh_display(display_id):
    """Refresh display"""
    global controller
    if controller is None:
        return jsonify({'status': 'error', 'message': 'Controller not initialized. Call /start first'}), 400
        
    success, message = controller.refresh_display(display_id)
    status_code = 200 if success else 500
    return jsonify({'status': 'success' if success else 'error', 'message': message}), status_code

@app.route('/display/<int:display_id>/current', methods=['GET'])
def get_current_url(display_id):
    """Get current URL of display"""
    global controller
    if controller is None:
        return jsonify({'status': 'error', 'message': 'Controller not initialized. Call /start first'}), 400
        
    url, message = controller.get_current_url(display_id)
    if url:
        return jsonify({'status': 'success', 'url': url})
    else:
        return jsonify({'status': 'error', 'message': message}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get status of all displays"""
    global controller
    if controller is None:
        return jsonify({
            'status': 'inactive',
            'message': 'Controller not initialized',
            'displays': {}
        })
    
    status = {}
    for display_id in [1, 2]:
        if display_id in controller.browsers:
            url, message = controller.get_current_url(display_id)
            status[f'display_{display_id}'] = {
                'url': url,
                'status': 'active' if url else 'error',
                'message': message if not url else 'OK'
            }
        else:
            status[f'display_{display_id}'] = {
                'url': None,
                'status': 'inactive',
                'message': 'Display not started'
            }
    
    return jsonify({
        'status': 'success',
        'active_displays': len(controller.browsers) if controller else 0,
        'displays': status
    })

@app.route('/stop', methods=['POST'])
def stop_displays():
    """Stop all displays"""
    global controller
    if controller:
        controller.cleanup()
    return jsonify({'status': 'success', 'message': 'Displays stopped'})

@app.route('/', methods=['GET'])
def index():
    """Basic status page"""
    return jsonify({
        'name': 'Chrome Remote Control Display Controller',
        'status': 'running',
        'endpoints': {
            'POST /start': 'Start Chrome instances',
            'POST /display/<id>/goto': 'Navigate display to URL (JSON: {"url": "..."})',
            'POST /display/<id>/refresh': 'Refresh display',
            'GET /display/<id>/current': 'Get current URL',
            'GET /status': 'Get status of all displays',
            'POST /stop': 'Stop all displays'
        }
    })

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print('\nShutdown signal received...')
    global controller
    if controller:
        try:
            controller.cleanup()
        except Exception as e:
            print(f"Error during cleanup: {e}")
    print('Exiting...')
    os._exit(0)  # Force exit to avoid recursion

if __name__ == '__main__':
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Chrome Remote Control Display Controller')
    parser.add_argument('--displays', 
                       nargs='+', 
                       default=[':0.0', ':0.1'],
                       help='Specify displays to use (default: :0.0 :0.1)')
    parser.add_argument('--single-display', 
                       action='store_true',
                       help='Use single display mode')
    parser.add_argument('--monitor-layout',
                       choices=['extended', 'separate-screens', 'auto'],
                       default='auto',
                       help='Monitor layout mode (default: auto)')
    parser.add_argument('--positions',
                       nargs=2,
                       metavar=('POS1', 'POS2'),
                       help='Manual positioning: --positions "0,0,1920,1080" "1920,0,1920,1080"')
    
    args = parser.parse_args()
    
    # Configure displays and positioning
    if args.single_display:
        force_displays = [':0']
        positioning_mode = 'single'
    elif args.monitor_layout == 'extended':
        force_displays = [':0', ':0']  # Same display, different positioning
        positioning_mode = 'extended'
    elif args.monitor_layout == 'separate-screens':
        force_displays = args.displays
        positioning_mode = 'separate'
    else:
        force_displays = args.displays
        positioning_mode = 'auto'
    
    # Parse manual positions if provided
    manual_positions = None
    if args.positions:
        try:
            manual_positions = []
            for pos in args.positions:
                x, y, w, h = map(int, pos.split(','))
                manual_positions.append({'x': x, 'y': y, 'width': w, 'height': h})
        except (ValueError, IndexError):
            print("Error: Invalid position format. Use: x,y,width,height")
            sys.exit(1)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=== Chrome Remote Control Display Controller ===")
    print(f"Target displays: {force_displays}")
    print(f"Monitor layout: {positioning_mode}")
    if manual_positions:
        print(f"Manual positions: {manual_positions}")
    print("Starting display controller...")
    
    try:
        # Check dependencies and system requirements
        controller = DisplayController(force_displays=force_displays)
        
        # Set manual positions if provided
        if manual_positions:
            controller._manual_positions = manual_positions
        
        # Auto-start displays on startup
        controller.start_chrome_instances()
        
        print("Display controller ready!")
        print("Available endpoints:")
        print("  GET  / - Status and endpoint list")
        print("  POST /start - Start Chrome instances")
        print("  POST /display/<id>/goto - Navigate display to URL")
        print("  POST /display/<id>/refresh - Refresh display")
        print("  GET  /display/<id>/current - Get current URL")
        print("  GET  /status - Get status of all displays")
        print("  POST /stop - Stop all displays")
        print(f"Server starting on http://0.0.0.0:5000")
        
        # Start Flask app
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
        
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
    except Exception as e:
        print(f"Error starting application: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure Chrome/Chromium is installed")
        print("2. For extended desktop: python src/main.py --monitor-layout extended")
        print("3. For manual positioning: python src/main.py --positions '0,0,1920,1080' '1920,0,1920,1080'")
        print("4. For separate X screens: python src/main.py --monitor-layout separate-screens --displays :0.0 :0.1")
        print("5. For single display: python src/main.py --single-display")
        sys.exit(1)
    finally:
        if controller:
            controller.cleanup()