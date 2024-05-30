#!/bin/bash

# Update the repository (fetch and merge)
echo "Updating repository..."
git fetch upstream >/dev/null 2>&1  # Suppress output for cleaner status messages
result_fetch=$?

if [[ $result_fetch -eq 0 ]]; then
  git merge upstream/main >/dev/null 2>&1
  result_merge=$?

  if [[ $result_merge -eq 0 ]]; then
    echo "Repository updated successfully."
  else
    echo "Error: An error occurred during merge. Please review and resolve conflicts manually."
    exit 1  # Exit with an error code for CI/CD integration
  fi
else
  echo "Warning: Could not fetch updates from upstream. Are you connected to the internet?"
fi

# Activate the virtual environment (replace with your actual path)
echo "Activating virtual environment..."
source ./venv/Scripts/activate  # Assuming Windows environment (adjust for other OS)
result_activate=$?

if [[ $result_activate -eq 0 ]]; then
  echo "Virtual environment activated successfully."
else
  echo "Error: Could not activate virtual environment. Please check your virtual environment setup."
  exit 1
fi

# Run tests
echo "Running tests..."
python -m unittest discover -v -s tests
# Run the application
echo "Starting application..."
python run.py 