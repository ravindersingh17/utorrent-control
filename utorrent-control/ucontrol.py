import requests
import json
from urllib.parse import urlencode, parse_qs
from bs4 import BeautifulSoup as BS
import time
import sys, os
if sys.platform == "cygwin":
    from cygwin import cygpath

class ucontrolException(Exception):
    """
    Handle all errors from utorrent API

    """
    pass



class ucontrol:

    P_dont = 0
    P_low = 1
    P_normal = 2
    P_high = 3

    def __init__(self, base_url, user, password, work_dir, auto_connect=True):
        """
        Initialize session object and authenticate with utorrent

        :param base_url The http URL of utorrent. Eg http://localhost:9090/gui/
        :param user utorrent webUI auth user
        :param password
        :param work_dir directory to store torrents and temporary files
        :param auto_connect Connect to utorrent API and get the auth token(optional), default True
        """
        self.base_url = base_url if base_url[-1] == "/" else base_url + "/"
        self.session = requests.Session()
        self.session.auth = requests.auth.HTTPBasicAuth(user, password)
        self.work_dir = work_dir

        if auto_connect: self.connect()

    def connect(self):
        """
        Connect to utorrent webUI
        """
        try:
            response = self.session.get(self.base_url + "token.html")
            assert response.status_code == 200
        except AssertionError:
            raise ucontrolException("Unable to Authenticate with utorrent")
        except:
            raise ucontrolException("Unable to connect to utorrent")


        try:
            self.token = BS(response.text, "html.parser").find("div", {"id": "token"}).text
            assert len(self.token) == 64
        except:
            raise ucontrolException("Unable to parse auth token")



    def _apirequest(self, params, file_field = None, open_file = None):
        """
        Get results of API request

        :param params List of http GET parameters
        :return Dictionary of parsed json
        """
        try:
            url = "%s?token=%s&%s" % (self.base_url, self.token, urlencode(params))
            if not file_field:
                response = self.session.get(url)
            else:
                response = self.session.post(url, files={"torrent_file": (None, open_file, "application/x-bittorrent")})

            assert response.status_code == 200
        except AssertionError:
            raise ucontrolException("Authentication failure. URL: %s" % (url))
        except:
            raise ucontrolException("Unable to connect to uTorrent")
        try:
            parsed = json.loads(response.text)
        except:
            raise ucontrolException("Invalid json received")

        return parsed

    def get_list(self):
        """
        Get data of all torrents
        """
        params = [("list", 1)]
        return { k["hash"] : k for k in map(self.map_torrent_info, self._apirequest(params)["torrents"])}

    def map_torrent_info(self, torrent):
        """
        Get information about a torrent

        :param torrent
        :return dict
        """
        torrentinfo_map = { "hash": 0, "status": 1, "name": 2, "size": 3, "progress": 4, "downloaded": 5,
            "uploaded": 6, "downspeed":9, "eta":10, "savepath": 26}
        return {key:torrent[torrentinfo_map[key]] for key in torrentinfo_map.keys()}

    def get_settings(self):
        """
        Get list of all settings

        :return dict

        """
        params = [("action", "getsettings")]
        return {x[0]: x[2] for x in self._apirequest(params)["settings"]}

    def set_setting(self, key, value):
        params = [("action", "setsetting"), ("s", key), ("v", value)]
        return self._apirequest(params)

    def map_status(self, int_status):
        """
        Convert integer status to dictionary

        :param int_status
        :return dict
        """
        status_map = ("started", "checking", "start_after_check", "checked", "error", "paused", "queued", "loaded")
        return  dict(zip(status_map,[bool(2**i & int_status) for i in range(8)]))

    def get_files(self, torrent_hash):
        params = [("action", "getfiles"), ("hash", torrent_hash)]
        files_info = self._apirequest(params)
        return files_info["files"][1]

    def add_torrent(self, magnet):
        """
        Initialize settings, set magnet->torrent dir to work_dir
        """
        self.set_setting("torrents_start_stopped", "false")
        torrent_dir = self.work_dir if sys.platform != "cygwin" else cygpath(self.work_dir, "w")

        """
        Add torrent from url. To get the torrent info the torrent has to be started then immediately stopped and files deleted.
        """
        params = [("action", "add-url"), ("s", magnet)]
        add_action = self._apirequest(params)
        torrent_info = self.parse_magnet(magnet)
        torrent_hash = torrent_info["hash"]

        torrent_files = self.get_files(torrent_hash)
        self.start_torrent(torrent_hash)
        while not torrent_files or not torrent_files[1]:
            torrent_files = self.get_files(torrent_hash)
            time.sleep(.5)
        self.remove_torrent(torrent_hash, True)

        tor_file = open(os.path.join(self.work_dir, torrent_info["dn"] + ".torrent"), "rb")
        self.set_setting("torrents_start_stopped", "true")
        params = [("action", "add-file")]
        self._apirequest(params, "torrent_file", tor_file)

        self.prioritize_download(torrent_hash)

        return torrent_hash

    def prioritize_download(self, torrent_hash):
        files = self.get_files(torrent_hash)
        all_indexes = list(range(len(files)))
        self.set_priority(torrent_hash, ucontrol.P_dont, all_indexes)
        self.start_torrent(torrent_hash)

    def set_priority(self, torrent_hash, priority, indexes):
        params = [("action", "setprio"), ("hash", torrent_hash), ("p", priority)]
        for i in indexes: params.append(("f", i))
        self._apirequest(params)

    def recheck_torrent(self, torrent_hash):
        params = [("action", "recheck"), ("hash", torrent_hash)]
        self._apirequest(params)

    def parse_magnet(self, magnet):
        magnet_info = {}
        try:
            for k,v in iter(parse_qs(magnet).items()):
                if k.startswith("magnet:"):  magnet_info["hash"] = v[0].split(":")[-1].upper()
                if k == "dn": magnet_info["dn"] = v[0]
        except:
            raise ucontrolException("Malformed magnet URI")
        return magnet_info

    def pause_torrent(self, torrent_hash):
        params = [("action", "pause"),("hash", torrent_hash)]
        return self._apirequest(params)

    def start_torrent(self, torrent_hash):
        params = [("action", "start"),("hash", torrent_hash)]
        return self._apirequest(params)

    def remove_torrent(self, torrent_hash, with_data = False):
        action = "removedata" if with_data else "remove"
        params = [("action", action), ("hash", torrent_hash)]
        return self._apirequest(params)
