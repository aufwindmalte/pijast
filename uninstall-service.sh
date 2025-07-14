#!/bin/bash
"""
PIJAST Service Uninstallation Script
Copyright (C) 2025 Malte Hoeltken

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

set -e

SERVICE_NAME="pijast.service"
USER_SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_PATH="$USER_SERVICE_DIR/$SERVICE_NAME"

echo "PIJAST Service Uninstaller"
echo "=========================="

# Check if service exists
if [ ! -f "$SERVICE_PATH" ]; then
    echo "Service not found at $SERVICE_PATH"
    echo "Nothing to uninstall."
    exit 0
fi

echo "Stopping and disabling PIJAST service..."

# Stop the service if running
if systemctl --user is-active --quiet "$SERVICE_NAME"; then
    systemctl --user stop "$SERVICE_NAME"
    echo "Service stopped."
fi

# Disable the service
if systemctl --user is-enabled --quiet "$SERVICE_NAME"; then
    systemctl --user disable "$SERVICE_NAME"
    echo "Service disabled."
fi

# Remove service file
rm -f "$SERVICE_PATH"
echo "Service file removed."

# Reload systemd
systemctl --user daemon-reload
echo "Systemd reloaded."

echo ""
echo "PIJAST service uninstalled successfully!"
echo ""
echo "Note: The PIJAST script itself is still available for manual use."
