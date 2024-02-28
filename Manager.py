from SpotifyHandler import HandlerFactory
from JSONtools import JSONparser
import logging, os
log = logging.getLogger('manager')

class Manager:
    def __init__(self, config, tokens, json_name = None):
        log.warning(f"{config['use_spotify'] = }")
        self.sp = HandlerFactory().get_handler(config['use_spotify'], tokens)
        if json_name is None or not os.path.exists(json_name):
            self.swap_to_new_playlist()
        else:
            self.load_existing_playlist(json_name)

    def swap_to_new_playlist(self, file_name = None, name = None, desc = ''):
        log.info('Creating new Spotify playlist')
        date_text = os.path.splitext(os.path.basename(JSONparser.file_by_date()))[0]
        name = name or f'Sandyland songs: {date_text}'
        playlist_id = self.sp.new_playlist(name, desc)
        self.create_json_from_existing_playlist(playlist_id, file_name)

    def create_json_from_existing_playlist(self, playlist_id, file_name = None):
        log.info('Creating JSON from Spotify playlist')
        self.sp.set_playlist(playlist_id)
        self.parser = JSONparser(file_name = file_name or JSONparser.unique_name(), 
                                 playlist_id = playlist_id)

    def load_existing_playlist(self, file_name):
        log.info('Loading existing playlist')
        self.parser = JSONparser(file_name = file_name)
        self.sp.set_playlist(self.parser.get_playlist())

    def add_to_playlist(self, discord_id, url):
        split = url.split('/')
        try:
            plidx = split.index('track')
        except ValueError:
            return False
        track_id = split[plidx + 1]
        try:
            qidx = track_id.index('?')
            track_id = track_id[:qidx]
        except ValueError:
            pass
        # add to json file, check for duplicates
        success = self.parser.append_track(discord_id, track_id)
        # add to spotify
        if success:
            log.debug(url)
            # self.sp.add('https://open.spotify.com/track/' + track_id)
            self.sp.add(url)
        return success

    def remove_from_playlist(self, tracks):
        # remove from spotify
        self.sp.remove(tracks)
        # sync with json file
        raise NotImplementedError("I don't actually know why I started making a remove functionality. It's so much easier to just do it from the playlist itself.")

    def get_playlist_link(self):
        return self.sp.get_playlist()

