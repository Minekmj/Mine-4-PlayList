#호환성용. 예전에 mpv 쓰던거 귀찮으니 Pass
from PyQt6.QtMultimedia import QMediaPlayer

class MPVProxy:
    def __init__(self, core):
        self._core = core

    @property
    def speed(self) -> float:
        return self._core.qplayer.playbackRate()

    @speed.setter
    def speed(self, val: float):
        self._core.qplayer.setPlaybackRate(val)

    @property
    def duration(self) -> float:
        d = self._core.qplayer.duration()
        return (d / 1000.0) if d > 0 else 0.0

    @property
    def time_pos(self) -> float:
        p = self._core.qplayer.position()
        return (p / 1000.0) if p > 0 else 0.0

    @time_pos.setter
    def time_pos(self, sec: float):
        self._core.seek(sec)

    @property
    def eof_reached(self) -> bool:
        return self._core.qplayer.mediaStatus() == QMediaPlayer.MediaStatus.EndOfMedia

    @property
    def filename(self) -> str:
        return self._core.current_file or ""

    @property
    def pause(self) -> bool:
        return self._core.qplayer.playbackState() == QMediaPlayer.PlaybackState.PausedState

    @pause.setter
    def pause(self, val: bool):
        if val:
            self._core.qplayer.pause()
        else:
            self._core.qplayer.play()

    @property
    def volume(self) -> int:
        return self._core.user_volume

    @volume.setter
    def volume(self, val: int):
        self._core.set_volume(val)

    def sub_add(self, filepath: str):
        self._core.sub_manager.load_file(filepath)
        self._core.update_subtitle_display(self.time_pos)

    def command(self, cmd: str, *args):
        if cmd == 'stop':
            self._core.qplayer.stop()
        elif cmd == 'play':
            self._core.qplayer.play()
        elif cmd == 'pause':
            self._core.qplayer.pause()

    def __setitem__(self, key, value):
        pass

    def __getitem__(self, key):
        return None