#!/bin/bash
# Update Powerpipe
# Custom updater script for powerpipe

set -e

echo "Updating Powerpipe..."

# Download and run official installer
curl -fsSL https://raw.githubusercontent.com/turbot/powerpipe/main/install.sh | sh

echo "Powerpipe updated successfully"
