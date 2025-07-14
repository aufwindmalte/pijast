# PIJAST - Pijast Is Just A Screen Toggle

**Version 0.1.0**

A Linux utility for toggling touchscreen input via Surface Pen double-press events. Designed for Surface Pro users requiring quick palm rejection control during stylus operations.

## Features

- Double-press Surface Pen eraser button to toggle touchscreen state
- Configurable timing parameters for double-press detection
- Automatic device detection for Surface Pen and IPTS touchscreens
- Custom command execution support
- Desktop notifications via libnotify
- Comprehensive error handling and device diagnostics
- Compatible with xinput-controlled input devices

## Requirements

- Linux with X11 display server
- Python 3.6 or later
- python3-evdev package
- xinput utility (typically pre-installed)
- libnotify for desktop notifications (optional)

## Installation

### Dependencies

```bash
# Ubuntu/Debian
sudo apt install python3-pip libnotify-bin
pip3 install evdev

# Fedora/RHEL
sudo dnf install python3-pip libnotify
pip3 install evdev

# Arch Linux
sudo pacman -S python-pip libnotify
pip install evdev
```

### User Permissions

Add user to input group for device access:
```bash
sudo usermod -a -G input $USER
```
Log out and back in for changes to take effect.

### Source Installation

```bash
git clone https://github.com/aufwindmalte/pijast.git
cd pijast
chmod +x pijast.py
```

## Usage

### Command Line Interface

```bash
python3 pijast.py [options]

Options:
  -p, --pen-device       Pen device name (default: auto-detect)
  -t, --touch-device     Touchscreen device name (default: auto-detect IPTS)
  -i, --interval         Double-press interval in seconds (default: 0.5)
  -c, --command          Custom command instead of xinput toggle
  -h, --help             Display help information
  --version              Display version information
```

### Device Discovery

```bash
# List input devices
python3 -c "import evdev; [print(f'{d.path}: {d.name}') for d in evdev.list_devices()]"

# List xinput devices
xinput list
```

### Basic Operation

```bash
# Auto-detection mode
python3 pijast.py

# Explicit device specification
python3 pijast.py -p "Surface Pen" -t "IPTS 1B96:006A Touchscreen"

# Custom timing
python3 pijast.py -i 0.3

# Background execution
nohup python3 pijast.py &
```

## System Service Integration

### Automated Installation

```bash
./install-service.sh
```

The installer configures:
- Executable permissions
- systemd user service
- Auto-start on login
- Service activation

### Service Management

```bash
# Status monitoring
systemctl --user status pijast.service

# Log inspection
journalctl --user -u pijast.service -f

# Manual control
systemctl --user {start|stop|restart} pijast.service

# Persistent configuration
systemctl --user {enable|disable} pijast.service

# Complete removal
./uninstall-service.sh
```

### Manual Service Configuration

Create `~/.config/systemd/user/pijast.service`:

```ini
[Unit]
Description=PIJAST - Surface Pen Touchscreen Toggle
Documentation=https://github.com/aufwindmalte/pijast
After=graphical-session.target
Wants=graphical-session.target

[Service]
Type=simple
ExecStart=/home/username/pijast/pijast.py
Restart=always
RestartSec=5
Environment=DISPLAY=:0
User=%i
Group=input
SupplementaryGroups=input
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=%h/pijast

[Install]
WantedBy=default.target
```

Activate with:
```bash
systemctl --user daemon-reload
systemctl --user enable --now pijast.service
```

## Technical Implementation

1. **Device Detection**: Scans `/dev/input/` for devices matching pen/stylus/surface keywords
2. **Event Processing**: Uses evdev to capture EV_KEY button press events
3. **Timing Analysis**: Implements configurable double-press detection algorithm
4. **Device Control**: Executes xinput disable/enable commands for touchscreen manipulation
5. **Notification System**: Integrates with desktop notification daemon via notify-send

## Hardware Compatibility

### Tested Configurations
- Microsoft Surface Pro (multiple generations)
- Intel Precise Touch & Stylus (IPTS) drivers
- IPTSD virtual touchscreen devices
- Surface Pen with Bluetooth connectivity
- Wacom stylus devices

### Requirements
- Device enumeration via `/dev/input/` interface
- EV_KEY event generation capability
- xinput-compatible touchscreen device

## Troubleshooting

### Permission Issues
```bash
# Verify group membership
groups

# Add to input group if missing
sudo usermod -a -G input $USER

# Temporary elevation (not recommended)
sudo python3 pijast.py
```

### Device Detection Failures
```bash
# Enumerate all input devices
python3 -c "import evdev; [print(f'{d.path}: {d.name}') for d in evdev.list_devices()]"

# Verify xinput device list
xinput list

# Manual device specification
python3 pijast.py -p "Exact Device Name"
```

### Connectivity Issues
- Verify Bluetooth pairing status
- Test pen functionality in other applications
- Check battery level
- Attempt alternate pen buttons

### xinput Integration
```bash
# Manual toggle testing
xinput disable "Touchscreen Device Name"
xinput enable "Touchscreen Device Name"

# Verify device name accuracy
xinput list | grep -i touch
```

## Contributing

1. Fork repository
2. Create feature branch
3. Implement changes with tests
4. Verify hardware compatibility
5. Submit pull request

## License

GNU General Public License v3.0 - See LICENSE file for complete terms.

## Support

- [Issue Tracker](https://github.com/aufwindmalte/pijast/issues)
- [Source Code](https://github.com/aufwindmalte/pijast)
- [Documentation](pijast.py)

## Etymology

**P**ijast **I**s **J**ust **A** **S**creen **T**oggle - nothing more.
