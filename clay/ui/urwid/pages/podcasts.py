"""
Components for "podcasts" page
"""
import urwid

from .page import AbstractPage, AbstractListItem, AbstractListBox
from clay.core import gp
from clay.ui.urwid import SongListBox, hotkey_manager

class PodcastListBox(AbstractListBox):
    def populate(self, artists):
        items = []
        for artist in sorted(artists, key=artists.__getitem__):
            artist = AbstractListItem(artists[artist], self._icon)
            urwid.connect_signal(artist, 'activate', self.item_activated)
            items.append(artist)
        self.walker[:] = items
        self.app.redraw()

class PodcastEpisodeListBox(AbstractListBox):
    def populate(self, albums):
        items = []
        for album in albums:
            album = AbstractListItem(album, album.icon)
            urwid.connect_signal(album, 'activate', self.item_activated)
            items.append(album)
        self.walker[:] = items
        self.app.redraw()

class PodcastsPage(urwid.Columns, AbstractPage):
    """
    Podcasts page.
    Contains two parts:
    - List of podcasts
    - List of episodes by selected podcast
    """
    @property
    def name(self):
        return 'Podcasts'

    @property
    def key(self):
        return 7

    @property
    def slug(self):
        """
        Return page ID (`str`)
        """
        return "podcasts"

    def __init__(self, app):
        self.app = app
        self.podcastlist = PodcastListBox(app, '\U0001F399')
        self.episodelist = PodcastEpisodeListBox(app)
        self.songlist = SongListBox(app)
        self.songlist.set_placeholder('\n Select a podcast')

        urwid.connect_signal(self.podcastlist, 'activate', self.podcast_activated)
        urwid.connect_signal(self.episodelist, 'activate', self.episode_activate)

        super(PodcastsPage, self).__init__([self.podcastlist, self.episodelist, self.songlist])

    def podcast_activated(self, artist):
        pass
        # self.albumlist.populate(artist.albums)

    def activate(self):
        pass
        # self.artistlist.populate(gp.cached_artists)

    def episode_activate(self, album):
        pass
        # self.songlist.populate(album.tracks)
        # self.app.redraw()
