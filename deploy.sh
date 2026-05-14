#!/bin/bash
# Jarvis Deployment Script

set -e

echo "🚀 Deploying Jarvis AI System..."

# Check if running as root for system deployment
if [[ $1 == "system" ]]; then
    if [[ $EUID -ne 0 ]]; then
        echo "System deployment requires root privileges"
        exit 1
    fi

    INSTALL_DIR="/opt/jarvis"
    USER="jarvis"

    # Create user if not exists
    if ! id "$USER" &>/dev/null; then
        useradd --create-home --shell /bin/bash "$USER"
    fi

    # Create directories
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$INSTALL_DIR/data"

    # Copy files
    cp -r . "$INSTALL_DIR/"
    chown -R "$USER:$USER" "$INSTALL_DIR"

    # Setup virtual environment
    sudo -u "$USER" python3 -m venv "$INSTALL_DIR/venv"
    sudo -u "$USER" "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    sudo -u "$USER" "$INSTALL_DIR/venv/bin/pip" install -e "$INSTALL_DIR"

    # Install systemd service
    cp jarvis.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable jarvis
    systemctl start jarvis

    echo "✅ Jarvis deployed as system service"
    echo "Check status: systemctl status jarvis"
    echo "View logs: journalctl -u jarvis -f"

elif [[ $1 == "docker" ]]; then
    # Docker deployment
    docker-compose up -d
    echo "✅ Jarvis deployed with Docker"
    echo "Check status: docker-compose ps"
    echo "View logs: docker-compose logs -f"

else
    echo "Usage: $0 [system|docker]"
    echo "  system: Install as system service (requires root)"
    echo "  docker: Deploy with Docker Compose"
    exit 1
fi