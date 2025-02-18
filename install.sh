#!/bin/bash

# Function to check if Poetry is installed and install it if not
check_poetry() {
    if command -v poetry >/dev/null 2>&1; then
        return 0
    else
        echo "Poetry is not installed. Installing Poetry..."

        if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            powershell -Command "(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -" || {
                echo "Failed to install Poetry. Please install it manually."
                return 1
            }
        else
            curl -sSL https://install.python-poetry.org | python3 - || {
                echo "Failed to install Poetry. Please install it manually."
                return 1
            }
        fi
        return 0
    fi
}

# Parse command line arguments
TEST=0
GPU=0

while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--test)
            TEST=1
            shift
            ;;
        -g|--gpu)
            GPU=1
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-t|--test] [-g|--gpu]"
            exit 1
            ;;
    esac
done

# Main installation function
install() {
    if ! check_poetry; then
        exit 1
    fi

    INSTALL_ARGS=()
    if [ $GPU -eq 1 ]; then
        echo "Installing GPU version..."
        INSTALL_ARGS+=("-E" "gpu" "--with" "gpu" "--no-root")
    else
        echo "Installing CPU version..."
        INSTALL_ARGS+=("-E" "cpu" "--with" "cpu" "--no-root")
    fi

    if [ $TEST -eq 1 ]; then
        echo "Including test dependencies..."
        INSTALL_ARGS+=("-E" "test")
    fi

    poetry install "${INSTALL_ARGS[@]}" || {
        echo "An error occurred during installation"
        exit 1
    }
}

# Main execution
trap 'echo -e "\nInstallation cancelled by user."; exit 1' INT

echo "Installing Libb-NLP API"
install
echo "Installation completed successfully!"
