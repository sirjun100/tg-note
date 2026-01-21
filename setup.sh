#!/bin/bash
# Intelligent Joplin Librarian - Setup Script
# This script creates a virtual environment, installs dependencies, and sets up the project

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python 3.8+ is available
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info[0])')
    PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info[1])')

    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        print_error "Python 3.8 or higher is required. You have Python $PYTHON_VERSION."
        exit 1
    fi

    print_success "Python $PYTHON_VERSION found ✓"
}

# Create virtual environment
create_venv() {
    print_step "Creating virtual environment..."

    if [ -d "venv" ]; then
        print_warning "Virtual environment already exists. Removing..."
        rm -rf venv
    fi

    python3 -m venv venv
    print_success "Virtual environment created ✓"
}

# Activate virtual environment and install requirements
setup_environment() {
    print_step "Activating virtual environment and installing dependencies..."

    # Activate virtual environment
    source venv/bin/activate

    # Upgrade pip
    pip install --upgrade pip

    # Install requirements
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed ✓"
    else
        print_error "requirements.txt not found!"
        exit 1
    fi
}

# Run the Python setup script
run_python_setup() {
    print_step "Running Python setup script..."

    if [ -f "setup_env.py" ]; then
        python setup_env.py
    else
        print_error "setup_env.py not found!"
        exit 1
    fi
}

# Create activation script
create_activation_script() {
    print_step "Creating activation helper script..."

    cat > activate.sh << 'EOF'
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
EOF

    chmod +x activate.sh
    print_success "Created activate.sh script ✓"
}

# Print next steps
print_next_steps() {
    echo
    echo "=========================================="
    echo "🎉 SETUP COMPLETE!"
    echo "=========================================="
    echo
    echo "Next steps:"
    echo "1. Edit the .env file with your API keys:"
    echo "   - TELEGRAM_BOT_TOKEN"
    echo "   - OPENAI_API_KEY"
    echo "   - ALLOWED_TELEGRAM_USER_IDS"
    echo
    echo "2. Start Joplin with Web Clipper enabled"
    echo
    echo "3. Activate the virtual environment:"
    echo "   source activate.sh"
    echo
    echo "4. Run the bot:"
    echo "   python main.py"
    echo
    echo "5. Test with /start command in Telegram"
    echo
    echo "For help, see README.md"
    echo
    echo "=========================================="
}

# Main execution
main() {
    echo "🤖 Intelligent Joplin Librarian Setup"
    echo "====================================="
    echo

    check_python
    create_venv
    setup_environment
    run_python_setup
    create_activation_script
    print_next_steps
}

# Run main function
main "$@"