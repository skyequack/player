#!/bin/bash

# Music Player App Installation Script

echo "Installing Music Player App..."

# Copy the application to home directory
cp music_player_app.py ~/music_player_app.py
chmod +x ~/music_player_app.py

# Install systemd service (optional - for auto-start on boot)
read -p "Do you want the music player to auto-start on boot? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    sudo cp music-player.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable music-player.service
    echo "Auto-start enabled. The music player will start on boot."
fi

echo ""
echo "Installation complete!"
echo ""
echo "To run manually: python3 ~/music_player_app.py"
echo "To start service: sudo systemctl start music-player"
echo "To stop service: sudo systemctl stop music-player"
echo ""
echo "Keyboard shortcuts:"
echo "  ESC - Go back / Exit"
echo "  SPACE - Play/Pause"
