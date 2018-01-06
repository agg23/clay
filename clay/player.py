"""
Media player built using libVLC.
"""
# pylint: disable=too-many-instance-attributes
from random import randint
import json

from clay import vlc
from clay.eventhook import EventHook
from clay.notifications import NotificationArea
from clay.hotkeys import HotkeyManager


class Queue(object):
    """
    Model that represents player queue (local playlist),
    i.e. list of tracks to be played.

    Queue is used by :class:`.Player` to choose tracks for playback.

    Queue handles shuffling & repeating.

    Can be populated with :class:`clay.gp.Track` instances.
    """
    def __init__(self):
        self.random = False
        self.repeat_one = False

        self.tracks = []
        self.current_track = None

    def load(self, tracks, current_track=None):
        """
        Load list of tracks into queue.

        *current_track* can be either ``None`` or ``int`` (zero-indexed).
        """
        self.tracks = tracks[:]
        if (current_track is None) and self.tracks:
            current_track = 0
        self.current_track = current_track

    def append(self, track):
        """
        Append track to playlist.
        """
        self.tracks.append(track)

    def remove(self, track):
        """
        Remove track from playlist if is present there.
        """
        if track not in self.tracks:
            return

        index = self.tracks.index(track)
        self.tracks.remove(track)
        if index < self.current_track:
            self.current_track -= 1

    def get_current_track(self):
        """
        Return current :class:`clay.gp.Track`
        """
        if self.current_track is None:
            return None
        return self.tracks[self.current_track]

    def next(self, force=False):
        """
        Advance to the next track and return it.

        If *force* is ``True`` then track will be changed even if
        track repetition is enabled. Otherwise current track may be yielded
        again.

        Manual track switching calls this method with ``force=True`` while
        :class:`.Player` end-of-track event will call it with ``force=False``.
        """
        if self.current_track is None:
            if not self.tracks:
                return None
            self.current_track = self.tracks[0]

        if self.repeat_one and not force:
            return self.get_current_track()

        if self.random:
            self.current_track = randint(0, len(self.tracks) - 1)
            return self.get_current_track()

        self.current_track += 1
        if (self.current_track + 1) >= len(self.tracks):
            self.current_track = 0

        return self.get_current_track()

    def get_tracks(self):
        """
        Return current queue, i.e. a list of :class:`Track` instances.
        """
        return self.tracks


