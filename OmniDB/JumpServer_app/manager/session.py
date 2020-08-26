import logging
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


session_manager = SessionManager()
