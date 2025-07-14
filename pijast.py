#!/usr/bin/env python3
"""
PIJAST - Pijast Is Just A Screen Toggle
Toggle your screen input devices (e.g., touchscreen) on/off by double-clicking your Surface Pen's eraser button.
Copyright (C) 2025 Malte Hoeltken

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

USAGE:
    python3 pijast.py [options]

    Options:
        -p, --pen-device       Name of the pen device (default: auto-detect Surface Pen)
        -t, --touch-device     Name of the touchscreen device (default: auto-detect)
        -i, --interval         Double-press time window in seconds (default: 0.5)
        -c, --command          Custom command to run instead of xinput toggle
        -h, --help             Show this help message

REQUIREMENTS:
    - python3-evdev package (pip install evdev)
    - xinput command (usually pre-installed on Linux)
    - notify-send for desktop notifications (libnotify-bin package)

SETUP:
    1. Find your pen device: python3 -c "import evdev; [print(f'{d.path}: {d.name}') for d in evdev.list_devices()]"
    2. Find your touchscreen: xinput list
    3. Run: python3 pijast.py -p "Your Pen Device Name" -t "Your Touchscreen Name"
"""

import argparse
import logging
import subprocess
import sys
import time
from typing import List, Optional, Union

__version__ = "0.1.0"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("pijast")

try:
    import evdev
except ImportError:
    logger.error("evdev module not found. Install with: pip install evdev")
    sys.exit(1)


class PijastError(Exception):
    """Base exception for PIJAST errors."""
    pass


class DeviceNotFoundError(PijastError):
    """Raised when a required device cannot be found."""
    pass


class CommandExecutionError(PijastError):
    """Raised when a system command fails."""
    pass


