# Music Player App for Raspberry Pi

A full-featured, touch-friendly music player designed for Raspberry Pi with a 480x320 display.

## Features

### 🎵 Multi-Level Navigation
- **Landing Menu**: Albums, Artists, Favorites
- **Album Browser**: View all albums organized by metadata
- **Artist Browser**: Browse music by artist
- **Favorites**: Quick access to your favorite albums
- **Album Detail**: See all tracks in an album
- **Now Playing**: Full-screen playback with album art

### ✨ Smart Features
- **Auto-fullscreen**: Automatically fits your display size
- **Dynamic sizing**: All UI elements scale to your screen
- **Auto-advance**: Next track plays automatically
- **Favorites system**: Mark albums you love
- **Metadata-based**: Organizes by tags, not folders
- **Album art**: Beautiful display of embedded artwork
- **Touch-friendly**: Large buttons and list items

### 🎨 Beautiful Design
- Modern dark theme with gradients
- Red accent colors
- Glass morphism effects
- Smooth animations
- Circular control buttons

## Installation

### Requirements
```bash
sudo apt-get update
sudo apt-get install python3-pyqt5 python3-vlc
pip3 install python-vlc mutagen
```

### Quick Install
```bash
chmod +x install.sh
./install.sh
```

### Manual Installation
```bash
# Copy to home directory
cp music_player_app.py ~/music_player_app.py
chmod +x ~/music_player_app.py

# Run manually
python3 ~/music_player_app.py
```

### Auto-Start on Boot
```bash
# Copy service file
sudo cp music-player.service /etc/systemd/system/

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable music-player.service
sudo systemctl start music-player.service
```

## Usage

### Navigation Flow
1. **Landing Page**: Choose Albums, Artists, or Favorites
2. **List View**: Select an album from the list
3. **Album Detail**: View and select individual tracks
4. **Now Playing**: Control playback

### Controls
- **Back buttons**: Navigate to previous screen
- **Track selection**: Tap any track to play
- **Play/Pause**: Large red button
- **Previous/Next**: Side buttons
- **Favorites**: Heart icon on album detail page

### Keyboard Shortcuts
- `ESC`: Go back / Exit application
- `SPACE`: Play/Pause

## Configuration

### Music Directory
By default, the app looks for music in `~/Music`. To change this, edit the last line:
```python
music_folder = os.path.expanduser("~/Music")
```

### Audio Device
The app is configured for ALSA device `hw:1,0`. To change:
```python
self.instance = vlc.Instance([
    "--aout=alsa",
    "--alsa-audio-device=hw:1,0"  # Change this
])
```

### Screen Size
The app automatically detects and adapts to your screen size. No configuration needed!

## Troubleshooting

### No audio output
```bash
# List audio devices
aplay -l

# Test VLC
cvlc --aout=alsa --alsa-audio-device=hw:1,0 test.mp3
```

### Display issues
- Make sure X server is running
- Check display resolution: `xrandr`
- Verify DISPLAY variable: `echo $DISPLAY`

### Service won't start
```bash
# Check service status
sudo systemctl status music-player

# View logs
journalctl -u music-player -f
```

## File Formats Supported
- FLAC
- MP3
- M4A
- OGG

## Data Storage
- **Favorites**: Stored in `~/.music_player_favorites.json`
- **Music**: Reads from your specified directory
- **Metadata**: Extracted from audio file tags

## Development

### Project Structure
- `music_player_app.py`: Main application
- `music-player.service`: Systemd service file
- `install.sh`: Installation script

### Key Classes
- `MusicPlayerApp`: Main application window
- Pages: Landing, Albums, Artists, Favorites, Album Detail, Now Playing

## License
Free to use and modify for personal projects.

## Credits
Built for Raspberry Pi music enthusiasts!
