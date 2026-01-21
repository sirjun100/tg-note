#!/bin/bash
# Activation script for Intelligent Joplin Librarian
# Run this to activate the virtual environment: source activate.sh

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
    echo "Virtual environment activated. Run 'deactivate' to exit."
else
    echo "Virtual environment already active."
fi