class PijastToggler:
    """Main class for handling pen input and touchscreen toggling."""
    
    # Device detection keywords
    PEN_KEYWORDS = ['surface', 'pen', 'stylus', 'wacom']
    SURFACE_KEYWORDS = ['ipts', 'iptsd', 'surface']
    
    def __init__(
        self,
        pen_device_name: Optional[str] = None,
        touch_device_name: Optional[str] = None,
        double_press_interval: float = 0.5,
        custom_command: Optional[str] = None
    ) -> None:
        """Initialize the PijastToggler.
        
        Args:
            pen_device_name: Name of the pen device to use
            touch_device_name: Name of the touchscreen device to control
            double_press_interval: Time window for double-press detection
            custom_command: Custom command to execute instead of xinput toggle
        """
        self.pen_device_name = pen_device_name
        self.touch_device_name = touch_device_name
        self.double_press_interval = self._validate_interval(double_press_interval)
        self.custom_command = custom_command
        self.last_press_time: float = 0.0
        self.touch_enabled: bool = True
        self.pen_device: Optional[evdev.InputDevice] = None
        
    @staticmethod
    def _validate_interval(interval: float) -> float:
        """Validate the double-press interval."""
        if not isinstance(interval, (int, float)) or interval <= 0:
            raise ValueError(f"Invalid interval: {interval}. Must be positive number.")
        if interval > 5.0:
            logger.warning(f"Large interval ({interval}s) may cause usability issues")
        return float(interval)

    def _run_command(
        self, 
        cmd: List[str], 
        capture_output: bool = True, 
        check: bool = False,
        timeout: Optional[int] = None
    ) -> subprocess.CompletedProcess[str]:
        """Run a system command with proper error handling.
        
        Args:
            cmd: Command and arguments as a list
            capture_output: Whether to capture stdout/stderr
            check: Whether to raise exception on non-zero exit
            timeout: Timeout in seconds
            
        Returns:
            CompletedProcess result
            
        Raises:
            CommandExecutionError: If command fails and check=True
        """
        try:
            result = subprocess.run(
                cmd,
                capture_output=capture_output,
                text=True,
                check=check,
                timeout=timeout
            )
            return result
        except subprocess.CalledProcessError as e:
            raise CommandExecutionError(f"Command {cmd[0]} failed: {e}") from e
        except subprocess.TimeoutExpired as e:
            raise CommandExecutionError(f"Command {cmd[0]} timed out: {e}") from e
        except FileNotFoundError as e:
            raise CommandExecutionError(f"Command {cmd[0]} not found: {e}") from e

    def find_pen_device(self) -> Optional[evdev.InputDevice]:
        """Find the Surface Pen or specified pen device.
        
        Returns:
            The pen device if found, None otherwise
            
        Raises:
            DeviceNotFoundError: If specified device is not found
        """
        try:
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        except (OSError, PermissionError) as e:
            logger.error(f"Cannot access input devices: {e}")
            return None

        if self.pen_device_name:
            # Look for user-specified device
            for device in devices:
                if self.pen_device_name.lower() in device.name.lower():
                    logger.info(f"Found specified pen device: {device.name}")
                    return device
            
            available = [f"{d.path}: {d.name}" for d in devices]
            raise DeviceNotFoundError(
                f"Pen device '{self.pen_device_name}' not found. "
                f"Available devices:\n{chr(10).join(available)}"
            )
        else:
            # Auto-detect Surface Pen or similar
            for device in devices:
                device_name_lower = device.name.lower()
                if any(keyword in device_name_lower for keyword in self.PEN_KEYWORDS):
                    # Check if device has the right capabilities
                    caps = device.capabilities()
                    if evdev.ecodes.EV_KEY in caps:
                        logger.info(f"Auto-detected pen device: {device.name}")
                        return device
            
            available = [f"{d.path}: {d.name}" for d in devices]
            logger.error(f"No pen device found. Available devices:\n{chr(10).join(available)}")
            return None

    def get_touchscreen_status(self) -> Optional[bool]:
        """Check if touchscreen is currently enabled using xinput.
        
        Returns:
            True if enabled, False if disabled, None if status unknown
        """
        if not self.touch_device_name:
            return None
            
        try:
            result = self._run_command(['xinput', 'list-props', self.touch_device_name])
            
            # Look for "Device Enabled" property
            for line in result.stdout.split('\n'):
                if 'Device Enabled' in line and ':' in line:
                    return '1' in line.split(':')[-1]
            return None
        except CommandExecutionError:
            logger.debug(f"Could not get status for device: {self.touch_device_name}")
            return None

    def _get_xinput_devices(self) -> List[str]:
        """Get list of xinput devices, returning empty list on error."""
        try:
            result = self._run_command(['xinput', 'list'])
            return result.stdout.split('\n')
        except CommandExecutionError:
            logger.debug("Could not get xinput device list")
            return []

    def _extract_device_names(self, lines: List[str]) -> List[str]:
        """Extract touchscreen device names from xinput output lines."""
        devices = []
        for line in lines:
            line_lower = line.lower()
            if ('slave  pointer' in line and 
                ('touchscreen' in line_lower or 'touch' in line_lower)):
                # Extract device name between ↳ and id=
                start = line.find('↳ ')
                end = line.find('id=')
                if start != -1 and end != -1 and end > start:
                    device_name = line[start + 2:end].strip()
                    if device_name:  # Only add non-empty names
                        devices.append(device_name)
        return devices

    def _find_best_touchscreen(self, devices: List[str]) -> Optional[str]:
        """Find the best touchscreen device, prioritizing Surface devices."""
        if not devices:
            return None
            
        # Prioritize Surface IPTS/IPTSD devices
        for device in devices:
            device_lower = device.lower()
            if any(keyword in device_lower for keyword in self.SURFACE_KEYWORDS):
                if 'touchscreen' in device_lower:
                    logger.info(f"Auto-detected Surface touchscreen: {device}")
                    return device

        # Fall back to any touchscreen device
        for device in devices:
            if 'touchscreen' in device.lower():
                logger.info(f"Auto-detected touchscreen: {device}")
                return device

        # Last resort: look for touch devices
        for device in devices:
            if 'touch' in device.lower():
                logger.info(f"Auto-detected touch device: {device}")
                return device

        return None

    def find_touchscreen_device(self) -> Optional[str]:
        """Auto-detect touchscreen device, prioritizing Surface IPTS devices."""
        if self.touch_device_name:
            return self.touch_device_name

        lines = self._get_xinput_devices()
        if not lines:
            return None

        devices = self._extract_device_names(lines)
        return self._find_best_touchscreen(devices)

    def _execute_custom_command(self) -> bool:
        """Execute custom command if specified."""
        if not self.custom_command:
            return False
            
        try:
            self._run_command(self.custom_command, shell=True, check=True)
            self._notify_custom_command()
            logger.info("Custom command executed successfully")
            return True
        except CommandExecutionError as e:
            logger.error(f"Custom command failed: {e}")
            return False

    def toggle_touchscreen(self) -> bool:
        """Toggle touchscreen enabled/disabled state.
        
        Returns:
            True if toggle was successful, False otherwise
        """
        if self.custom_command:
            return self._execute_custom_command()

        # Auto-detect touchscreen if not specified
        if not self.touch_device_name:
            self.touch_device_name = self.find_touchscreen_device()
            if not self.touch_device_name:
                logger.error("No touchscreen device found")
                self._log_available_devices()
                return False

        current_status = self.get_touchscreen_status()
        if current_status is None:
            logger.error(f"Cannot find touchscreen device '{self.touch_device_name}'")
            self._log_available_devices()
            return False

        # Toggle state
        action = 'disable' if current_status else 'enable'
        try:
            self._run_command(['xinput', action, self.touch_device_name], check=True)
            self.touch_enabled = not current_status
            self._notify_toggle(self.touch_enabled)
            logger.info(f"Touchscreen {action}d")
            return True
        except CommandExecutionError as e:
            logger.error(f"Failed to {action} touchscreen: {e}")
            return False

    def _log_available_devices(self) -> None:
        """Log available input devices for debugging."""
        try:
            result = self._run_command(['xinput', 'list'])
            logger.info(f"Available input devices:\n{result.stdout}")
        except CommandExecutionError:
            logger.error("Could not list available input devices")

    def _notify_toggle(self, enabled: bool) -> None:
        """Send desktop notification about touchscreen state."""
        status = "enabled" if enabled else "disabled"
        icon = "input-touchpad" if enabled else "input-touchpad-off"
        message = f"Touchscreen {status}"

        try:
            self._run_command(
                ['notify-send', '-i', icon, 'PIJAST', message],
                capture_output=False,
                timeout=5
            )
        except CommandExecutionError:
            logger.debug("Could not send desktop notification")

    def _notify_custom_command(self) -> None:
        """Send notification for custom command execution."""
        try:
            self._run_command(
                ['notify-send', '-i', 'system-run', 'PIJAST', 'Custom command executed'],
                capture_output=False,
                timeout=5
            )
        except CommandExecutionError:
            logger.debug("Could not send desktop notification")

    def handle_pen_event(self, event: evdev.InputEvent) -> None:
        """Process pen input events and detect double-press.
        
        Args:
            event: Input event from the pen device
        """
        # Look for button press events (eraser button is typically BTN_STYLUS2)
        if event.type == evdev.ecodes.EV_KEY and event.value == 1:  # Key press
            current_time = time.time()

            # Check for double-press
            if (current_time - self.last_press_time) <= self.double_press_interval:
                logger.info("Double-press detected! Toggling touchscreen...")
                self.toggle_touchscreen()
                self.last_press_time = 0.0  # Reset to prevent triple-press
            else:
                self.last_press_time = current_time

    def run(self) -> bool:
        """Main event loop.
        
        Returns:
            True if execution completed successfully, False on error
        """
        try:
            self.pen_device = self.find_pen_device()
            if not self.pen_device:
                return False

            # Auto-detect touchscreen if not specified
            if not self.touch_device_name:
                self.touch_device_name = self.find_touchscreen_device()
                if not self.touch_device_name:
                    logger.error("No touchscreen device found for auto-detection")
                    return False

            logger.info(f"Listening for double-press on: {self.pen_device.name}")
            logger.info(f"Target touchscreen: {self.touch_device_name}")
            logger.info(f"Double-press interval: {self.double_press_interval}s")
            logger.info("Press Ctrl+C to exit")

            # Check initial touchscreen status
            initial_status = self.get_touchscreen_status()
            if initial_status is not None:
                self.touch_enabled = initial_status
                status_text = "enabled" if self.touch_enabled else "disabled"
                logger.info(f"Touchscreen currently: {status_text}")

            # Grab device to prevent other applications from receiving events
            self.pen_device.grab()

            for event in self.pen_device.read_loop():
                self.handle_pen_event(event)

        except KeyboardInterrupt:
            logger.info("Exiting...")
        except PermissionError as e:
            logger.error(f"Permission denied: {e}")
            logger.error("Try running with sudo or add user to input group:")
            logger.error("sudo usermod -a -G input $USER")
            logger.error("Then log out and back in.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
        finally:
            if self.pen_device:
                try:
                    self.pen_device.ungrab()
                except Exception as e:
                    logger.debug(f"Error releasing device: {e}")

        return True


def validate_args(args: argparse.Namespace) -> None:
    """Validate command line arguments.
    
    Args:
        args: Parsed command line arguments
        
    Raises:
        ValueError: If arguments are invalid
    """
    if args.interval <= 0:
        raise ValueError(f"Interval must be positive, got: {args.interval}")
    if args.interval > 10:
        logger.warning(f"Large interval ({args.interval}s) may cause usability issues")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="PIJAST - Toggle touchscreen with Surface Pen double-press",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 pijast.py
  python3 pijast.py -p "Surface Pen" -t "ELAN Touchscreen"
  python3 pijast.py -i 0.3 -c "echo 'Custom toggle command'"
        """
    )

    parser.add_argument('--version', action='version',
                       version=f'PIJAST {__version__}')

    parser.add_argument('-p', '--pen-device',
                       help='Name of the pen device (default: auto-detect)')
    parser.add_argument('-t', '--touch-device',
                       help='Name of the touchscreen device (default: auto-detect Surface/IPTS touchscreen)')
    parser.add_argument('-i', '--interval',
                       type=float, default=0.5,
                       help='Double-press time window in seconds (default: 0.5)')
    parser.add_argument('-c', '--command',
                       help='Custom command to run instead of xinput toggle')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Enable verbose logging')

    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.setLevel(logging.DEBUG)

    try:
        validate_args(args)
        
        toggler = PijastToggler(
            pen_device_name=args.pen_device,
            touch_device_name=args.touch_device,
            double_press_interval=args.interval,
            custom_command=args.command
        )

        success = toggler.run()
        sys.exit(0 if success else 1)
        
    except (ValueError, DeviceNotFoundError, CommandExecutionError) as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()