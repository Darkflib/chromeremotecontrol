#!/usr/bin/env python3
"""
Dual Display Controller for Raspberry Pi using Chrome Remote Debugging
Requires: pip install pychrome flask
"""

import pychrome
from flask import Flask, request, jsonify
import subprocess
import time
import os
import signal
import sys

app = Flask(__name__)

class DisplayController:
    def __init__(self):
        self.browsers = {}
        self.chrome_processes = {}
        
    def start_chrome_instances(self):
        """Start Chrome instances for each display"""
        # Kill any existing Chrome processes
        subprocess.run(['pkill', '-f', 'chromium-browser'], check=False)
        time.sleep(2)
        
        # Chrome instance for display 1
        cmd1 = [
            'chromium-browser',
            '--kiosk',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--remote-debugging-port=9222',
            '--user-data-dir=/tmp/chrome_display1',
            '--display=:0.0',
            'about:blank'
        ]
        
        # Chrome instance for display 2
        cmd2 = [
            'chromium-browser',
            '--kiosk',
            '--no-sandbox',
            '--disable-web-security',
            '--disable-features=VizDisplayCompositor',
            '--remote-debugging-port=9223',
            '--user-data-dir=/tmp/chrome_display2',
            '--display=:0.1',
            'about:blank'
        ]
        
        # Start Chrome processes
        env = os.environ.copy()
        self.chrome_processes[1] = subprocess.Popen(cmd1, env=env)
        self.chrome_processes[2] = subprocess.Popen(cmd2, env=env)
        
        # Wait for Chrome to start
        time.sleep(3)
        
        # Connect to Chrome instances
        try:
            browser1 = pychrome.Browser(url="http://127.0.0.1:9222")
            browser2 = pychrome.Browser(url="http://127.0.0.1:9223")
            
            # Get the first tab from each browser
            tab1 = browser1.list_tab()[0]
            tab2 = browser2.list_tab()[0]
            
            # Start the tabs
            tab1.start()
            tab2.start()
            
            # Enable necessary domains
            tab1.Page.enable()
            tab1.Runtime.enable()
            tab2.Page.enable()
            tab2.Runtime.enable()
            
            self.browsers[1] = tab1
            self.browsers[2] = tab2
            
            print("Chrome instances started successfully")
            
        except Exception as e:
            print(f"Error connecting to Chrome: {e}")
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
        # Close browser connections
        for tab in self.browsers.values():
            try:
                tab.stop()
            except:
                pass
        
        # Kill Chrome processes
        for process in self.chrome_processes.values():
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Clean up temp directories
        subprocess.run(['rm', '-rf', '/tmp/chrome_display1', '/tmp/chrome_display2'], check=False)

# Global controller instance
controller = DisplayController()

@app.route('/start', methods=['POST'])
def start_displays():
    """Start the Chrome instances"""
    try:
        controller.start_chrome_instances()
        return jsonify({'status': 'success', 'message': 'Displays started'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/display/<int:display_id>/goto', methods=['POST'])
def goto_url(display_id):
    """Navigate display to URL"""
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'status': 'error', 'message': 'URL required'}), 400
    
    success, message = controller.navigate_to_url(display_id, data['url'])
    status_code = 200 if success else 500
    return jsonify({'status': 'success' if success else 'error', 'message': message}), status_code

@app.route('/display/<int:display_id>/refresh', methods=['POST'])
def refresh_display(display_id):
    """Refresh display"""
    success, message = controller.refresh_display(display_id)
    status_code = 200 if success else 500
    return jsonify({'status': 'success' if success else 'error', 'message': message}), status_code

@app.route('/display/<int:display_id>/current', methods=['GET'])
def get_current_url(display_id):
    """Get current URL of display"""
    url, message = controller.get_current_url(display_id)
    if url:
        return jsonify({'status': 'success', 'url': url})
    else:
        return jsonify({'status': 'error', 'message': message}), 500

@app.route('/status', methods=['GET'])
def get_status():
    """Get status of all displays"""
    status = {}
    for display_id in [1, 2]:
        url, message = controller.get_current_url(display_id)
        status[f'display_{display_id}'] = {
            'url': url,
            'status': 'active' if url else 'inactive'
        }
    return jsonify(status)

@app.route('/stop', methods=['POST'])
def stop_displays():
    """Stop all displays"""
    controller.cleanup()
    return jsonify({'status': 'success', 'message': 'Displays stopped'})

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print('Shutting down...')
    controller.cleanup()
    sys.exit(0)

if __name__ == '__main__':
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Auto-start displays on startup
        print("Starting display controller...")
        controller.start_chrome_instances()
        
        # Start Flask app
        app.run(host='0.0.0.0', port=5000, debug=False)
        
    except KeyboardInterrupt:
        print("Received interrupt signal")
    finally:
        controller.cleanup()