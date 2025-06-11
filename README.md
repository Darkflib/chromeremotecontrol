# Chrome Remote Control Display Controller

A Flask-based application for controlling Chrome/Chromium browsers on multiple displays using the Chrome DevTools Protocol.

## Features

- Control multiple Chrome instances on different displays
- Remote control via REST API
- Navigate, refresh, and monitor browser instances
- Suspend (turn off) and resume (turn on) displays while preserving layout
- Robust error handling and cleanup

## Requirements

- Python 3.11+
- Chrome or Chromium browser
- X11 display server (for GUI displays)
- uv (for dependency management)

## Installation

```bash
# Install dependencies
uv sync

# Or using pip
pip install -r requirements.txt
```

## Usage

### Start the application
```bash
# Default: Auto-detect display configuration
python src/main.py

# Extended desktop (most common dual monitor setup)
python src/main.py --monitor-layout extended

# Manual positioning for extended desktop
python src/main.py --monitor-layout extended --positions "0,0,1920,1080" "1920,0,1920,1080"

# Separate X screens (uncommon)
python src/main.py --monitor-layout separate-screens --displays :0.0 :0.1

# Single display mode
python src/main.py --single-display
```

**For dual monitors configured as extended desktop** (most common setup):
- HDMI-2: 1920x1080+0+0 (left monitor)
- HDMI-1: 1920x1080+1920+0 (right monitor)
- Use: `python src/main.py --positions "0,0,1920,1080" "1920,0,1920,1080"`

### API Endpoints

- `GET /` - Status and available endpoints
- `POST /start` - Start Chrome instances
- `POST /display/<id>/goto` - Navigate display to URL
  ```json
  {"url": "https://example.com"}
  ```
- `POST /display/<id>/refresh` - Refresh display
- `GET /display/<id>/current` - Get current URL
- `GET /status` - Get status of all displays
- `POST /stop` - Stop all displays
- `POST /suspend` - Saves current display layout and turns off all displays
- `POST /resume` - Restores saved display layout and turns on displays

### Suspend Displays

*   **Endpoint:** `/suspend`
*   **Method:** `POST`
*   **Description:** Saves the current display layout (resolution, position of connected monitors) and then turns off all active displays using `xrandr`. This is useful for temporarily blanking the screens.

### Resume Displays

*   **Endpoint:** `/resume`
*   **Method:** `POST`
*   **Description:** Restores the display layout that was saved prior to the last call to `/suspend`. It turns on the displays and sets them to their previously recorded resolution and position using `xrandr`.

### Example Usage

```bash
# Start the server
python src/main.py

# In another terminal, test the API
curl http://localhost:5000/status

# Navigate display 1 to a website
curl -X POST -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}' \
     http://localhost:5000/display/1/goto
```

```text
mike@pi4b4:~/dev/chromeremotecontrol $ curl -X POST -H "Content-Type: application/json"      -d '{"url": "https://news.google.com"}'      http://localhost:5000/display/1/goto
{"message":"Navigation successful","status":"success"}
mike@pi4b4:~/dev/chromeremotecontrol $ curl -X POST -H "Content-Type: application/json"      -d '{"url": "https://www.google.com"}'      http://localhost:5000/display/2/goto
{"message":"Navigation successful","status":"success"}
mike@pi4b4:~/dev/chromeremotecontrol $ curl http://localhost:5000/status
{"active_displays":2,"displays":{"display_1":{"message":"OK","status":"active","url":"https://news.google.com/home?hl=en-GB&gl=GB&ceid=GB:en"},"display_2":{"message":"OK","status":"active","url":"https://www.google.com/"}},"status":"success"}
mike@pi4b4:~/dev/chromeremotecontrol $ 
```


## Troubleshooting

### Test your setup
```bash
python test_setup.py
```

### Common Issues

1. **"Flash and nothing happens"**
   - Missing Chrome/Chromium: Install with `sudo apt install chromium-browser`
   - Missing dependencies: Run `uv sync` or `pip install pychrome flask`
   - Display issues: Check `DISPLAY` environment variable

2. **"Chrome instances won't start"**
   - Check if Chrome is already running: `pkill -f chrome`
   - Verify dual displays are available: `xdpyinfo -display :0.0` and `xdpyinfo -display :0.1`
   - Check ports 9222/9223 are free: `netstat -ln | grep 922`
   - Make sure you have two independent screens, not just one extended desktop

3. **"Connection refused"**
   - Chrome remote debugging might be disabled
   - Firewall blocking ports 9222/9223
   - Chrome crashed during startup

4. **Headless Environments**
   - Use Xvfb: `Xvfb :99 -screen 0 1920x1080x24 &`
   - Set DISPLAY: `export DISPLAY=:99`

### Debug Mode

Add debug logging to see what's happening:

```python
# In src/main.py, change the Flask app line to:
app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Format code
black src/
isort src/

# Type checking
mypy src/

# Run tests
pytest
```

## Architecture

- **DisplayController**: Manages Chrome instances and connections
- **Flask API**: REST endpoints for remote control
- **Chrome DevTools Protocol**: Communication with browsers
- **Multi-display Support**: Handles different X displays

## License

MIT License - see LICENSE file for details.
