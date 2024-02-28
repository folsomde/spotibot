from types import TracebackType
from typing import Any, IO, Optional, Type
import logging, time, os, json

class JSONFileLoader:
    def __init__(self, file_path: str, mode: Optional[str] = 'r+') -> None:
        self.file_path = file_path
        self.file: IO = open(file_path, mode, encoding='utf-8')
        self.data: Any = json.load(self.file, object_hook = self.object_hook)

    def __enter__(self) -> Any:
        if self.file.writable():
            return self.data, self.file
        else:
            return self.data

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        if self.file:
            self.file.close()

    @staticmethod
    def object_hook(d):
        return {int(k) if k.lstrip('-').isdigit() else k: v for k, v in d.items()}

class JSONparser:
    def __init__(self, file_name: Optional[str] = None, playlist_id: Optional[str] = None) -> None:
        if file_name is None:
            self.file: str = JSONparser.file_by_date()
        else:
            self.file: str = file_name

        self.is_new = not os.path.exists(self.file)
        if self.is_new:
            logging.getLogger('JSON.init').info(f'Creating new file: {self.file}')
            with open(self.file, 'a+', encoding='utf-8') as json_file:
                self.creation_time: int = int(time.time())
                self.playlist: str = 'N/A' if playlist_id is None else playlist_id
                json.dump({'playlist': self.playlist, 'creation_time': self.creation_time}, json_file, ensure_ascii=True, indent=4)
                self.tracks: set(str) = set()
        else:
            logging.getLogger('JSON.init').info(f'Reading existing file: {self.file}')
            with JSONFileLoader(self.file, mode = 'r') as cur_dict:
                self.playlist: str = cur_dict['playlist']
                self.creation_time: int = cur_dict['creation_time']
                self.tracks: set(str) = set(t for users in cur_dict.keys() if type(users) == int for t in cur_dict[users]['tracks'])
        logging.getLogger('JSON.init').debug(f'{self.playlist = }, {self.creation_time = }, {len(self.tracks) = }')

    def get_playlist(self) -> str:
        return self.playlist

    def append_track(self, disc_id: int, track_id: str) -> bool:
        if track_id in self.tracks:
            logging.getLogger('JSON.append').info(f'Skipped {disc_id}: {track_id} as track already exists')
            return False
        disc_id = int(disc_id)
        with JSONFileLoader(self.file) as data:
            cur_dict, json_file = data
            if disc_id in cur_dict:
                cur_dict[disc_id]['tracks'].append(track_id)
                cur_dict[disc_id]['times'].append(int(time.time()))
            else:
                cur_dict[disc_id] = {'tracks': [track_id,], 'times': [int(time.time()),]}

            # move the cursor to the top, dump, trim file to size
            json_file.seek(0)
            json.dump(cur_dict, json_file, ensure_ascii=True, indent=4)
            json_file.truncate()
        logging.getLogger('JSON.append').info(f'Logged {disc_id}: {track_id} to {self.file}')
        self.tracks.add(track_id)
        return True

    def get_all_track_counts(self) -> dict[int, int]:
        with JSONFileLoader(self.file, mode = 'r') as cur_dict:
            return {users: len(cur_dict[users]['tracks']) for users in cur_dict.keys() if type(users) == int}

    def get_all_tracks(self) -> dict[int, list[str]]:
        with JSONFileLoader(self.file, mode = 'r') as cur_dict:
            return {users: cur_dict[users]['tracks'] for users in cur_dict.keys() if type(users) == int}
            
    def get_all_last_track_times(self) -> dict[int, int]:
        with JSONFileLoader(self.file, mode = 'r') as cur_dict:
            return {users: cur_dict[users]['times'][-1] for users in cur_dict.keys() if type(users) == int}

    def get_all_last_track_ids(self) -> dict[int, str]:
        with JSONFileLoader(self.file, mode = 'r') as cur_dict:
            return {users: cur_dict[users]['tracks'][-1] for users in cur_dict.keys() if type(users) == int}

    def get_track_count(self, disc_id: int) -> int:
        disc_id = int(disc_id)
        with JSONFileLoader(self.file, mode = 'r') as cur_dict:
            return len(cur_dict[disc_id]['tracks']) if disc_id in cur_dict else 0

    def get_last_track_time(self, disc_id: int) -> int:
        return self.get_last_attr(disc_id, 'times')
    
    def get_last_track_id(self, disc_id: int) -> str:
        return self.get_last_attr(disc_id, 'tracks')

    def get_last_attr(self, disc_id: int, attr: str) -> Any:
        disc_id = int(disc_id)
        with JSONFileLoader(self.file, mode = 'r') as cur_dict:
            return cur_dict[disc_id][attr][-1] if disc_id in cur_dict else None

    @staticmethod
    def file_by_date() -> str:
        curtime = time.gmtime()
        return f"playlist_data/{curtime.tm_year}-{curtime.tm_mon:02}.json"

    @staticmethod
    def uniquify(path: str) -> str:
        filename, extension = os.path.splitext(path)
        counter = 1

        while os.path.exists(path):
            path = filename + '-' + str(counter) + extension
            counter += 1

        return path

    @staticmethod
    def unique_name() -> str:
        return JSONparser.uniquify(JSONparser.file_by_date())