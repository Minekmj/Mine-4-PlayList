import os
import re
from PyQt6.QtCore import QObject, pyqtSignal
import yt_dlp
from src.trans_srt import fetch_and_translate_srt

class DownloadSignals(QObject):
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

def run_youtube_download(url: str, save_dir: str, signals: DownloadSignals):
    try:
        os.makedirs(save_dir, exist_ok=True)
        signals.status.emit("비디오 분석 및 다운로드 중...")

        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(save_dir, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'quiet': True,
            'noplaylist': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info)

        if not os.path.exists(video_file):
            base, _ = os.path.splitext(video_file)
            candidates = [base + '.mp4', base + '.webm', base + '.mkv']
            video_file = next((path for path in candidates if os.path.exists(path)), video_file)

        v_match = re.search(r'(?:v=|youtu\.be/|/shorts/|/embed/)([0-9A-Za-z_-]{11})', url)

        if v_match:
            try:
                signals.status.emit("공식 자막 추출 및 파파고 번역 적용 중...")
                srt_path = os.path.splitext(video_file)[0] + '.srt'
                fetch_and_translate_srt(v_match.group(1), srt_path)
            except Exception as e:
                signals.status.emit(f"자막 번역 실패: {e}")

        signals.finished.emit(video_file)

    except Exception as e:
        signals.error.emit(f"다운로드 실패: {e}")