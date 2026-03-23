#!/bin/bash
# Update John the Ripper
# Custom updater script for John the Ripper (jumbo version)

set -e

JOHN_PATH="/opt/cracking-tools/john"

echo "Updating John the Ripper..."

cd "$JOHN_PATH"

# Pull latest changes
git pull origin bleeding-jumbo

# Compile
cd src
./configure
make -s clean
make -sj$(nproc)

echo "John the Ripper updated successfully"
