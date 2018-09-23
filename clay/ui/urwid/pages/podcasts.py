"""
Components for "podcasts" page
"""
import urwid

from .page import AbstractPage, AbstractListItem, AbstractListBox
from clay.core.gp.podcast import PodcastEpisode
from clay.core import gp
from clay.ui.urwid import SongListBox, hotkey_manager
from clay.core.log import logger


class PodcastListBox(AbstractListBox):
    def auth_state_changed(self, is_auth):
        """
        Called when auth state changes (e. g. user is logged in).
        Requests fetching of podcasts.
        """
        if is_auth:
            self.walker[:] = [
                urwid.Text(u'\n \uf01e Loading podcasts...', align='center')
            ]

            gp.get_all_user_podcasts_async(callback=self.populate)


class PodcastEpisodeListBox(AbstractListBox):
    def populate(self, podcasts):
        super().populate(sorted(podcasts, key=lambda podcast: podcast.publication_timestamp, reverse=True))


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

    def podcast_activated(self, podcast):
        self.episodelist.populate(gp.get_cached_podcast_episodes(podcast))

    def activate(self):
        pass
        # self.artistlist.populate(gp.cached_artists)

    def episode_activate(self, album):
        pass
        # self.songlist.populate(album.tracks)
        # self.app.redraw()
