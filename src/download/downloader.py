import os
import re
from PyQt6.QtCore import QObject, pyqtSignal

import yt_dlp

from src.download.trans_srt import fetch_and_translate_srt

class DownloadSignals(QObject):
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

def run_youtube_download(url: str, save_dir: str, signals: DownloadSignals):
    try:
        signals.status.emit("비디오 분석 및 다운로드 중...")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(save_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)

        v_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
        if v_match:
            signals.status.emit("공식 자막 추출 및 파파고 번역 적용 중...")
            srt_path = os.path.splitext(video_file)[0] + ".srt"
            fetch_and_translate_srt(v_match.group(1), srt_path)

        signals.finished.emit(video_file)
    except Exception as e:
        signals.error.emit(f"다운로드 실패: {e}")