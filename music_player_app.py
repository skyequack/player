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

        # DPI scaling
        self.scale = self.ui_scale()

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
        self.current_art_size = 150  # FIX: Reduced from 300 to 150 for small screen
        self.track_ending = False  # FIX: Prevent duplicate auto-advance

        self.showFullScreen()
        self.set_minimal_theme()
        self.init_ui()
        self.scan_music_library()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.timer.start(500)

    # ---------- Scaling ----------
    def ui_scale(self):
        # FIX: For 480x320 screens, use fixed small scale
        screen = QGuiApplication.primaryScreen()
        geometry = screen.geometry()
        
        # If screen width is 480 or less, use minimal scaling
        if geometry.width() <= 480:
            return 0.5  # Force small scale for tiny displays
        
        dpi = screen.logicalDotsPerInch()
        return dpi / 96.0

    def scaled(self, px):
        return int(px * self.scale)

    def touch_height(self):
        return self.scaled(40)  # FIX: Reduced from 56 to 40

    # ---------- Theme ----------
    def set_minimal_theme(self):
        self.setStyleSheet(f"""
        QWidget {{
            background-color: #ffffff;
            color: #000000;
            font-family: "Segoe UI", Arial;
            font-size: {self.scaled(11)}px;
        }}

        QListWidget {{
            border: none;
            padding: {self.scaled(4)}px;
            outline: none;
        }}

        QListWidget::item {{
            padding: {self.scaled(8)}px;
            border-bottom: 1px solid #e5e5e5;
        }}

        QListWidget::item:selected {{
            background-color: #e6f0ff;
        }}

        QPushButton {{
            background-color: #f5f5f5;
            border: 1px solid #d0d0d0;
            border-radius: {self.scaled(4)}px;
            padding: {self.scaled(6)}px;
            min-height: {self.touch_height()}px;
        }}

        QPushButton:hover {{
            background-color: #ebebeb;
        }}

        QPushButton:pressed {{
            background-color: #dcdcdc;
        }}

        QPushButton#accent {{
            background-color: #1976d2;
            color: white;
            border: none;
        }}

        QPushButton#accent:pressed {{
            background-color: #1259a3;
        }}

        QSlider::groove:horizontal {{
            height: {self.scaled(4)}px;
            background: #e0e0e0;
            border-radius: {self.scaled(2)}px;
        }}

        QSlider::sub-page:horizontal {{
            background: #1976d2;
            border-radius: {self.scaled(2)}px;
        }}

        QSlider::handle:horizontal {{
            background: #1976d2;
            width: {self.scaled(16)}px;
            height: {self.scaled(16)}px;
            margin: {self.scaled(-6)}px 0;
            border-radius: {self.scaled(8)}px;
        }}
        """)

    # ---------- UI ----------
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(self.scaled(4), self.scaled(4),
                                       self.scaled(4), self.scaled(4))
        main_layout.setSpacing(self.scaled(4))

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
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, self.scaled(4))

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(back_action)
        layout.addWidget(back_btn)

        label = QLabel(title)
        label.setAlignment(Qt.AlignCenter)
        label.setStyleSheet(f"font-size: {self.scaled(12)}px; font-weight: 600;")
        layout.addWidget(label, 1)

        layout.addWidget(QLabel(), 0)
        return header

    def create_landing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(self.scaled(4))

        title = QLabel("Music Player")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: {self.scaled(14)}px; font-weight: 700;")
        layout.addWidget(title)

        btn_albums = QPushButton("Albums")
        btn_artists = QPushButton("Artists")
        btn_favorites = QPushButton("Favorites")

        for b in [btn_albums, btn_artists, btn_favorites]:
            b.setObjectName("accent")

        btn_albums.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_artists.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_favorites.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        layout.addWidget(btn_albums, 1)
        layout.addWidget(btn_artists, 1)
        layout.addWidget(btn_favorites, 1)

        btn_exit = QPushButton("Exit")
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)

        return page

    def create_albums_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(self.create_header("Albums",
                                            lambda: self.stack.setCurrentIndex(0)))

        self.album_list = QListWidget()
        self.album_list.itemClicked.connect(self.show_album_detail)
        layout.addWidget(self.album_list)

        return page

    def create_artists_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(self.create_header("Artists",
                                            lambda: self.stack.setCurrentIndex(0)))

        self.artist_list = QListWidget()
        self.artist_list.itemClicked.connect(self.show_artist_albums)
        layout.addWidget(self.artist_list)

        return page

    def create_favorites_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        layout.addWidget(self.create_header("Favorites",
                                            lambda: self.stack.setCurrentIndex(0)))

        self.favorites_list = QListWidget()
        self.favorites_list.itemClicked.connect(self.show_album_detail)
        layout.addWidget(self.favorites_list)

        return page

    def create_album_detail_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        header = QWidget()
        h = QHBoxLayout(header)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(self.go_back_from_detail)
        h.addWidget(back_btn)

        self.detail_album_label = QLabel("")
        self.detail_album_label.setAlignment(Qt.AlignCenter)
        self.detail_album_label.setStyleSheet(
            f"font-size: {self.scaled(11)}px; font-weight: 600;"
        )
        h.addWidget(self.detail_album_label, 1)

        self.favorite_btn = QPushButton("♡")
        self.favorite_btn.clicked.connect(self.toggle_favorite)
        h.addWidget(self.favorite_btn)

        layout.addWidget(header)

        self.track_list = QListWidget()
        self.track_list.itemClicked.connect(self.play_selected_track)
        layout.addWidget(self.track_list)

        return page

    def create_now_playing_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)

        back_btn = QPushButton("Back")
        back_btn.clicked.connect(lambda: self.stack.setCurrentIndex(4))
        layout.addWidget(back_btn)

        self.album_art = QLabel()
        self.album_art.setAlignment(Qt.AlignCenter)
        self.album_art.setSizePolicy(QSizePolicy.Expanding,
                                     QSizePolicy.Expanding)
        layout.addWidget(self.album_art, stretch=4)

        self.track_label = QLabel("No track")
        self.track_label.setAlignment(Qt.AlignCenter)
        self.track_label.setStyleSheet(
            f"font-size: {self.scaled(11)}px; font-weight: 600;"
        )
        layout.addWidget(self.track_label)

        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.artist_label)

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)

        self.progress = QSlider(Qt.Horizontal)
        self.progress.sliderMoved.connect(self.seek)
        layout.addWidget(self.progress)

        controls = QHBoxLayout()

        self.prev_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")

        size = self.scaled(50)  # FIX: Reduced from 72 to 50
        for b in [self.prev_btn, self.play_btn, self.next_btn]:
            b.setFixedSize(size, size)
            b.setStyleSheet(f"border-radius: {size//2}px;")

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

    # ---------- Resize ----------
    def resizeEvent(self, event):
        super().resizeEvent(event)
        # FIX: Check if album_art exists before accessing it
        if hasattr(self, 'album_art'):
            self.current_art_size = min(
                self.album_art.width(), self.album_art.height()
            )

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
                if 'APIC:' in audio:
                    meta['art'] = audio['APIC:'].data

        except Exception:
            pass

        return meta

    def get_track_number(self, path):
        return self.get_metadata(path).get('track', 999)

    # ---------- Lists ----------
    def populate_lists(self):
        self.album_list.clear()
        for album in sorted(self.albums):
            artist = self.album_metadata[album]['artist']
            item = QListWidgetItem(f"{album}\n{artist}")
            item.setData(Qt.UserRole, album)
            self.album_list.addItem(item)

        self.artist_list.clear()
        for artist in sorted(self.artists):
            item = QListWidgetItem(artist)
            item.setData(Qt.UserRole, artist)
            self.artist_list.addItem(item)

        self.update_favorites_list()

    def update_favorites_list(self):
        self.favorites_list.clear()
        for album in self.favorites:
            if album in self.albums:
                artist = self.album_metadata[album]['artist']
                item = QListWidgetItem(f"{album}\n{artist}")
                item.setData(Qt.UserRole, album)
                self.favorites_list.addItem(item)

    # ---------- Navigation ----------
    def show_album_detail(self, item):
        album = item.data(Qt.UserRole)
        self.current_album = album
        self.current_tracks = self.albums[album]

        artist = self.album_metadata[album]['artist']
        self.detail_album_label.setText(f"{album}\n{artist}")

        # FIX: Update favorite button to show current state
        self.update_favorite_button()

        self.track_list.clear()
        for i, path in enumerate(self.current_tracks):
            meta = self.get_metadata(path)
            it = QListWidgetItem(f"{i+1}. {meta['title']}")
            it.setData(Qt.UserRole, i)
            self.track_list.addItem(it)

        self.stack.setCurrentIndex(4)

    def show_artist_albums(self, item):
        artist = item.data(Qt.UserRole)
        self.album_list.clear()

        for album in self.artists[artist]:
            art = self.album_metadata[album]['artist']
            it = QListWidgetItem(f"{album}\n{art}")
            it.setData(Qt.UserRole, album)
            self.album_list.addItem(it)

        self.stack.setCurrentIndex(1)

    def go_back_from_detail(self):
        self.populate_lists()
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

        self.play_btn.setText("⏸")
        self.update_now_playing(path)

    def update_now_playing(self, path):
        meta = self.get_metadata(path)
        self.track_label.setText(meta['title'])
        self.artist_label.setText(f"{meta['artist']} • {meta['album']}")

        art = meta.get('art')
        size = self.current_art_size

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
            self.play_btn.setText("▶")
        else:
            self.player.play()
            self.play_btn.setText("⏸")

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
        self.update_favorites_list()
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
    sys.exit(app.exec_())