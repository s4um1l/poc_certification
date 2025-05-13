#!/bin/bash

echo "Starting AI COO Shopify Agent using uv..."
echo "----------------------------------------"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it with:"
    echo "curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Set up environment variable for uv to use system Python instead of trying to build the project
export UV_SYSTEM_PYTHON=1

# Create .env file for backend if it doesn't exist
if [ ! -f "backend/.env" ]; then
    echo "Creating .env file in backend directory..."
    echo "# Add your API key here" > backend/.env
    echo "# OPENAI_API_KEY=your_api_key_here" >> backend/.env
    echo "# ANTHROPIC_API_KEY=your_api_key_here" >> backend/.env
    echo ""
    echo "⚠️  IMPORTANT: Please edit backend/.env to add your API key before proceeding."
    echo "Press any key to continue when ready..."
    read -n 1
fi

# Create .env.local file for frontend if it doesn't exist
if [ ! -f "frontend/.env.local" ]; then
    echo "Creating .env.local file for frontend..."
    mkdir -p frontend
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
fi

# Start backend and frontend in separate terminals
case "$(uname -s)" in
    Darwin)
        # macOS
        echo "Starting backend in new terminal..."
        osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./backend-uv.sh"'
        echo "Starting frontend in new terminal..."
        osascript -e 'tell app "Terminal" to do script "cd '"$(pwd)"' && ./frontend-uv.sh"'
        ;;
    Linux)
        # Linux
        echo "Starting backend in new terminal..."
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "cd $(pwd) && ./backend-uv.sh; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "cd $(pwd) && ./backend-uv.sh" &
        else
            echo "Could not find a suitable terminal emulator. Please run backend-uv.sh and frontend-uv.sh in separate terminals."
            exit 1
        fi
        
        echo "Starting frontend in new terminal..."
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal -- bash -c "cd $(pwd) && ./frontend-uv.sh; exec bash"
        elif command -v xterm &> /dev/null; then
            xterm -e "cd $(pwd) && ./frontend-uv.sh" &
        fi
        ;;
    CYGWIN*|MINGW*|MSYS*)
        # Windows
        echo "Starting backend and frontend..."
        echo "On Windows, please run backend-uv.sh and frontend-uv.sh in separate terminals."
        ;;
    *)
        # Unknown OS
        echo "Unknown operating system. Please run backend-uv.sh and frontend-uv.sh in separate terminals."
        ;;
esac

echo ""
echo "The application should now be starting..."
echo "- Backend will be available at: http://localhost:8000"
echo "- Frontend will be available at: http://localhost:3000"
echo ""
echo "If the terminals didn't open automatically, please run these commands in separate terminals:"
echo "- ./backend-uv.sh"
echo "- ./frontend-uv.sh" 