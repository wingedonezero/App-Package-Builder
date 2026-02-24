#!/bin/bash

# App Package Builder - Application Launcher

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}Error: Virtual environment not found!${NC}"
    echo ""
    echo "Please run the setup script first:"
    echo -e "  ${BLUE}./setup_env.sh${NC}"
    echo ""
    exit 1
fi

activate_venv() {
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        return 0
    fi
    echo -e "${RED}Error: Failed to activate virtual environment.${NC}"
    return 1
}

run_in_current_terminal() {
    echo "========================================="
    echo "App Package Builder"
    echo "========================================="
    echo ""
    echo -e "${BLUE}Starting application...${NC}"
    echo ""

    cd "$PROJECT_DIR"

    if ! activate_venv; then
        exit 1
    fi

    python main.py 2>&1
    EXIT_CODE=$?

    echo ""
    if [ $EXIT_CODE -eq 0 ]; then
        echo -e "${GREEN}Application exited normally${NC}"
    else
        echo -e "${RED}Application exited with error code: $EXIT_CODE${NC}"
    fi
    echo -e "${YELLOW}Press Enter to close...${NC}"
    read
}

main() {
    WRAPPER_CMD="cd '$PROJECT_DIR' && source '$VENV_DIR/bin/activate' && python main.py 2>&1; EXIT_CODE=\$?; echo ''; if [ \$EXIT_CODE -eq 0 ]; then echo -e '${GREEN}Application exited normally${NC}'; else echo -e '${RED}Application exited with error code: '\$EXIT_CODE'${NC}'; fi; echo -e '${YELLOW}Press Enter to close...${NC}'; read"

    # If already in a terminal, just run directly
    if [ -t 0 ]; then
        run_in_current_terminal
    else
        # Detect terminal emulator
        if command -v konsole &> /dev/null; then
            konsole -e bash -c "$WRAPPER_CMD"
        elif command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "$WRAPPER_CMD"
        elif command -v xfce4-terminal &> /dev/null; then
            xfce4-terminal -e "bash -c \"$WRAPPER_CMD\""
        elif command -v alacritty &> /dev/null; then
            alacritty -e bash -c "$WRAPPER_CMD"
        elif command -v kitty &> /dev/null; then
            kitty bash -c "$WRAPPER_CMD"
        elif command -v xterm &> /dev/null; then
            xterm -e bash -c "$WRAPPER_CMD"
        else
            echo -e "${YELLOW}No terminal emulator found. Running in current shell...${NC}"
            run_in_current_terminal
        fi
    fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    main "$@"
fi
