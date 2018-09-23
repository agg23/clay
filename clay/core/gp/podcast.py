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
from . import client


class Podcast(object):
    """
    Model that represents a podcast series from Google Play Music.
    """
    def __init__(self, podcast_id, title, description):
        self._id = podcast_id
        self.name = title
        self.description = description

    @property
    def id(self):  # pylint: disable=invalid-name
        """
        Podcast ID.
        """
        return self._id

    def __str__(self):
        return "{} ({})".format(self.name, self.description)


class PodcastEpisode(object):
    """
    Model that represents a single podcast episode from Google Play Music.
    """
    def __init__(self, data):
        self._id = data['episodeId']
        self.name = data['title']

        self.podcast = client.gp.add_podcast(data['seriesId'], data['seriesTitle'], data['description'])

        self.publication_timestamp = data['publicationTimestampMillis']
        self.duration = data['durationMillis']
        self.explicit_rating = (int(data['explicitType'] if 'explicitType' in data else 0))

    def __str__(self):
        return "{}".format(self.name)

    @property
    def id(self):  # pylint: disable=invalid-name
        """
        PodcastEpisode ID.
        """
        return self._id

    @classmethod
    def from_data(cls, data, many=False):
        """
        Construct and return one or many (in a dict) :class:`.PodcastEpisode` instances
        from Google Play Music API response.
        """
        if many:
            episodes = {}
            for one in data:
                episode = cls.from_data(one)
                if episode.podcast.id not in episodes:
                    episodes[episode.podcast.id] = [episode]
                else:
                    episodes[episode.podcast.id].append(episode)

            return episodes

        return PodcastEpisode(
            data=data
        )

    def get_url(self, callback):
        """
        Gets playable stream URL for this Podcast.

        "callback" is called with "(url, error)" args after URL is fetched.

        Keep in mind this URL is valid for a limited time.
        """
        def on_get_url(url, error):
            """
            Called when URL is fetched.
            """
            self.cached_url = url
            callback(url, error, self)

        podcast_id = str(self.id)
        client.gp.get_podcast_stream_url_async(podcast_id, callback=on_get_url)

