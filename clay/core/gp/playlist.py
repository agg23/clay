# This file is part of Clay.
# Copyright (C) 2018, Andrew Dunbai & Clay Contributors
#
# Clay is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Clay is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Clay. If not, see <https://www.gnu.org/licenses/>.
"""
This file contains the classes and methods for dealing with Google Play Playlists
"""
from .utils import Source
from .track import Track

class Playlist(object):
    """
    Model that represents remotely stored (Google Play Music) playlist.
    """
    def __init__(self, playlist_id, name, tracks):
        self._id = playlist_id
        self.name = name
        self.tracks = tracks

    def __str__(self):
        return "{} ({})".format(self.name, len(self.tracks))

    @property
    def id(self):  # pylint: disable=invalid-name
        """
        Playlist ID.
        """
        return self._id

    @classmethod
    def from_data(cls, data, many=False):
        """
        Construct and return one or many :class:`.Playlist` instances
        from Google Play Music API response.
        """
        if many:
            return [cls.from_data(one) for one in data]

        return Playlist(
            playlist_id=data['id'],
            name=data['name'],
            tracks=Track.from_data(data['tracks'], Source.playlist, many=True)
        )


class LikedSongs(object):
    """
    A local model that represents the songs that a user liked and displays them as a faux playlist.

    This mirrors the "liked songs" generated playlist feature of the Google Play Music apps.
    """
    def __init__(self):
        self._id = None  # pylint: disable=invalid-name
        self.name = "Liked Songs"
        self._tracks = []
        self._sorted = False

    def __str__(self):
        return "{} ({})".format(self.name, len(self._tracks))

    @property
    def tracks(self):
        """
        Get a sorted list of liked tracks.
        """
        if self._sorted:
            tracks = self._tracks
        else:
            self._tracks.sort(key=lambda k: k.original_data.get('lastRatingChangeTimestamp', '0'),
                              reverse=True)
            self._sorted = True
            tracks = self._tracks

        return tracks

    def add_liked_song(self, song):
        """
        Add a liked song to the list.
        """
        self._tracks.insert(0, song)

    def remove_liked_song(self, song):
        """
        Remove a liked song from the list
        """
        self._tracks.remove(song)
