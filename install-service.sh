#!/bin/bash
"""
PIJAST Service Installation Script
Copyright (C) 2025 Malte Hoeltken

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="pijast.service"
SERVICE_FILE="$SCRIPT_DIR/$SERVICE_NAME"
USER_SERVICE_DIR="$HOME/.config/systemd/user"

echo "PIJAST Service Installer"
echo "========================"

# Check if we're in the right directory
if [ ! -f "$SCRIPT_DIR/pijast.py" ]; then
    echo "ERROR: pijast.py not found in $SCRIPT_DIR"
    echo "Please run this script from the PIJAST directory."
    exit 1
fi

if [ ! -f "$SERVICE_FILE" ]; then
    echo "ERROR: $SERVICE_NAME not found in $SCRIPT_DIR"
    exit 1
fi

# Check if user is in input group
if ! groups | grep -q "input"; then
    echo "WARNING: User is not in the 'input' group."
    echo "You may need to add yourself to the input group:"
    echo "  sudo usermod -a -G input \$USER"
    echo "Then log out and back in."
    echo ""
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Make pijast.py executable
echo "Making pijast.py executable..."
chmod +x "$SCRIPT_DIR/pijast.py"

# Create user systemd directory
echo "Creating systemd user directory..."
mkdir -p "$USER_SERVICE_DIR"

# Copy and customize service file
echo "Installing service file..."
sed "s|%h/pijast/pijast.py|$SCRIPT_DIR/pijast.py|g" "$SERVICE_FILE" > "$USER_SERVICE_DIR/$SERVICE_NAME"

# Reload systemd and enable service
echo "Reloading systemd and enabling service..."
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"

echo ""
echo "PIJAST service installed successfully!"
echo ""
echo "Service commands:"
echo "  Start:   systemctl --user start $SERVICE_NAME"
echo "  Stop:    systemctl --user stop $SERVICE_NAME"
echo "  Status:  systemctl --user status $SERVICE_NAME"
echo "  Logs:    journalctl --user -u $SERVICE_NAME -f"
echo ""
echo "The service will start automatically on login."
echo ""
read -p "Start the service now? (Y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo "Starting PIJAST service..."
    systemctl --user start "$SERVICE_NAME"

    sleep 2
    echo ""
    echo "Service status:"
    systemctl --user status "$SERVICE_NAME" --no-pager -l
fi

echo ""
echo "Installation complete!"
