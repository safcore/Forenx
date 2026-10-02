#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "==> Upgrading pip..."
pip install --upgrade pip

if [ -f "requirements.txt" ]; then
    echo "==> Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    echo "==> Running collectstatic..."
    python manage.py collectstatic --no-input
    echo "==> Running database migrations..."
    python manage.py migrate
elif [ -f "backend/requirements.txt" ]; then
    echo "==> Installing dependencies from backend/requirements.txt..."
    pip install -r backend/requirements.txt
    echo "==> Running collectstatic..."
    python backend/manage.py collectstatic --no-input
    echo "==> Running database migrations..."
    python backend/manage.py migrate
else
    echo "ERROR: requirements.txt not found!"
    exit 1
fi

echo "==> Build completed successfully!"
