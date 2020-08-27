import logging
import datetime
from .. import service


logger = logging.getLogger('JumpServer_app.manager.terminal')


class SessionManager(object):

    def __init__(self):
        self.active_sessions = {}

    def add_to_active_sessions(self, session):
        self.active_sessions[session['id']] = session

    def remove_from_active_sessions(self, session):
        self.active_sessions.pop(session['id'], None)

    def get_active_sessions(self):
        return list(self.active_sessions.values())

    def get_active_sessions_ids(self):
        return list(self.active_sessions.keys())

    @staticmethod
    def create_session(data):
        return service.client.jumpserver_client.create_session(data)

    @staticmethod
    def finish_session(session_id):
        data = {
            'is_finished': True,
            'date_end': datetime.datetime.now(),
        }
        return service.client.jumpserver_client.update_session(session_id, data)

    @staticmethod
    def finish_session_replay_upload(session_id):
        data = {
            'has_replay': True
        }
        return service.client.jumpserver_client.update_session(session_id, data)


session_manager = SessionManager()
