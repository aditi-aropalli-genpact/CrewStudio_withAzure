#!/bin/bash

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/Scripts/activate"

cd "$SCRIPT_DIR"

streamlit run app/app.py --server.headless True --server.port 4200

