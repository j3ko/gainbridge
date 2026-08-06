from mutagen.flac import FLAC
# also handle mutagen.id3, mutagen.mp4, etc. later

class TaggerService:
    def write_replaygain(self, path: str, track_gain: float, track_peak: float,
                         album_gain: float | None = None, album_peak: float | None = None):
        audio = FLAC(path)
        audio["REPLAYGAIN_TRACK_GAIN"] = [f"{track_gain:.2f} dB"]
        audio["REPLAYGAIN_TRACK_PEAK"] = [f"{track_peak:.6f}"]
        if album_gain is not None:
            audio["REPLAYGAIN_ALBUM_GAIN"] = [f"{album_gain:.2f} dB"]
        if album_peak is not None:
            audio["REPLAYGAIN_ALBUM_PEAK"] = [f"{album_peak:.6f}"]
        audio.save()