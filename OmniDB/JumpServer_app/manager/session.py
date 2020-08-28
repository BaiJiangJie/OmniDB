import logging
import datetime
from .. import service


logger = logging.getLogger('JumpServer_app.manager.terminal')


class SessionManager(object):

    def __init__(self):
        self.active_sessions = {}
        self.ws_objects = {}

    def add_ws_object(self, session_id, ws_object):
        self.ws_objects[session_id] = ws_object

    def remove_ws_object(self, session_id):
        self.ws_objects.pop(session_id, None)

    def get_ws_object(self, session_id):
        return self.ws_objects.get(session_id)

    def terminate_ws_object(self, session_id):
        ws_object = self.get_ws_object(session_id)
        if ws_object is None:
            return
        ws_object.on_terminate()

    def add_active_session(self, session):
        self.active_sessions[session['id']] = session

    def remove_active_session(self, session_id):
        self.active_sessions.pop(session_id, None)

    def get_active_sessions(self):
        return list(self.active_sessions.values())

    def get_active_sessions_ids(self):
        return list(self.active_sessions.keys())

    @staticmethod
    def create_session(data):
        return service.client.jumpserver_client.create_session(data)

    @staticmethod
    def finish_session(session_id):
        return service.client.jumpserver_client.finish_session(session_id)

    @staticmethod
    def finish_session_replay_upload(session_id):
        return service.client.jumpserver_client.finish_session_replay_upload(session_id)


session_manager = SessionManager()
