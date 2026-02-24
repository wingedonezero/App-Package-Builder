#!/bin/bash

# App Package Builder - Environment Setup

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

show_menu() {
    echo ""
    echo "========================================="
    echo "App Package Builder - Environment Setup"
    echo "========================================="
    echo ""
    echo -e "${BLUE}Project Directory:${NC} $PROJECT_DIR"
    echo ""
    echo "Please select an option:"
    echo ""
    echo -e "  ${CYAN}1)${NC} Full Setup - Create venv and install dependencies"
    echo -e "  ${CYAN}2)${NC} Update Dependencies"
    echo -e "  ${CYAN}3)${NC} Show Installed Packages"
    echo -e "  ${CYAN}4)${NC} Exit"
    echo ""
    echo -n "Enter your choice [1-4]: "
}

venv_pip() {
    "$VENV_PYTHON" -m pip "$@"
}

ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}Virtual environment not found!${NC}"
        echo -e "${YELLOW}Please run Full Setup first (option 1)${NC}"
        return 1
    fi
    source "$VENV_DIR/bin/activate"
    if [ ! -x "$VENV_PYTHON" ]; then
        echo -e "${RED}Virtual environment Python not found at $VENV_PYTHON${NC}"
        return 1
    fi
    return 0
}

full_setup() {
    echo ""
    echo "========================================="
    echo "Full Setup"
    echo "========================================="
    echo ""

    # Step 1: Find Python 3.13
    echo -e "${YELLOW}[1/3] Checking for Python 3.13...${NC}"

    PYTHON_CMD=""
    for py in python3.13 python3 python; do
        if command -v "$py" &> /dev/null; then
            version=$("$py" --version 2>&1 | grep -oP '\d+\.\d+\.\d+')
            if [[ "$version" == 3.13.* ]]; then
                PYTHON_CMD="$py"
                echo -e "${GREEN}✓ Found Python $version: $PYTHON_CMD${NC}"
                break
            fi
        fi
    done

    if [ -z "$PYTHON_CMD" ]; then
        echo -e "${RED}Python 3.13 not found.${NC}"
        echo "Please install it with:"
        echo "  sudo apt install python3.13 python3.13-venv"
        exit 1
    fi

    # Step 2: Create venv
    echo ""
    echo -e "${YELLOW}[2/3] Setting up virtual environment...${NC}"

    if [ -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Removing existing virtual environment...${NC}"
        rm -rf "$VENV_DIR"
    fi

    echo -e "${BLUE}Creating virtual environment at: $VENV_DIR${NC}"

    if ! "$PYTHON_CMD" -m venv "$VENV_DIR"; then
        echo -e "${RED}Failed to create virtual environment.${NC}"
        echo "Make sure python3.13-venv is installed:"
        echo "  sudo apt install python3.13-venv"
        exit 1
    fi

    source "$VENV_DIR/bin/activate"
    echo -e "${GREEN}✓ Virtual environment created${NC}"

    echo -e "${BLUE}Upgrading pip...${NC}"
    venv_pip install --upgrade pip

    # Step 3: Install dependencies
    echo ""
    echo -e "${YELLOW}[3/3] Installing dependencies...${NC}"

    venv_pip install PySide6

    echo ""
    echo -e "${GREEN}✓ Setup complete!${NC}"
    echo ""
    echo "========================================="
    echo -e "${GREEN}Environment ready!${NC}"
    echo "========================================="
    echo ""
    echo "To run the application:"
    echo -e "  ${BLUE}./run.sh${NC}"
    echo ""
}

update_deps() {
    echo ""
    echo "========================================="
    echo "Update Dependencies"
    echo "========================================="
    echo ""

    if ! ensure_venv; then
        return 1
    fi

    echo -e "${YELLOW}Checking for updates...${NC}"
    echo ""

    outdated=$(venv_pip list --outdated --format=json 2>/dev/null)

    if [ "$outdated" == "[]" ] || [ -z "$outdated" ]; then
        echo -e "${GREEN}✓ All packages are up to date!${NC}"
        return 0
    fi

    echo -e "${YELLOW}Updates available:${NC}"
    echo "$outdated" | "$VENV_PYTHON" -c "
import sys, json
data = json.load(sys.stdin)
for pkg in data:
    print(f\"  {pkg['name']:30s} {pkg['version']:15s} -> {pkg['latest_version']}\")
"

    echo ""
    echo -n "Update all? [y/N]: "
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        packages=$(echo "$outdated" | "$VENV_PYTHON" -c "
import sys, json
data = json.load(sys.stdin)
print(' '.join(p['name'] for p in data))
")
        venv_pip install --upgrade $packages
        echo -e "${GREEN}✓ Updated successfully!${NC}"
    else
        echo -e "${YELLOW}Update cancelled${NC}"
    fi
}

show_packages() {
    echo ""
    echo "========================================="
    echo "Installed Packages"
    echo "========================================="
    echo ""

    if ! ensure_venv; then
        return 1
    fi

    venv_pip list
}

main() {
    case "$1" in
        --setup)  full_setup;    exit 0 ;;
        --update) update_deps;   exit 0 ;;
        --list)   show_packages; exit 0 ;;
    esac

    while true; do
        show_menu
        read -r choice
        case $choice in
            1) full_setup    ;;
            2) update_deps   ;;
            3) show_packages ;;
            4) echo ""; echo -e "${GREEN}Goodbye!${NC}"; echo ""; exit 0 ;;
            *) echo ""; echo -e "${RED}Invalid choice.${NC}" ;;
        esac
        echo ""
        echo -n "Press Enter to return to menu..."
        read -r
    done
}

main "$@"
