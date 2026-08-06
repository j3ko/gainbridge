from plexapi.server import PlexServer

class PlexService:
    def __init__(self, base_url: str, token: str):
        self.server = PlexServer(base_url, token)

    def get_music_libraries(self):
        return [s for s in self.server.library.sections() if s.type == "artist"]

    def get_track_loudness(self, track):
        # returns gain / peak / etc. from the media stream analysis
        pass