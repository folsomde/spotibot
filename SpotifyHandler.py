import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
log = logging.getLogger('SPOTIFY')

class SpotifyHandler:
	scopes: str = 'playlist-modify-public'
	def __init__(self, credentials: dict[str, str]) -> None:
		log.debug(f'Creating real API object')
		self.spotify = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=self.scopes, 
			client_id=credentials['spotify_client_id'], client_secret=credentials['spotify_secret'], redirect_uri=credentials['spotify_redirect_uri']))
		self.playlist = None

	def get_track_info(self, urls):
		return self.spotify.tracks(urls)

	def set_playlist(self, playlist) -> None:
		log.info(f'Setting playlist ID to {playlist}')
		self.playlist = playlist

	def get_playlist(self) -> str:
		return 'https://open.spotify.com/playlist/' + str(self.playlist)

	def add(self, tracks: str, position: int = None, playlist: str = None) -> None:
		if playlist is None:
			playlist = self.playlist
		log.info(f'Adding {tracks} to playlist {playlist} at position {position}')
		self.spotify.playlist_add_items(self.playlist, [tracks], position)

	def remove(self, tracks: str, playlist: str = None) -> None:
		if playlist is None:
			playlist = self.playlist
		log.info(f'Setting removing {tracks} from playlist {playlist}')
		self.spotify.playlist_remove_all_occurrences_of_items(playlist, tracks)

	def new_playlist(self, playlist_name: str = None, playlist_desc: str = None) -> str:
		if playlist_name is None:
			playlist_name = 'New spotipy playlist'
		if playlist_desc is None:
			playlist_desc = 'New spotipy playlist'

		log.info(f'Creating new playlist named {playlist_name} with description {playlist_desc}')
		out = self.spotify.user_playlist_create(self.spotify.me()['id'], playlist_name, description=playlist_desc)
		log.debug(f'{out = }')
		return out['id']

class Dummy:
	def __init__(self):
		log.debug(f'Creating dummy object')
		pass

	def set_playlist(self, playlist) -> None:
		log.info(f'Setting playlist ID to {playlist}')
		pass

	def get_playlist(self) -> str:
		return 'http://localhost:5000'

	def add(self, tracks: str, position: int = None, playlist: str = None) -> None:
		log.info(f'Adding {tracks} to playlist {playlist} at position {position}')
		pass

	def remove_by_name(self, tracks: str, playlist: str = None) -> None:
		log.info(f'Setting removing {tracks} from playlist {playlist}')
		pass

	def new_playlist(self, playlist_name: str = None, playlist_desc: str = None) -> str:
		log.info(f'Creating new playlist named {playlist_name} with description {playlist_desc}')
		return ''

	def get_track_info(self, urls):
		thislen = len(urls)
		return thislen * ['Artist',], thislen * ['Track',]


class HandlerFactory:
    def get_handler(self, use_spotify: bool, credentials: dict[str, str] = None) -> [SpotifyHandler, Dummy]:
        if use_spotify:
            return SpotifyHandler(credentials)
        else:
            return Dummy()