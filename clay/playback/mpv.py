"""
An implementation of the Clay player using VLC

Copyright (c) 2018, Clay Contributors
"""
from ctypes import CFUNCTYPE, c_void_p, c_int, c_char_p
from clay.core import osd_manager, logger, meta, settings_manager

import mpv
from .abstract import AbstractPlayer


class MPVPlayer(AbstractPlayer):
    """
    Interface to MPV. Uses Queue as a playback plan.
    Emits various events if playback state, tracks or play flags change.

    Singleton.
    """

    def __init__(self):
        # self.instance = mpv.MPV()

        # self.instance.set_user_agent(
        #     meta.APP_NAME,
        #     meta.USER_AGENT
        # )

        self.media_player = mpv.MPV()

        self.media_player.observe_property('pause', self._media_state_changed)
        self.media_player.observe_property('stream-open-filename', self._media_state_changed)
        # self.media_player.observe_property('end', self._media_end_reached)
        # self.media_player.observe_property('time-pos', self._media_position_changed)
        self.media_player.observe_property('stream-pos', self._media_position_changed)
        self.media_player.observe_property('idle-active', self._media_end_reached)

        # self.media_player.event_manager().event_attach(
        #     vlc.EventType.MediaPlayerPositionChanged,
        #     self._media_position_changed
        # )

        # self.equalizer = vlc.libvlc_audio_equalizer_new()
        # self.media_player.set_equalizer(self.equalizer)
        # self._create_station_notification = None
        AbstractPlayer.__init__(self)


    def _media_state_changed(self, *_):
        """
        Called when a libVLC playback state changes.
        Broadcasts playback state & fires :attr:`media_state_changed` event.
        """
        self.broadcast_state()
        self.media_state_changed.fire(self.is_loading, self.is_playing)

    def _media_end_reached(self, event, value):
        """
        Called when end of currently played track is reached.
        Advances to the next track.
        """
        if value:
            self.next()

    def _media_position_changed(self, *_):
        """
        Called when playback position changes (this happens few times each second.)
        Fires :attr:`.media_position_changed` event.
        """
        self.broadcast_state()
        self.media_position_changed.fire(
            self.get_play_progress()
        )

#    def create_station_from_track(self, track):
#        """
#        Request creation of new station from some track.
#        Runs in background.
#        """
#        #self._create_station_notification = notification_area.notify('Creating station...')
#        track.create_station_async(callback=self._create_station_from_track_ready)

    def _create_station_ready(self, station, error):
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

    def play(self):
        """
        Pick current track from a queue and requests media stream URL.
        Completes in background.
        """
        track = self.queue.get_current_track()
        if track is None:
            return
        self._is_loading = True
        self.broadcast_state()
        self.track_changed.fire(track)

        if settings_manager.get('download_tracks', 'play_settings') or \
           settings_manager.get_is_file_cached(track.filename):
            path = settings_manager.get_cached_file_path(track.filename)

            if path is None:
                logger.debug('Track %s not in cache, downloading...', track.store_id)
                track.get_url(callback=self._download_track)
            else:
                logger.debug('Track %s in cache, playing', track.store_id)
                self._play_ready(path, None, track)
        else:
            logger.debug('Starting to stream %s', track.store_id)
            track.get_url(callback=self._play_ready)

    def _play_ready(self, url, error, track):
        """
        Called once track's media stream URL request completes.
        If *error* is ``None``, tell libVLC to play media by *url*.
        """
        self._is_loading = False
        if error:
            #notification_area.notify('Failed to request media URL: {}'.format(str(error)))
            logger.error(
                'Failed to request media URL for track %s: %s',
                track.original_data,
                str(error)
            )
            return
        assert track
        # media = vlc.Media(url)
        # self.media_player.set_media(media)

        # self.media_player.play()

        self.media_player.play(url)

        osd_manager.notify(track)

    @property
    def is_loading(self):
        """
        True if current libVLC state is :attr:`vlc.State.Playing`
        """
        return self._is_loading

    @property
    def is_playing(self):
        """
        True if current libVLC state is :attr:`vlc.State.Playing`
        """
        return not (self.media_player.pause or self.is_loading)

    def play_pause(self):
        """
        Toggle playback, i.e. play if paused or pause if playing.
        """
        self.media_player.pause = not self.media_player.pause

    def get_play_progress(self):
        """
        Return current playback position in range ``[0;1]`` (``float``).
        """
        try:
            return self.media_player.playback_time / self.media_player.duration
        except TypeError:
            return 0

    def get_play_progress_seconds(self):
        """
        Return current playback position in seconds (``int``).
        """
        progress = self.media_player.playback_time
        if progress is None:
            return 0
        return int(progress)

    def get_length_seconds(self):
        """
        Return currently played track's length in seconds (``int``).
        """
        duration = self.media_player.duration
        if duration is None:
            duration = 0
        return int(duration)

    def seek(self, delta):
        """
        Seek to relative position.
        *delta* must be a ``float`` in range ``[-1;1]``.
        """
        try:
            self.media_player.seek(int(self.get_length_seconds() * delta))
        except:
            pass

    def seek_absolute(self, position):
        """
        Seek to absolute position.
        *position* must be a ``float`` in range ``[0;1]``.
        """
        try:
            self.media_player.seek(int(self.get_length_seconds() * position), reference='absolute')
        except:
            pass

    @staticmethod
    def get_equalizer_freqs():
        """
        Return a list of equalizer frequencies for each band.
        """
        return [0] * 8

    def get_equalizer_amps(self):
        """
        Return a list of equalizer amplifications for each band.
        """
        return [0] * 8

    def set_equalizer_value(self, index, amp):
        """
        Set equalizer amplification for specific band.
        """

    def set_equalizer_values(self, amps):
        """
        Set a list of equalizer amplifications for each band.
        """