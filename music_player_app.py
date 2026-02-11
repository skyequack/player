#!/usr/bin/env python3
import sys
import os
import json
from collections import defaultdict
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
    QLabel, QPushButton, QStackedWidget, QListWidgetItem, QScrollArea
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter, QLinearGradient, QPalette
import vlc
from mutagen import File
from mutagen.flac import FLAC
from mutagen.mp3 import MP3


class MusicPlayerApp(QWidget):
    def __init__(self, music_root):
        super().__init__()
        self.music_root = music_root
        self.favorites_file = os.path.expanduser("~/.music_player_favorites.json")
        
        # VLC setup with ALSA audio
        self.instance = vlc.Instance([
            "--aout=alsa",
            "--alsa-audio-device=hw:1,0"
        ])
        self.player = self.instance.media_player_new()
        
        # Data structures
        self.albums = {}  # {album_name: [track_paths]}
        self.album_metadata = {}  # {album_name: {'artist': ..., 'art': ...}}
        self.artists = {}  # {artist_name: [album_names]}
        self.favorites = self.load_favorites()
        
        self.current_tracks = []
        self.current_album = None
        self.current_index = -1
        
        # Auto-fullscreen
        self.showFullScreen()
        
        # Get screen size for dynamic sizing
        screen = QApplication.primaryScreen().geometry()
        self.screen_width = screen.width()
        self.screen_height = screen.height()
        
        self.init_ui()
        self.scan_music_library()
        
        # Update timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(500)
        
    def init_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Apply dark theme
        self.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #1a252f);
                color: #ecf0f1;
                font-family: 'Segoe UI', 'Helvetica', 'Arial', sans-serif;
            }}
            QListWidget {{
                background: rgba(255, 255, 255, 0.05);
                border: none;
                font-size: {int(self.screen_height * 0.04)}px;
                color: #ecf0f1;
                padding: 10px;
            }}
            QListWidget::item {{
                padding: {int(self.screen_height * 0.025)}px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                margin: 5px;
            }}
            QListWidget::item:hover {{
                background: rgba(52, 152, 219, 0.3);
            }}
            QListWidget::item:selected {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e74c3c, stop:1 #c0392b);
                color: white;
            }}
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495e, stop:1 #2c3e50);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 12px;
                padding: {int(self.screen_height * 0.025)}px;
                font-size: {int(self.screen_height * 0.04)}px;
                font-weight: bold;
                color: #ecf0f1;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3d5a6f, stop:1 #34495e);
                border: 2px solid rgba(255, 255, 255, 0.4);
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #2c3e50, stop:1 #1a252f);
            }}
            QSlider::groove:horizontal {{
                height: {int(self.screen_height * 0.015)}px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: {int(self.screen_height * 0.0075)}px;
            }}
            QSlider::sub-page:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e74c3c, stop:1 #c0392b);
                border-radius: {int(self.screen_height * 0.0075)}px;
            }}
            QSlider::handle:horizontal {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ecf0f1, stop:1 #bdc3c7);
                width: {int(self.screen_height * 0.04)}px;
                height: {int(self.screen_height * 0.04)}px;
                margin: {int(-self.screen_height * 0.0125)}px 0;
                border-radius: {int(self.screen_height * 0.02)}px;
                border: 2px solid #34495e;
            }}
        """)
        
        # Stacked widget for different pages
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)
        
        # Create pages
        self.landing_page = self.create_landing_page()
        self.albums_page = self.create_albums_page()
        self.artists_page = self.create_artists_page()
        self.favorites_page = self.create_favorites_page()
        self.album_detail_page = self.create_album_detail_page()
        self.now_playing_page = self.create_now_playing_page()
        
        self.stack.addWidget(self.landing_page)
        self.stack.addWidget(self.albums_page)
        self.stack.addWidget(self.artists_page)
        self.stack.addWidget(self.favorites_page)
        self.stack.addWidget(self.album_detail_page)
        self.stack.addWidget(self.now_playing_page)
        
    def create_landing_page(self):
        """Main landing menu with three options"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # Title
        title = QLabel("♫ MUSIC PLAYER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            font-size: {int(self.screen_height * 0.08)}px;
            font-weight: bold;
            color: #e74c3c;
            padding: 20px;
            letter-spacing: 3px;
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Menu buttons
        btn_albums = QPushButton("Albums")
        btn_artists = QPushButton("Artists")
        btn_favorites = QPushButton("Favorites")
        
        btn_albums.setFixedHeight(int(self.screen_height * 0.15))
        btn_artists.setFixedHeight(int(self.screen_height * 0.15))
        btn_favorites.setFixedHeight(int(self.screen_height * 0.15))
        
        btn_albums.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_artists.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_favorites.clicked.connect(lambda: self.stack.setCurrentIndex(3))
        
        layout.addWidget(btn_albums)
        layout.addWidget(btn_artists)
        layout.addWidget(btn_favorites)
        
        layout.addStretch()
        
        # Exit button
        btn_exit = QPushButton("Exit")
        btn_exit.setFixedHeight(int(self.screen_height * 0.1))
        btn_exit.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #95a5a6, stop:1 #7f8c8d);
            font-size: {int(self.screen_height * 0.03)}px;
        """)
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)
        
        return page
    
    def create_albums_page(self):
        """Page showing all albums"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self.create_header("Albums", lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(header)
        
        # Album list
        self.album_list = QListWidget()
        self.album_list.itemClicked.connect(self.show_album_detail)
        layout.addWidget(self.album_list)
        
        return page
    
    def create_artists_page(self):
        """Page showing all artists"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self.create_header("Artists", lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(header)
        
        # Artist list
        self.artist_list = QListWidget()
        self.artist_list.itemClicked.connect(self.show_artist_albums)
        layout.addWidget(self.artist_list)
        
        return page
    
    def create_favorites_page(self):
        """Page showing favorite albums"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = self.create_header("Favorites", lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(header)
        
        # Favorites list
        self.favorites_list = QListWidget()
        self.favorites_list.itemClicked.connect(self.show_album_detail)
        layout.addWidget(self.favorites_list)
        
        return page
    
    def create_album_detail_page(self):
        """Page showing tracks in an album"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with album info
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_widget.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #e74c3c, stop:0.5 #c0392b, stop:1 #e74c3c);
        """)
        
        # Back button
        back_btn = QPushButton("< Back")
        back_btn.setFixedWidth(int(self.screen_width * 0.2))
        back_btn.clicked.connect(self.go_back_from_detail)
        back_btn.setStyleSheet(f"""
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid white;
            font-size: {int(self.screen_height * 0.03)}px;
        """)
        header_layout.addWidget(back_btn)
        
        # Album info
        self.detail_album_label = QLabel("")
        self.detail_album_label.setAlignment(Qt.AlignCenter)
        self.detail_album_label.setStyleSheet(f"""
            font-size: {int(self.screen_height * 0.045)}px;
            font-weight: bold;
            color: white;
        """)
        header_layout.addWidget(self.detail_album_label, 1)
        
        # Favorite button
        self.favorite_btn = QPushButton("♡")
        self.favorite_btn.setFixedWidth(int(self.screen_width * 0.15))
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        self.favorite_btn.setStyleSheet(f"""
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid white;
            font-size: {int(self.screen_height * 0.05)}px;
        """)
        header_layout.addWidget(self.favorite_btn)
        
        layout.addWidget(header_widget)
        
        # Track list
        self.track_list = QListWidget()
        self.track_list.itemClicked.connect(self.play_selected_track)
        layout.addWidget(self.track_list)
        
        return page
    
    def create_now_playing_page(self):
        """Now playing page with album art and controls"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Back button
        back_btn = QPushButton("< Back")
        back_btn.setFixedHeight(int(self.screen_height * 0.08))
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        layout.addWidget(back_btn)
        
        # Album art
        self.album_art = QLabel()
        self.album_art.setAlignment(Qt.AlignCenter)
        art_size = int(min(self.screen_width, self.screen_height) * 0.5)
        self.album_art.setFixedSize(art_size, art_size)
        self.album_art.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #34495e, stop:1 #2c3e50);
            border: 3px solid rgba(236, 240, 241, 0.2);
            border-radius: 15px;
        """)
        self.set_placeholder_art(art_size)
        layout.addWidget(self.album_art, alignment=Qt.AlignCenter)
        
        # Track info
        self.track_label = QLabel("No track")
        self.track_label.setAlignment(Qt.AlignCenter)
        self.track_label.setWordWrap(True)
        self.track_label.setStyleSheet(f"""
            color: #ecf0f1;
            font-size: {int(self.screen_height * 0.045)}px;
            font-weight: bold;
            padding: 5px;
        """)
        layout.addWidget(self.track_label)
        
        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setStyleSheet(f"""
            color: #95a5a6;
            font-size: {int(self.screen_height * 0.035)}px;
            padding: 5px;
        """)
        layout.addWidget(self.artist_label)
        
        # Progress bar
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet(f"""
            font-size: {int(self.screen_height * 0.03)}px;
            color: #7f8c8d;
            font-family: 'Courier New', monospace;
        """)
        layout.addWidget(self.time_label)
        
        from PyQt5.QtWidgets import QSlider
        self.progress = QSlider(Qt.Horizontal)
        self.progress.sliderMoved.connect(self.seek)
        layout.addWidget(self.progress)
        
        # Transport controls
        controls = QHBoxLayout()
        controls.setSpacing(15)
        
        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        
        btn_size = int(self.screen_height * 0.12)
        play_size = int(self.screen_height * 0.15)
        
        self.prev_btn.setFixedSize(btn_size, btn_size)
        self.play_btn.setFixedSize(play_size, play_size)
        self.next_btn.setFixedSize(btn_size, btn_size)
        
        side_button_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #34495e, stop:1 #2c3e50);
                border: 2px solid rgba(236, 240, 241, 0.2);
                border-radius: {btn_size // 2}px;
                color: #ecf0f1;
                font-size: {int(self.screen_height * 0.045)}px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #445d78, stop:1 #34495e);
            }}
        """
        
        play_button_style = f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #e74c3c, stop:1 #c0392b);
                border: 3px solid rgba(255, 255, 255, 0.3);
                border-radius: {play_size // 2}px;
                color: white;
                font-size: {int(self.screen_height * 0.055)}px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ff5e4d, stop:1 #e74c3c);
            }}
        """
        
        self.prev_btn.setStyleSheet(side_button_style)
        self.play_btn.setStyleSheet(play_button_style)
        self.next_btn.setStyleSheet(side_button_style)
        
        self.prev_btn.clicked.connect(self.prev_track)
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn.clicked.connect(self.next_track)
        
        controls.addStretch()
        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch()
        
        layout.addLayout(controls)
        
        return page
    
    def create_header(self, title, back_action):
        """Create a standard header with back button"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(15, 10, 15, 10)
        header.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #e74c3c, stop:0.5 #c0392b, stop:1 #e74c3c);
        """)
        
        back_btn = QPushButton("< Back")
        back_btn.setFixedWidth(int(self.screen_width * 0.25))
        back_btn.clicked.connect(back_action)
        back_btn.setStyleSheet(f"""
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid white;
            font-size: {int(self.screen_height * 0.035)}px;
        """)
        layout.addWidget(back_btn)
        
        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"""
            font-size: {int(self.screen_height * 0.05)}px;
            font-weight: bold;
            color: white;
            letter-spacing: 2px;
        """)
        layout.addWidget(label, 1)
        
        # Spacer to center title
        layout.addWidget(QLabel(), 0)
        layout.itemAt(2).widget().setFixedWidth(int(self.screen_width * 0.25))
        
        return header
    
    def scan_music_library(self):
        """Scan music library and organize by album metadata"""
        if not os.path.isdir(self.music_root):
            return
            
        print("Scanning music library...")
        
        for root, dirs, files in os.walk(self.music_root):
            for file in files:
                if file.lower().endswith(('.flac', '.mp3', '.m4a', '.ogg')):
                    file_path = os.path.join(root, file)
                    try:
                        metadata = self.get_metadata(file_path)
                        album = metadata.get('album', 'Unknown Album')
                        artist = metadata.get('artist', 'Unknown Artist')
                        
                        if album not in self.albums:
                            self.albums[album] = []
                            self.album_metadata[album] = {
                                'artist': artist,
                                'art': None
                            }
                        
                        self.albums[album].append(file_path)
                        
                        # Store album art from first track
                        if self.album_metadata[album]['art'] is None:
                            self.album_metadata[album]['art'] = metadata.get('art')
                        
                        # Track artists
                        if artist not in self.artists:
                            self.artists[artist] = []
                        if album not in self.artists[artist]:
                            self.artists[artist].append(album)
                            
                    except Exception as e:
                        print(f"Error reading {file_path}: {e}")
        
        # Sort tracks within each album
        for album in self.albums:
            self.albums[album].sort(key=lambda x: self.get_track_number(x))
        
        # Populate lists
        self.populate_lists()
        print(f"Found {len(self.albums)} albums, {len(self.artists)} artists")
    
    def get_metadata(self, path):
        """Extract metadata from audio file"""
        metadata = {
            'title': 'Unknown',
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'track': 0,
            'art': None
        }
        
        try:
            audio = File(path)
            
            if isinstance(audio, FLAC):
                metadata['title'] = audio.get('title', ['Unknown'])[0]
                metadata['artist'] = audio.get('artist', ['Unknown Artist'])[0]
                metadata['album'] = audio.get('album', ['Unknown Album'])[0]
                track = audio.get('tracknumber', ['0'])[0]
                metadata['track'] = int(str(track).split('/')[0]) if track else 0
                
                if audio.pictures:
                    metadata['art'] = audio.pictures[0].data
                    
            elif isinstance(audio, MP3):
                metadata['title'] = str(audio.get('TIT2', 'Unknown'))
                metadata['artist'] = str(audio.get('TPE1', 'Unknown Artist'))
                metadata['album'] = str(audio.get('TALB', 'Unknown Album'))
                track = str(audio.get('TRCK', '0'))
                metadata['track'] = int(track.split('/')[0]) if track else 0
                
                for tag in audio.tags.values():
                    if hasattr(tag, 'mime') and 'image' in tag.mime:
                        metadata['art'] = tag.data
                        break
            else:
                if hasattr(audio, 'tags') and audio.tags:
                    metadata['title'] = str(audio.tags.get('title', ['Unknown'])[0])
                    metadata['artist'] = str(audio.tags.get('artist', ['Unknown Artist'])[0])
                    metadata['album'] = str(audio.tags.get('album', ['Unknown Album'])[0])
                    
        except Exception as e:
            print(f"Metadata error for {path}: {e}")
            
        return metadata
    
    def get_track_number(self, path):
        """Get track number for sorting"""
        try:
            metadata = self.get_metadata(path)
            return metadata.get('track', 999)
        except:
            return 999
    
    def populate_lists(self):
        """Populate all list widgets"""
        # Albums
        self.album_list.clear()
        for album in sorted(self.albums.keys()):
            artist = self.album_metadata[album]['artist']
            item = QListWidgetItem(f"{album}\n{artist}")
            item.setData(Qt.UserRole, album)
            self.album_list.addItem(item)
        
        # Artists
        self.artist_list.clear()
        for artist in sorted(self.artists.keys()):
            album_count = len(self.artists[artist])
            item = QListWidgetItem(f"{artist}\n{album_count} album{'s' if album_count != 1 else ''}")
            item.setData(Qt.UserRole, artist)
            self.artist_list.addItem(item)
        
        # Favorites
        self.update_favorites_list()
    
    def update_favorites_list(self):
        """Update the favorites list"""
        self.favorites_list.clear()
        for album in self.favorites:
            if album in self.albums:
                artist = self.album_metadata[album]['artist']
                item = QListWidgetItem(f"{album}\n{artist}")
                item.setData(Qt.UserRole, album)
                self.favorites_list.addItem(item)
    
    def show_album_detail(self, item):
        """Show album detail page with tracks"""
        album = item.data(Qt.UserRole)
        self.current_album = album
        self.current_tracks = self.albums[album]
        
        # Update header
        artist = self.album_metadata[album]['artist']
        self.detail_album_label.setText(f"{album}\n{artist}")
        
        # Update favorite button
        if album in self.favorites:
            self.favorite_btn.setText("♥")
            self.favorite_btn.setStyleSheet(self.favorite_btn.styleSheet() + "color: #e74c3c;")
        else:
            self.favorite_btn.setText("♡")
        
        # Populate track list
        self.track_list.clear()
        for i, track_path in enumerate(self.current_tracks):
            metadata = self.get_metadata(track_path)
            title = metadata['title']
            track_num = metadata.get('track', i + 1)
            item = QListWidgetItem(f"{track_num}. {title}")
            item.setData(Qt.UserRole, i)
            self.track_list.addItem(item)
        
        self.stack.setCurrentIndex(4)
        self.previous_page = self.stack.currentIndex()
    
    def show_artist_albums(self, item):
        """Show albums by selected artist"""
        artist = item.data(Qt.UserRole)
        
        # Temporarily filter album list
        self.album_list.clear()
        for album in self.artists[artist]:
            artist_name = self.album_metadata[album]['artist']
            item = QListWidgetItem(f"{album}\n{artist_name}")
            item.setData(Qt.UserRole, album)
            self.album_list.addItem(item)
        
        self.stack.setCurrentIndex(1)
        self.from_artist = True
    
    def go_back_from_detail(self):
        """Go back from album detail page"""
        if hasattr(self, 'from_artist') and self.from_artist:
            self.from_artist = False
            self.stack.setCurrentIndex(2)
        else:
            # Refresh album list
            self.populate_lists()
            self.stack.setCurrentIndex(1)
    
    def play_selected_track(self, item):
        """Play the selected track from track list"""
        track_index = item.data(Qt.UserRole)
        self.play_track(track_index)
        self.stack.setCurrentIndex(5)
    
    def play_track(self, index):
        """Play a specific track"""
        if index < 0 or index >= len(self.current_tracks):
            return
            
        self.current_index = index
        path = self.current_tracks[index]
        
        media = self.instance.media_new(path)
        self.player.set_media(media)
        self.player.play()
        
        self.play_btn.setText("⏸")
        self.update_now_playing(path)
    
    def update_now_playing(self, path):
        """Update the now playing display"""
        metadata = self.get_metadata(path)
        
        self.track_label.setText(metadata['title'])
        self.artist_label.setText(f"{metadata['artist']} • {metadata['album']}")
        
        # Update album art
        art_data = metadata.get('art') or self.album_metadata.get(self.current_album, {}).get('art')
        art_size = int(min(self.screen_width, self.screen_height) * 0.5)
        
        if art_data:
            pixmap = QPixmap()
            pixmap.loadFromData(art_data)
            scaled = pixmap.scaled(art_size, art_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            if scaled.width() != art_size or scaled.height() != art_size:
                final_pixmap = QPixmap(art_size, art_size)
                final_pixmap.fill(QColor("#2c3e50"))
                painter = QPainter(final_pixmap)
                x = (art_size - scaled.width()) // 2
                y = (art_size - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
                painter.end()
                self.album_art.setPixmap(final_pixmap)
            else:
                self.album_art.setPixmap(scaled)
        else:
            self.set_placeholder_art(art_size)
    
    def set_placeholder_art(self, size):
        """Create a gradient placeholder"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        gradient = QLinearGradient(0, 0, size, size)
        gradient.setColorAt(0, QColor("#34495e"))
        gradient.setColorAt(1, QColor("#2c3e50"))
        painter.fillRect(0, 0, size, size, gradient)
        
        painter.setPen(QColor(236, 240, 241, 60))
        font = QFont()
        font.setPointSize(int(size * 0.3))
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignCenter, "♫")
        painter.end()
        
        self.album_art.setPixmap(pixmap)
    
    def toggle_play(self):
        """Toggle play/pause"""
        if self.player.is_playing():
            self.player.pause()
            self.play_btn.setText("▶")
        else:
            self.player.play()
            self.play_btn.setText("⏸")
    
    def next_track(self):
        """Play next track"""
        if self.current_index < len(self.current_tracks) - 1:
            self.play_track(self.current_index + 1)
        else:
            self.play_track(0)
    
    def prev_track(self):
        """Play previous track"""
        if self.player.get_time() > 3000:
            self.player.set_time(0)
        elif self.current_index > 0:
            self.play_track(self.current_index - 1)
        else:
            self.play_track(len(self.current_tracks) - 1)
    
    def update_progress(self):
        """Update progress bar and auto-advance"""
        length = self.player.get_length()
        
        if length > 0:
            self.progress.setMaximum(length)
            current_time = self.player.get_time()
            self.progress.setValue(current_time)
            
            current_str = self.format_time(current_time)
            total_str = self.format_time(length)
            self.time_label.setText(f"{current_str} / {total_str}")
            
            # Auto-advance when track ends
            if current_time >= length - 500 and self.player.is_playing():
                self.next_track()
    
    def format_time(self, ms):
        """Format milliseconds to MM:SS"""
        s = ms // 1000
        return f"{s // 60}:{s % 60:02d}"
    
    def seek(self, value):
        """Seek to position"""
        self.player.set_time(value)
    
    def toggle_favorite(self):
        """Toggle favorite status of current album"""
        if self.current_album in self.favorites:
            self.favorites.remove(self.current_album)
            self.favorite_btn.setText("♡")
        else:
            self.favorites.append(self.current_album)
            self.favorite_btn.setText("♥")
            self.favorite_btn.setStyleSheet(self.favorite_btn.styleSheet() + "color: #e74c3c;")
        
        self.save_favorites()
        self.update_favorites_list()
    
    def load_favorites(self):
        """Load favorites from file"""
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_favorites(self):
        """Save favorites to file"""
        try:
            with open(self.favorites_file, 'w') as f:
                json.dump(self.favorites, f)
        except Exception as e:
            print(f"Error saving favorites: {e}")
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Escape:
            # Go back or exit
            current_page = self.stack.currentIndex()
            if current_page == 0:
                self.close()
            elif current_page in [1, 2, 3]:
                self.stack.setCurrentIndex(0)
            elif current_page == 4:
                self.go_back_from_detail()
            elif current_page == 5:
                self.stack.setCurrentIndex(4)
        elif event.key() == Qt.Key_Space:
            if self.player.get_media():
                self.toggle_play()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Set application to be fullscreen
    app.setOverrideCursor(Qt.BlankCursor)  # Hide mouse cursor
    
    music_folder = os.path.expanduser("~/Music")
    player = MusicPlayerApp(music_folder)
    
    sys.exit(app.exec_())