class Player(object):
    """
    Interface to libVLC. Uses Queue as a playback plan.
    Emits various events if playback state, tracks or play flags change.

    Singleton.
    """
    instance = None

    media_position_changed = EventHook()
    media_state_changed = EventHook()
    track_changed = EventHook()
    playback_flags_changed = EventHook()
    queue_changed = EventHook()
    track_appended = EventHook()
    track_removed = EventHook()

    def __init__(self):
        assert self.__class__.instance is None, 'Can be created only once!'
        self.media_player = vlc.MediaPlayer()

        self.media_player.event_manager().event_attach(
            vlc.EventType.MediaPlayerPlaying,
            self._media_state_changed
        )
        self.media_player.event_manager().event_attach(
            vlc.EventType.MediaPlayerPaused,
            self._media_state_changed
        )
        self.media_player.event_manager().event_attach(
            vlc.EventType.MediaPlayerEndReached,
            self._media_end_reached
        )
        self.media_player.event_manager().event_attach(
            vlc.EventType.MediaPlayerPositionChanged,
            self._media_position_changed
        )

        hotkey_manager = HotkeyManager.get()
        hotkey_manager.play_pause += self.play_pause
        hotkey_manager.next += self.next
        hotkey_manager.prev += lambda: self.seek_absolute(0)

        self._create_station_notification = None
        self.queue = Queue()

    @classmethod
    def get(cls):
        """
        Create new :class:`.Player` instance or return existing one.
        """
        if cls.instance is None:
            cls.instance = Player()

        return cls.instance

    def broadcast_state(self):
        """
        Write current playback state into a ``/tmp/clay.json`` file.
        """
        track = self.queue.get_current_track()
        if track is None:
            data = dict(
                playing=False,
                artist=None,
                title=None,
                progress=None,
                length=None
            )
        else:
            data = dict(
                playing=self.is_playing,
                artist=track.artist,
                title=track.title,
                progress=self.get_play_progress_seconds(),
                length=self.get_length_seconds()
            )
        with open('/tmp/clay.json', 'w') as statefile:
            statefile.write(json.dumps(data, indent=4))

    def _media_state_changed(self, event):
        """
        Called when a libVLC playback state changes.
        Broadcasts playback state & fires :attr:`media_state_changed` event.
        """
        assert event
        self.broadcast_state()
        self.media_state_changed.fire(self.is_playing)

    def _media_end_reached(self, event):
        """
        Called when end of currently played track is reached.
        Advances to the next track.
        """
        assert event
        self.next()

    def _media_position_changed(self, event):
        """
        Called when playback position changes (this happens few times each second.)
        Fires :attr:`.media_position_changed` event.
        """
        assert event
        self.broadcast_state()
        self.media_position_changed.fire(
            self.get_play_progress()
        )

    def load_queue(self, data, current_index=None):
        """
        Load queue & start playback.
        Fires :attr:`.queue_changed` event.

        See :meth:`.Queue.load`.
        """
        self.queue.load(data, current_index)
        self.queue_changed.fire()
        self._play()

    def append_to_queue(self, track):
        """
        Append track to queue.
        Fires :attr:`.track_appended` event.

        See :meth:`.Queue.append`
        """
        self.queue.append(track)
        self.track_appended.fire(track)
        # self.queue_changed.fire()

    def remove_from_queue(self, track):
        """
        Remove track from queue.
        Fires :attr:`.track_removed` event.

        See :meth:`.Queue.remove`
        """
        self.queue.remove(track)
        self.queue_changed.fire()
        self.track_removed.fire(track)

    def create_station_from_track(self, track):
        """
        Request creation of new station from some track.
        Runs in background.
        """
        self._create_station_notification = NotificationArea.notify('Creating station...')
        track.create_station_async(callback=self._create_station_from_track_ready)

    def _create_station_from_track_ready(self, station, error):
        """
        Called when a station is created.
        If *error* is ``None``, load new station's tracks into queue.
        """
        if error:
            self._create_station_notification.update(
                'Failed to create station: {}'.format(str(error))
            )
            return

        if not station.get_tracks():
            self._create_station_notification.update(
                'Newly created station is empty :('
            )
            return

        self.load_queue(station.get_tracks())
        self._create_station_notification.update('Station ready!')

    def get_is_random(self):
        """
        Return ``True`` if track selection from queue is randomed, ``False`` otherwise.
        """
        return self.queue.random

    def get_is_repeat_one(self):
        """
        Return ``True`` if track repetition in queue is enabled, ``False`` otherwise.
        """
        return self.queue.repeat_one

    def set_random(self, value):
        """
        Enable/disable random track selection.
        """
        self.queue.random = value
        self.playback_flags_changed.fire()

    def set_repeat_one(self, value):
        """
        Enable/disable track repetition.
        """
        self.queue.repeat_one = value
        self.playback_flags_changed.fire()

    def get_queue_tracks(self):
        """
        Return :attr:`.Queue.get_tracks`
        """
        return self.queue.get_tracks()

    def _play(self):
        """
        Pick current track from a queue and requests media stream URL.
        Completes in background.
        """
        track = self.queue.get_current_track()
        if track is None:
            return
        track.get_url(callback=self._play_ready)
        self.broadcast_state()
        self.track_changed.fire(track)

    def _play_ready(self, url, error, track):
        """
        Called once track's media stream URL request completes.
        If *error* is ``None``, tell libVLC to play media by *url*.
        """
        if error:
            NotificationArea.notify('Failed to request media URL: {}'.format(str(error)))
            return
        assert track
        self.media_player.set_media(vlc.Media(url))
        self.media_player.play()

    @property
    def is_playing(self):
        """
        True if current libVLC state is :attr:`vlc.State.Playing`
        """
        return self.media_player.get_state() == vlc.State.Playing

    def play_pause(self):
        """
        Toggle playback, i.e. play if paused or pause if playing.
        """
        if self.is_playing:
            self.media_player.pause()
        else:
            self.media_player.play()

    def get_play_progress(self):
        """
        Return current playback position in range ``[0;1]`` (``float``).
        """
        return self.media_player.get_position()

    def get_play_progress_seconds(self):
        """
        Return current playback position in seconds (``int``).
        """
        return int(self.media_player.get_position() * self.media_player.get_length() / 1000)

    def get_length_seconds(self):
        """
        Return currently played track's length in seconds (``int``).
        """
        return int(self.media_player.get_length() // 1000)

    def next(self, force=False):
        """
        Advance to next track in queue.
        See :meth:`.Queue.next`.
        """
        self.queue.next(force)
        self._play()

    def get_current_track(self):
        """
        Return currently played track.
        See :meth:`.Queue.get_current_track`.
        """
        return self.queue.get_current_track()

    def seek(self, delta):
        """
        Seek to relative position.
        *delta* must be a ``float`` in range ``[-1;1]``.
        """
        self.media_player.set_position(self.get_play_progress() + delta)

    def seek_absolute(self, position):
        """
        Seek to absolute position.
        *position* must be a ``float`` in range ```[0;1]`.
        """
        self.media_player.set_position(position)