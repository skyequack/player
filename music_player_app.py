#!/usr/bin/env python3
import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QLabel, QPushButton, QStackedWidget, QListWidgetItem, QSlider,
    QSizePolicy
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QFont, QColor, QPainter, QGuiApplication
import vlc
from mutagen import File
from mutagen.flac import FLAC
from mutagen.mp3 import MP3


class MusicPlayerApp(QWidget):
    def __init__(self, music_root):
        super().__init__()
        self.music_root = music_root
        self.favorites_file = os.path.expanduser("~/.music_player_favorites.json")

        # Portrait screen dimensions for iPod-style display
        self.SCREEN_WIDTH = 320
        self.SCREEN_HEIGHT = 460

        # VLC
        self.instance = vlc.Instance(["--aout=alsa", "--alsa-audio-device=hw:1,0"])
        self.player = self.instance.media_player_new()

        # Data
        self.albums = {}
        self.album_metadata = {}
        self.artists = {}
        self.favorites = self.load_favorites()

        self.current_tracks = []
        self.current_album = None
        self.current_index = -1
        self.track_ending = False

        # Pagination state
        self.albums_per_page = 8
        self.artists_per_page = 14
        self.favorites_per_page = 10
        self.tracks_per_page = 10
        self.album_page = 0
        self.artist_page = 0
        self.favorites_page = 0
        self.track_page = 0
        self.all_albums = []
        self.all_artists = []
        self.all_tracks_data = []

        # Set fixed size for portrait display
        self.setFixedSize(self.SCREEN_WIDTH, self.SCREEN_HEIGHT)
        self.setWindowTitle("Music Player")

        self.set_minimal_theme()
        self.init_ui()
        self.scan_music_library()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(500)

    # ---------- Helper methods ----------
    def scaled(self, px):
        """No scaling needed - use pixels directly for fixed-size display"""
        return px

    def touch_height(self):
        return 32

    # ---------- Theme ----------
    def set_minimal_theme(self):
        """Apple Music-inspired minimal theme optimized for small portrait screen"""
        self.setStyleSheet("""
        QWidget {
            background-color: #ffffff;
            color: #000000;
            font-family: "Segoe UI", "San Francisco", "Helvetica", Arial;
            font-size: 10px;
        }

        QListWidget {
            border: none;
            padding: 2px;
            outline: none;
        }

        QListWidget::item {
            padding: 6px 8px;
            border-bottom: 1px solid #f0f0f0;
        }

        QListWidget::item:selected {
            background-color: #f5f5f5;
            color: #000000;
        }

        QPushButton {
            background-color: #f8f8f8;
            border: 1px solid #e0e0e0;
            border-radius: 6px;
            padding: 4px 8px;
            min-height: 22px;
            font-size: 10px;
        }

        QPushButton:pressed {
            background-color: #e8e8e8;
        }

        QPushButton#accent {
            background-color: #007AFF;
            color: white;
            border: none;
            font-weight: 500;
        }

        QPushButton#accent:pressed {
            background-color: #0051D5;
        }

        QSlider::groove:horizontal {
            height: 3px;
            background: #e8e8e8;
            border-radius: 1px;
        }

        QSlider::sub-page:horizontal {
            background: #007AFF;
            border-radius: 1px;
        }

        QSlider::handle:horizontal {
            background: #ffffff;
            border: 1px solid #007AFF;
            width: 12px;
            height: 12px;
            margin: -5px 0;
            border-radius: 6px;
        }
        """)

    # ---------- UI ----------
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.landing_page = self.create_landing_page()
        self.albums_page = self.create_albums_page()
        self.artists_page = self.create_artists_page()
        self.favorites_page = self.create_favorites_page()
        self.album_detail_page = self.create_album_detail_page()
        self.now_playing_page = self.create_now_playing_page()

        for p in [
            self.landing_page, self.albums_page, self.artists_page,
            self.favorites_page, self.album_detail_page,
            self.now_playing_page
        ]:
            self.stack.addWidget(p)

    def create_header(self, title, back_action):
        header = QWidget()
        header.setFixedHeight(40)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 6, 8, 6)

        back_btn = QPushButton("‹ Back")
        back_btn.setFixedWidth(60)
        back_btn.clicked.connect(back_action)
        layout.addWidget(back_btn)

        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 11px; font-weight: 600;")
        layout.addWidget(label, 1)

        spacer = QLabel()
        spacer.setFixedWidth(60)
        layout.addWidget(spacer)
        return header

    def create_pagination_footer(self, prev_action, next_action):
        footer = QWidget()
        footer.setFixedHeight(36)
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(8, 4, 8, 4)

        prev_btn = QPushButton("‹ Prev")
        prev_btn.setFixedWidth(60)
        prev_btn.clicked.connect(prev_action)
        layout.addWidget(prev_btn)

        page_label = QLabel("Page 1/1")
        page_label.setObjectName("page_label")
        page_label.setAlignment(Qt.AlignCenter)
        page_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(page_label, 1)

        next_btn = QPushButton("Next ›")
        next_btn.setFixedWidth(60)
        next_btn.clicked.connect(next_action)
        layout.addWidget(next_btn)

        return footer

    def create_landing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 40, 16, 16)

        title = QLabel("Music")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 700; color: #000000;")
        layout.addWidget(title)
        
        layout.addSpacing(20)

        btn_albums = QPushButton("Albums")
        btn_artists = QPushButton("Artists")
        btn_favorites = QPushButton("Favorites")

        for b in [btn_albums, btn_artists, btn_favorites]:
            b.setObjectName("accent")
            b.setFixedHeight(33)

        btn_albums.clicked.connect(self.show_albums_page)
        btn_artists.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_favorites.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        layout.addWidget(btn_albums)
        layout.addWidget(btn_artists)
        layout.addWidget(btn_favorites)
        
        layout.addStretch()

        btn_exit = QPushButton("Exit")
        btn_exit.setFixedHeight(27)
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)
        
        layout.addSpacing(12)

        return page

    def create_albums_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_header("Albums",
                                            lambda: self.stack.setCurrentIndex(0)))

        self.album_list = QListWidget()
        self.album_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.album_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.album_list.setMaximumHeight(340)
        self.album_list.itemClicked.connect(self.show_album_detail)
        layout.addWidget(self.album_list)

        # Pagination footer
        footer = self.create_pagination_footer(
            lambda: self.prev_page('albums'),
            lambda: self.next_page('albums')
        )
        self.album_page_label = footer.findChild(QLabel, "page_label")
        layout.addWidget(footer)

        return page

    def create_artists_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_header("Artists",
                                            lambda: self.stack.setCurrentIndex(0)))

        self.artist_list = QListWidget()
        self.artist_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.artist_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.artist_list.setMaximumHeight(340)
        self.artist_list.itemClicked.connect(self.show_artist_albums)
        layout.addWidget(self.artist_list)

        # Pagination footer
        footer = self.create_pagination_footer(
            lambda: self.prev_page('artists'),
            lambda: self.next_page('artists')
        )
        self.artist_page_label = footer.findChild(QLabel, "page_label")
        layout.addWidget(footer)

        return page

    def create_favorites_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_header("Favorites",
                                            lambda: self.stack.setCurrentIndex(0)))

        self.favorites_list = QListWidget()
        self.favorites_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.favorites_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.favorites_list.setMaximumHeight(340)
        self.favorites_list.itemClicked.connect(self.show_album_detail)
        layout.addWidget(self.favorites_list)

        # Pagination footer
        footer = self.create_pagination_footer(
            lambda: self.prev_page('favorites'),
            lambda: self.next_page('favorites')
        )
        self.favorites_page_label = footer.findChild(QLabel, "page_label")
        layout.addWidget(footer)

        return page

    def create_album_detail_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(40)
        h = QHBoxLayout(header)
        h.setContentsMargins(4, 4, 4, 4)

        back_btn = QPushButton("‹ Back")
        back_btn.setFixedWidth(60)
        back_btn.clicked.connect(self.go_back_from_detail)
        h.addWidget(back_btn)

        self.detail_album_label = QLabel("")
        self.detail_album_label.setAlignment(Qt.AlignCenter)
        self.detail_album_label.setStyleSheet(
            "font-size: 10px; font-weight: 600;"
        )
        h.addWidget(self.detail_album_label, 1)

        self.favorite_btn = QPushButton("♡")
        self.favorite_btn.setFixedWidth(40)
        self.favorite_btn.setStyleSheet("font-size: 16px;")
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        h.addWidget(self.favorite_btn)

        layout.addWidget(header)

        self.track_list = QListWidget()
        self.track_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.track_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.track_list.setMaximumHeight(340)
        self.track_list.itemClicked.connect(self.play_selected_track)
        layout.addWidget(self.track_list)

        # Pagination footer
        footer = self.create_pagination_footer(
            lambda: self.prev_page('tracks'),
            lambda: self.next_page('tracks')
        )
        self.track_page_label = footer.findChild(QLabel, "page_label")
        layout.addWidget(footer)

        return page

    def create_now_playing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 20)
        layout.setSpacing(1)

        # Header with back button
        header = QWidget()
        header.setFixedHeight(24)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 2, 8, 2)
        
        back_btn = QPushButton("‹")
        back_btn.setFixedSize(32, 24)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        h_layout.addWidget(back_btn)
        h_layout.addStretch()
        
        layout.addWidget(header)

        # Album art - fixed size for small portrait screen
        art_container = QWidget()
        art_layout = QVBoxLayout(art_container)
        art_layout.setContentsMargins(16, 0, 16, 0)
        
        self.album_art = QLabel()
        self.album_art.setAlignment(Qt.AlignCenter)
        self.album_art.setFixedSize(160, 160)  # Reduced for 320px wide screen
        self.album_art.setScaledContents(False)
        art_layout.addWidget(self.album_art, alignment=Qt.AlignCenter)
        
        layout.addWidget(art_container)

        # Track info
        self.track_label = QLabel("No track")
        self.track_label.setAlignment(Qt.AlignCenter)
        self.track_label.setWordWrap(True)
        self.track_label.setStyleSheet(
            "font-size: 12px; font-weight: 600; padding: 0 12px; max-height: 36px;"
        )
        layout.addWidget(self.track_label)

        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignCenter)
        self.artist_label.setWordWrap(True)
        self.artist_label.setStyleSheet("font-size: 9px; color: #666; padding: 0 12px; max-height: 24px;")
        layout.addWidget(self.artist_label)

        # Progress slider
        slider_container = QWidget()
        slider_layout = QVBoxLayout(slider_container)
        slider_layout.setContentsMargins(12, 2, 12, 2)
        slider_layout.setSpacing(1)
        
        self.progress = QSlider(Qt.Horizontal)
        self.progress.sliderMoved.connect(self.seek)
        slider_layout.addWidget(self.progress)
        
        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("font-size: 9px; color: #888;")
        slider_layout.addWidget(self.time_label)
        
        layout.addWidget(slider_container)
        
        # Add space before control buttons
        layout.addSpacing(12)

        # Control buttons
        controls = QHBoxLayout()
        controls.setSpacing(16)

        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("►")
        self.next_btn = QPushButton("⏭")

        # Larger round buttons
        self.prev_btn.setFixedSize(40, 40)
        self.play_btn.setFixedSize(50, 50)
        self.next_btn.setFixedSize(40, 40)
        
        self.prev_btn.setStyleSheet("border-radius: 20px; font-size: 13px;")
        self.play_btn.setStyleSheet("border-radius: 25px; font-size: 16px;")
        self.next_btn.setStyleSheet("border-radius: 20px; font-size: 13px;")

        self.play_btn.setObjectName("accent")

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

    # ---------- No resize needed for fixed-size window ----------

    # ---------- Music scan ----------
    def scan_music_library(self):
        if not os.path.isdir(self.music_root):
            return

        for root, _, files in os.walk(self.music_root):
            for file in files:
                if file.lower().endswith(('.flac', '.mp3', '.m4a', '.ogg')):
                    path = os.path.join(root, file)
                    meta = self.get_metadata(path)

                    album = meta['album']
                    artist = meta['artist']

                    self.albums.setdefault(album, []).append(path)
                    self.album_metadata.setdefault(album, {
                        'artist': artist,
                        'art': meta.get('art')
                    })

                    self.artists.setdefault(artist, [])
                    if album not in self.artists[artist]:
                        self.artists[artist].append(album)

        for album in self.albums:
            self.albums[album].sort(key=self.get_track_number)

        self.populate_lists()

    # ---------- Metadata ----------
    def get_metadata(self, path):
        meta = {
            'title': 'Unknown',
            'artist': 'Unknown Artist',
            'album': 'Unknown Album',
            'track': 0,
            'art': None
        }

        try:
            audio = File(path)

            if isinstance(audio, FLAC):
                meta['title'] = audio.get('title', ['Unknown'])[0]
                meta['artist'] = audio.get('artist', ['Unknown Artist'])[0]
                meta['album'] = audio.get('album', ['Unknown Album'])[0]
                # FIX: Extract track number from FLAC
                track_num = audio.get('tracknumber', ['0'])[0]
                try:
                    # Handle "1/10" format
                    meta['track'] = int(str(track_num).split('/')[0])
                except (ValueError, IndexError):
                    meta['track'] = 0
                
                if audio.pictures:
                    meta['art'] = audio.pictures[0].data

            elif isinstance(audio, MP3):
                # FIX: Properly access MP3 ID3 tags
                meta['title'] = str(audio.get('TIT2', 'Unknown'))
                if 'TIT2' in audio and hasattr(audio['TIT2'], 'text'):
                    meta['title'] = audio['TIT2'].text[0]

                meta['artist'] = str(audio.get('TPE1', 'Unknown Artist'))
                if 'TPE1' in audio and hasattr(audio['TPE1'], 'text'):
                    meta['artist'] = audio['TPE1'].text[0]

                meta['album'] = str(audio.get('TALB', 'Unknown Album'))
                if 'TALB' in audio and hasattr(audio['TALB'], 'text'):
                    meta['album'] = audio['TALB'].text[0]
                
                # FIX: Extract track number from MP3
                if 'TRCK' in audio and hasattr(audio['TRCK'], 'text'):
                    track_num = audio['TRCK'].text[0]
                    try:
                        meta['track'] = int(str(track_num).split('/')[0])
                    except (ValueError, IndexError):
                        meta['track'] = 0
                
                # FIX: Extract album art from MP3
                if audio.tags:
                    apic_frames = audio.tags.getall('APIC')
                    if apic_frames:
                        meta['art'] = apic_frames[0].data

            if meta['art'] is None:
                meta['art'] = self.load_folder_art(path)

        except Exception:
            pass

        return meta

    def load_folder_art(self, path):
        folder = os.path.dirname(path)
        candidates = [
            "cover.jpg", "cover.png",
            "folder.jpg", "folder.png",
            "front.jpg", "front.png",
            "album.jpg", "album.png",
            "artwork.jpg", "artwork.png"
        ]

        try:
            entries = os.listdir(folder)
        except Exception:
            return None

        lookup = {name.lower(): name for name in entries}
        for name in candidates:
            actual = lookup.get(name)
            if not actual:
                continue
            file_path = os.path.join(folder, actual)
            try:
                with open(file_path, "rb") as f:
                    return f.read()
            except Exception:
                continue

        return None

    def get_track_number(self, path):
        return self.get_metadata(path).get('track', 999)

    # ---------- Pagination ----------
    def prev_page(self, list_type):
        if list_type == 'albums' and self.album_page > 0:
            self.album_page -= 1
            self.update_album_page()
        elif list_type == 'artists' and self.artist_page > 0:
            self.artist_page -= 1
            self.update_artist_page()
        elif list_type == 'favorites' and self.favorites_page > 0:
            self.favorites_page -= 1
            self.update_favorites_page()
        elif list_type == 'tracks' and self.track_page > 0:
            self.track_page -= 1
            self.update_track_page()

    def next_page(self, list_type):
        if list_type == 'albums':
            max_page = (len(self.all_albums) - 1) // self.albums_per_page
            if self.album_page < max_page:
                self.album_page += 1
                self.update_album_page()
        elif list_type == 'artists':
            max_page = (len(self.all_artists) - 1) // self.artists_per_page
            if self.artist_page < max_page:
                self.artist_page += 1
                self.update_artist_page()
        elif list_type == 'favorites':
            fav_albums = [a for a in self.favorites if a in self.albums]
            max_page = (len(fav_albums) - 1) // self.favorites_per_page if fav_albums else 0
            if self.favorites_page < max_page:
                self.favorites_page += 1
                self.update_favorites_page()
        elif list_type == 'tracks':
            max_page = (len(self.all_tracks_data) - 1) // self.tracks_per_page
            if self.track_page < max_page:
                self.track_page += 1
                self.update_track_page()

    # ---------- Lists ----------
    def populate_lists(self):
        self.all_albums = sorted(self.albums.keys())
        self.all_artists = sorted(self.artists.keys())
        self.album_page = 0
        self.artist_page = 0
        self.favorites_page = 0
        
        self.update_album_page()
        self.update_artist_page()
        self.update_favorites_page()

    def update_album_page(self):
        self.album_list.clear()
        start = self.album_page * self.albums_per_page
        end = start + self.albums_per_page
        page_albums = self.all_albums[start:end]
        
        for album in page_albums:
            artist = self.album_metadata[album]['artist']
            item = QListWidgetItem(f"{album}\n{artist}")
            item.setData(Qt.UserRole, album)
            self.album_list.addItem(item)
        
        total_pages = max(1, (len(self.all_albums) + self.albums_per_page - 1) // self.albums_per_page)
        self.album_page_label.setText(f"Page {self.album_page + 1}/{total_pages}")

    def update_artist_page(self):
        self.artist_list.clear()
        start = self.artist_page * self.artists_per_page
        end = start + self.artists_per_page
        page_artists = self.all_artists[start:end]
        
        for artist in page_artists:
            item = QListWidgetItem(artist)
            item.setData(Qt.UserRole, artist)
            self.artist_list.addItem(item)
        
        total_pages = max(1, (len(self.all_artists) + self.artists_per_page - 1) // self.artists_per_page)
        self.artist_page_label.setText(f"Page {self.artist_page + 1}/{total_pages}")

    def update_favorites_page(self):
        self.favorites_list.clear()
        fav_albums = [a for a in self.favorites if a in self.albums]
        
        start = self.favorites_page * self.favorites_per_page
        end = start + self.favorites_per_page
        page_favorites = fav_albums[start:end]
        
        for album in page_favorites:
            artist = self.album_metadata[album]['artist']
            item = QListWidgetItem(f"{album}\n{artist}")
            item.setData(Qt.UserRole, album)
            self.favorites_list.addItem(item)
        
        total_pages = max(1, (len(fav_albums) + self.favorites_per_page - 1) // self.favorites_per_page)
        self.favorites_page_label.setText(f"Page {self.favorites_page + 1}/{total_pages}")

    def update_track_page(self):
        self.track_list.clear()
        start = self.track_page * self.tracks_per_page
        end = start + self.tracks_per_page
        page_tracks = self.all_tracks_data[start:end]
        
        for track_idx, track_title in page_tracks:
            item = QListWidgetItem(track_title)
            item.setData(Qt.UserRole, track_idx)
            self.track_list.addItem(item)
        
        total_pages = max(1, (len(self.all_tracks_data) + self.tracks_per_page - 1) // self.tracks_per_page)
        self.track_page_label.setText(f"Page {self.track_page + 1}/{total_pages}")



    # ---------- Navigation ----------
    def show_albums_page(self):
        """Navigate to albums page and reset to show all albums"""
        self.all_albums = sorted(self.albums.keys())
        self.album_page = 0
        self.update_album_page()
        self.stack.setCurrentIndex(1)

    def show_album_detail(self, item):
        album = item.data(Qt.UserRole)
        self.current_album = album
        self.current_tracks = self.albums[album]

        artist = self.album_metadata[album]['artist']
        self.detail_album_label.setText(f"{album}\n{artist}")

        # FIX: Update favorite button to show current state
        self.update_favorite_button()

        # Build track data for pagination
        self.all_tracks_data = []
        for i, path in enumerate(self.current_tracks):
            meta = self.get_metadata(path)
            self.all_tracks_data.append((i, f"{i+1}. {meta['title']}"))
        
        self.track_page = 0
        self.update_track_page()

        self.stack.setCurrentIndex(4)

    def show_artist_albums(self, item):
        artist = item.data(Qt.UserRole)
        self.all_albums = sorted(self.artists[artist])
        self.album_page = 0
        self.update_album_page()
        self.stack.setCurrentIndex(1)

    def go_back_from_detail(self):
        self.all_albums = sorted(self.albums.keys())
        self.album_page = 0
        self.update_album_page()
        self.stack.setCurrentIndex(1)

    # ---------- Playback ----------
    def play_selected_track(self, item):
        self.play_track(item.data(Qt.UserRole))
        self.stack.setCurrentIndex(5)

    def play_track(self, index):
        if index < 0 or index >= len(self.current_tracks):
            return

        self.current_index = index
        self.track_ending = False  # FIX: Reset flag when playing new track
        path = self.current_tracks[index]

        media = self.instance.media_new(path)
        self.player.set_media(media)
        self.player.play()

        self.play_btn.setText("❚❚")
        self.update_now_playing(path)

    def update_now_playing(self, path):
        meta = self.get_metadata(path)
        self.track_label.setText(meta['title'])
        self.artist_label.setText(f"{meta['artist']} • {meta['album']}")

        art = meta.get('art')
        size = 160  # Reduced size for portrait screen

        if art:
            pix = QPixmap()
            pix.loadFromData(art)
            self.album_art.setPixmap(
                pix.scaled(size, size, Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
            )
        else:
            self.set_placeholder_art(size)

    def set_placeholder_art(self, size):
        pix = QPixmap(size, size)
        pix.fill(QColor("#f0f0f0"))

        painter = QPainter(pix)
        painter.setPen(QColor("#9e9e9e"))

        font = QFont()
        font.setPointSize(int(size * 0.25))
        painter.setFont(font)

        painter.drawText(0, 0, size, size, Qt.AlignCenter, "♪")
        painter.end()

        self.album_art.setPixmap(pix)

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.play_btn.setText("►")
        else:
            self.player.play()
            self.play_btn.setText("❚❚")

    def next_track(self):
        self.play_track((self.current_index + 1) % len(self.current_tracks))

    def prev_track(self):
        self.play_track((self.current_index - 1) % len(self.current_tracks))

    # ---------- Progress ----------
    def update_progress(self):
        length = self.player.get_length()
        if length <= 0:
            return

        self.progress.setMaximum(length)
        cur = self.player.get_time()
        self.progress.setValue(cur)

        self.time_label.setText(
            f"{self.format_time(cur)} / {self.format_time(length)}"
        )

        # FIX: Prevent duplicate auto-advance with flag
        if cur >= length - 500 and self.player.is_playing() and not self.track_ending:
            self.track_ending = True
            self.next_track()

    def format_time(self, ms):
        s = ms // 1000
        return f"{s//60}:{s%60:02d}"

    def seek(self, value):
        self.player.set_time(value)

    # ---------- Favorites ----------
    def toggle_favorite(self):
        if self.current_album in self.favorites:
            self.favorites.remove(self.current_album)
        else:
            self.favorites.append(self.current_album)

        self.save_favorites()
        self.update_favorites_page()
        # FIX: Update button after toggling
        self.update_favorite_button()

    def update_favorite_button(self):
        """FIX: Update favorite button to show filled/unfilled heart"""
        if self.current_album in self.favorites:
            self.favorite_btn.setText("♥")  # Filled heart
        else:
            self.favorite_btn.setText("♡")  # Empty heart

    def load_favorites(self):
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def save_favorites(self):
        try:
            with open(self.favorites_file, "w") as f:
                json.dump(self.favorites, f)
        except Exception:
            pass

    # ---------- Keyboard ----------
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        elif event.key() == Qt.Key_Space:
            self.toggle_play()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    music_folder = os.path.expanduser("~/Music")
    player = MusicPlayerApp(music_folder)
    player.show()
    sys.exit(app.exec_())