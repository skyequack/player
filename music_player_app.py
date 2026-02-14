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

        # Landscape screen dimensions
        self.SCREEN_WIDTH = 480
        self.SCREEN_HEIGHT = 280

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
        self.now_playing_sidebars = []
        self.sidebar_play_buttons = []

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

        # Set fixed size for landscape display
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
            font-size: 11px;
        }

        QListWidget {
            border: none;
            padding: 2px;
            outline: none;
        }

        QListWidget::item {
            padding: 6px 10px;
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
            min-height: 28px;
            font-size: 11px;
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
            height: 4px;
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
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
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
        header.setFixedHeight(32)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(8, 6, 8, 6)

        back_btn = QPushButton("‹ Back")
        back_btn.setFixedWidth(60)
        back_btn.clicked.connect(back_action)
        layout.addWidget(back_btn)

        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet("font-size: 12px; font-weight: 600;")
        layout.addWidget(label, 1)

        spacer = QLabel()
        spacer.setFixedWidth(60)
        layout.addWidget(spacer)
        return header

    def create_now_playing_sidebar(self):
        container = QWidget()
        container.setStyleSheet(
            "background-color: #fafafa; border: 1px solid #ededed; "
            "border-radius: 8px;"
        )
        container.setFixedHeight(120)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        title = QLabel("Now Playing")
        title.setStyleSheet("font-size: 11px; font-weight: 600;")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(6)

        art = QLabel()
        art.setAlignment(Qt.AlignCenter)
        art.setFixedSize(56, 56)
        row.addWidget(art)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        track = QLabel("Nothing playing")
        track.setWordWrap(True)
        track.setStyleSheet("font-size: 11px; font-weight: 600;")
        text_col.addWidget(track)

        artist = QLabel("")
        artist.setWordWrap(True)
        artist.setStyleSheet("font-size: 10px; color: #666;")
        text_col.addWidget(artist)

        row.addLayout(text_col)
        row.addStretch()
        layout.addLayout(row)

        controls = QHBoxLayout()
        controls.setSpacing(6)

        prev_btn = QPushButton("⏮")
        play_btn = QPushButton("▶")
        next_btn = QPushButton("⏭")

        for btn in [prev_btn, play_btn, next_btn]:
            btn.setFixedSize(28, 24)
            btn.setStyleSheet("border-radius: 6px; font-size: 10px;")

        prev_btn.clicked.connect(self.prev_track)
        play_btn.clicked.connect(self.toggle_play)
        next_btn.clicked.connect(self.next_track)

        controls.addWidget(prev_btn)
        controls.addWidget(play_btn)
        controls.addWidget(next_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.now_playing_sidebars.append({
            "art": art,
            "track": track,
            "artist": artist
        })
        self.sidebar_play_buttons.append(play_btn)
        self.set_preview_art(art, None, 56)

        return container

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
        layout = QHBoxLayout(page)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        title = QLabel("Music")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 700; color: #000000;")
        left_col.addWidget(title)

        tagline = QLabel("Your library, wide view")
        tagline.setStyleSheet("font-size: 11px; color: #666;")
        left_col.addWidget(tagline)

        left_col.addStretch()

        btn_exit = QPushButton("Exit")
        btn_exit.setFixedHeight(32)
        btn_exit.clicked.connect(self.close)
        left_col.addWidget(btn_exit)

        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        btn_albums = QPushButton("Albums")
        btn_artists = QPushButton("Artists")
        btn_favorites = QPushButton("Favorites")

        for b in [btn_albums, btn_artists, btn_favorites]:
            b.setObjectName("accent")
            b.setFixedHeight(40)

        btn_albums.clicked.connect(self.show_albums_page)
        btn_artists.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_favorites.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        right_col.addWidget(btn_albums)
        right_col.addWidget(btn_artists)
        right_col.addWidget(btn_favorites)
        right_col.addStretch()

        layout.addLayout(left_col, 1)
        layout.addLayout(right_col, 1)

        return page

    def create_albums_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self.create_header("Albums",
                                            lambda: self.stack.setCurrentIndex(0)))

        content = QHBoxLayout()
        content.setSpacing(10)

        self.album_list = QListWidget()
        self.album_list.itemClicked.connect(self.update_album_preview)
        self.album_list.itemDoubleClicked.connect(self.show_album_detail)
        self.album_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.album_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        content.addWidget(self.album_list, 3)

        preview = QWidget()
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(6)

        self.album_preview_art = QLabel()
        self.album_preview_art.setAlignment(Qt.AlignCenter)
        self.album_preview_art.setFixedSize(160, 160)
        preview_layout.addWidget(self.album_preview_art, alignment=Qt.AlignCenter)

        self.album_preview_title = QLabel("Select an album")
        self.album_preview_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.album_preview_title.setWordWrap(True)
        self.album_preview_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        preview_layout.addWidget(self.album_preview_title)

        self.album_preview_artist = QLabel("")
        self.album_preview_artist.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.album_preview_artist.setWordWrap(True)
        self.album_preview_artist.setStyleSheet("font-size: 11px; color: #666;")
        preview_layout.addWidget(self.album_preview_artist)

        preview_layout.addStretch()

        preview_actions = QHBoxLayout()
        self.album_open_btn = QPushButton("Open")
        self.album_play_btn = QPushButton("Play")
        self.album_open_btn.setEnabled(False)
        self.album_play_btn.setEnabled(False)
        self.album_open_btn.clicked.connect(self.open_preview_album)
        self.album_play_btn.clicked.connect(self.play_preview_album)
        preview_actions.addWidget(self.album_open_btn)
        preview_actions.addWidget(self.album_play_btn)
        preview_layout.addLayout(preview_actions)

        preview_layout.addSpacing(4)
        preview_layout.addWidget(self.create_now_playing_sidebar())

        content.addWidget(preview, 2)

        layout.addLayout(content)

        self.album_preview_album = None
        self.set_album_preview(None, self.album_preview_art,
                       self.album_preview_title,
                       self.album_preview_artist,
                       self.album_open_btn,
                       self.album_play_btn,
                       160,
                       "Select an album")

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

        content = QHBoxLayout()
        content.setSpacing(10)

        self.artist_list = QListWidget()
        self.artist_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.artist_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.artist_list.setMaximumHeight(340)
        self.artist_list.itemClicked.connect(self.show_artist_albums)
        content.addWidget(self.artist_list, 2)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)
        right_layout.setSpacing(6)

        self.artist_album_header = QLabel("Select an artist")
        self.artist_album_header.setStyleSheet("font-size: 13px; font-weight: 600;")
        right_layout.addWidget(self.artist_album_header)

        self.artist_album_list = QListWidget()
        self.artist_album_list.itemDoubleClicked.connect(self.show_album_detail)
        right_layout.addWidget(self.artist_album_list)

        right_layout.addSpacing(4)
        right_layout.addWidget(self.create_now_playing_sidebar())

        content.addWidget(right_panel, 3)

        layout.addLayout(content)

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

        content = QHBoxLayout()
        content.setSpacing(10)

        self.favorites_list = QListWidget()
        self.favorites_list.itemClicked.connect(self.update_favorites_preview)
        self.favorites_list.itemDoubleClicked.connect(self.show_album_detail)
        self.favorites_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.favorites_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        content.addWidget(self.favorites_list, 3)

        preview = QWidget()
        preview_layout = QVBoxLayout(preview)
        preview_layout.setContentsMargins(8, 8, 8, 8)
        preview_layout.setSpacing(6)

        self.favorites_preview_art = QLabel()
        self.favorites_preview_art.setAlignment(Qt.AlignCenter)
        self.favorites_preview_art.setFixedSize(160, 160)
        preview_layout.addWidget(self.favorites_preview_art, alignment=Qt.AlignCenter)

        self.favorites_preview_title = QLabel("Select a favorite")
        self.favorites_preview_title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.favorites_preview_title.setWordWrap(True)
        self.favorites_preview_title.setStyleSheet("font-size: 13px; font-weight: 600;")
        preview_layout.addWidget(self.favorites_preview_title)

        self.favorites_preview_artist = QLabel("")
        self.favorites_preview_artist.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.favorites_preview_artist.setWordWrap(True)
        self.favorites_preview_artist.setStyleSheet("font-size: 11px; color: #666;")
        preview_layout.addWidget(self.favorites_preview_artist)

        preview_layout.addStretch()

        preview_actions = QHBoxLayout()
        self.favorites_open_btn = QPushButton("Open")
        self.favorites_play_btn = QPushButton("Play")
        self.favorites_open_btn.setEnabled(False)
        self.favorites_play_btn.setEnabled(False)
        self.favorites_open_btn.clicked.connect(self.open_favorites_preview)
        self.favorites_play_btn.clicked.connect(self.play_favorites_preview)
        preview_actions.addWidget(self.favorites_open_btn)
        preview_actions.addWidget(self.favorites_play_btn)
        preview_layout.addLayout(preview_actions)

        preview_layout.addSpacing(4)
        preview_layout.addWidget(self.create_now_playing_sidebar())

        content.addWidget(preview, 2)

        layout.addLayout(content)

        self.favorites_preview_album = None
        self.set_album_preview(None, self.favorites_preview_art,
                       self.favorites_preview_title,
                       self.favorites_preview_artist,
                       self.favorites_open_btn,
                       self.favorites_play_btn,
                       160,
                       "Select a favorite")

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
        header.setFixedHeight(32)
        h = QHBoxLayout(header)
        h.setContentsMargins(4, 4, 4, 4)

        back_btn = QPushButton("‹ Back")
        back_btn.setFixedWidth(60)
        back_btn.clicked.connect(self.go_back_from_detail)
        h.addWidget(back_btn)

        self.detail_album_label = QLabel("")
        self.detail_album_label.setAlignment(Qt.AlignCenter)
        self.detail_album_label.setStyleSheet(
            "font-size: 11px; font-weight: 600;"
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
        layout = QHBoxLayout(page)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)

        # Left: album art column
        art_container = QWidget()
        art_layout = QVBoxLayout(art_container)
        art_layout.setContentsMargins(0, 0, 0, 0)
        art_layout.setSpacing(6)

        back_row = QHBoxLayout()
        back_btn = QPushButton("‹ Back")
        back_btn.setFixedSize(72, 28)
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        back_row.addWidget(back_btn)
        back_row.addStretch()
        art_layout.addLayout(back_row)

        self.album_art = QLabel()
        self.album_art.setAlignment(Qt.AlignCenter)
        self.album_art.setFixedSize(200, 200)
        self.album_art.setScaledContents(False)
        art_layout.addWidget(self.album_art, alignment=Qt.AlignCenter)
        art_layout.addStretch()

        # Right: track info and controls
        right_col = QVBoxLayout()
        right_col.setSpacing(6)

        self.track_label = QLabel("No track")
        self.track_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.track_label.setWordWrap(True)
        self.track_label.setStyleSheet(
            "font-size: 14px; font-weight: 600; padding-right: 6px;"
        )
        right_col.addWidget(self.track_label)

        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.artist_label.setWordWrap(True)
        self.artist_label.setStyleSheet("font-size: 11px; color: #666;")
        right_col.addWidget(self.artist_label)

        right_col.addStretch()

        slider_container = QWidget()
        slider_layout = QVBoxLayout(slider_container)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(2)

        self.progress = QSlider(Qt.Horizontal)
        self.progress.sliderMoved.connect(self.seek)
        slider_layout.addWidget(self.progress)

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.time_label.setStyleSheet("font-size: 10px; color: #888;")
        slider_layout.addWidget(self.time_label)

        right_col.addWidget(slider_container)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")

        self.prev_btn.setFixedSize(44, 36)
        self.play_btn.setFixedSize(54, 40)
        self.next_btn.setFixedSize(44, 36)

        self.prev_btn.setStyleSheet("border-radius: 18px; font-size: 13px;")
        self.play_btn.setStyleSheet("border-radius: 20px; font-size: 15px;")
        self.next_btn.setStyleSheet("border-radius: 18px; font-size: 13px;")

        self.play_btn.setObjectName("accent")

        self.prev_btn.clicked.connect(self.prev_track)
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn.clicked.connect(self.next_track)

        controls.addWidget(self.prev_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addStretch()

        right_col.addLayout(controls)

        layout.addWidget(art_container, 0)
        layout.addLayout(right_col, 1)
        
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

        if hasattr(self, "album_preview_art"):
            self.album_preview_album = None
            self.set_album_preview(None, self.album_preview_art,
                                   self.album_preview_title,
                                   self.album_preview_artist,
                                   self.album_open_btn,
                                   self.album_play_btn,
                                   160,
                                   "Select an album")

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
        self.artist_album_header.setText("Select an artist")
        self.artist_album_list.clear()

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

        self.favorites_preview_album = None
        self.set_album_preview(None, self.favorites_preview_art,
                               self.favorites_preview_title,
                               self.favorites_preview_artist,
                               self.favorites_open_btn,
                               self.favorites_play_btn,
                               160,
                               "Select a favorite")

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

    def open_album(self, album):
        if album not in self.albums:
            return
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

    def show_album_detail(self, item):
        self.open_album(item.data(Qt.UserRole))

    def show_artist_albums(self, item):
        artist = item.data(Qt.UserRole)
        self.artist_album_header.setText(f"Albums • {artist}")
        self.artist_album_list.clear()

        for album in self.artists[artist]:
            art = self.album_metadata[album]['artist']
            it = QListWidgetItem(f"{album}\n{art}")
            it.setData(Qt.UserRole, album)
            self.artist_album_list.addItem(it)

    def go_back_from_detail(self):
        self.show_albums_page()

    def set_album_preview(self, album, art_label, title_label, artist_label,
                          open_btn, play_btn, size, empty_title):
        if not album or album not in self.album_metadata:
            title_label.setText(empty_title)
            artist_label.setText("")
            open_btn.setEnabled(False)
            play_btn.setEnabled(False)
            self.set_preview_art(art_label, None, size)
            return

        meta = self.album_metadata[album]
        title_label.setText(album)
        artist_label.setText(meta.get('artist', 'Unknown Artist'))
        self.set_preview_art(art_label, meta.get('art'), size)
        open_btn.setEnabled(True)
        play_btn.setEnabled(True)

    def set_preview_art(self, target_label, art, size):
        if art:
            pix = QPixmap()
            pix.loadFromData(art)
            target_label.setPixmap(
                pix.scaled(size, size, Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
            )
        else:
            target_label.setPixmap(self.render_placeholder_pixmap(size))

    def render_placeholder_pixmap(self, size):
        pix = QPixmap(size, size)
        pix.fill(QColor("#f0f0f0"))

        painter = QPainter(pix)
        painter.setPen(QColor("#9e9e9e"))

        font = QFont()
        font.setPointSize(int(size * 0.25))
        painter.setFont(font)

        painter.drawText(0, 0, size, size, Qt.AlignCenter, "♪")
        painter.end()

        return pix

    def update_album_preview(self, item):
        album = item.data(Qt.UserRole)
        self.album_preview_album = album
        self.set_album_preview(album, self.album_preview_art,
                       self.album_preview_title,
                       self.album_preview_artist,
                       self.album_open_btn,
                       self.album_play_btn,
                       160,
                       "Select an album")

    def update_favorites_preview(self, item):
        album = item.data(Qt.UserRole)
        self.favorites_preview_album = album
        self.set_album_preview(album, self.favorites_preview_art,
                       self.favorites_preview_title,
                       self.favorites_preview_artist,
                       self.favorites_open_btn,
                       self.favorites_play_btn,
                       160,
                       "Select a favorite")

    def open_preview_album(self):
        if self.album_preview_album:
            self.open_album(self.album_preview_album)

    def play_preview_album(self):
        if self.album_preview_album:
            self.play_album(self.album_preview_album)

    def open_favorites_preview(self):
        if self.favorites_preview_album:
            self.open_album(self.favorites_preview_album)

    def play_favorites_preview(self):
        if self.favorites_preview_album:
            self.play_album(self.favorites_preview_album)

    def play_album(self, album):
        if album not in self.albums:
            return
        self.current_album = album
        self.current_tracks = self.albums[album]
        self.update_favorite_button()
        if self.current_tracks:
            self.play_track(0)
            self.stack.setCurrentIndex(5)

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

        self.set_play_button_state(True)
        self.update_now_playing(path)

    def update_now_playing(self, path):
        meta = self.get_metadata(path)
        self.track_label.setText(meta['title'])
        self.artist_label.setText(f"{meta['artist']} • {meta['album']}")

        art = meta.get('art')
        size = self.album_art.width()

        if art:
            pix = QPixmap()
            pix.loadFromData(art)
            self.album_art.setPixmap(
                pix.scaled(size, size, Qt.KeepAspectRatio,
                           Qt.SmoothTransformation)
            )
        else:
            self.set_placeholder_art(size)

        self.update_now_playing_sidebars(meta)

    def set_placeholder_art(self, size):
        self.album_art.setPixmap(self.render_placeholder_pixmap(size))

    def update_now_playing_sidebars(self, meta):
        track = meta.get('title', 'Unknown')
        artist = meta.get('artist', 'Unknown Artist')
        album = meta.get('album', 'Unknown Album')
        art = meta.get('art')

        for sidebar in self.now_playing_sidebars:
            sidebar['track'].setText(track)
            sidebar['artist'].setText(f"{artist} • {album}")
            size = sidebar['art'].width() or 56
            self.set_preview_art(sidebar['art'], art, size)

    def set_play_button_state(self, is_playing):
        text = "⏸" if is_playing else "▶"
        self.play_btn.setText(text)
        for btn in self.sidebar_play_buttons:
            btn.setText(text)

    def toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
            self.set_play_button_state(False)
        else:
            self.player.play()
            self.set_play_button_state(True)

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