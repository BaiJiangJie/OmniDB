import os
import socket
import logging
from django.conf import settings
from httpsig.requests_auth import HTTPSignatureAuth
from OmniDB import jumpserver_settings
import requests
from . import urls
from urllib.parse import urljoin
from .. import utils
from ..manager.session import session_manager


logger = logging.getLogger('JumpServer_app.service.client')


class JumpServerRequester(object):
    """ JumpServer Request (API层面) """
    def __init__(self):
        self._key_file = settings.JUMPSERVER_KEY_FILE

        self._allowed_method = ['get', 'post', 'patch']
        self._host = None
        self._auth = None
        self._headers = None

    def set_host(self, host):
        self._host = host

    def set_auth(self, auth):
        self._auth = auth

    def set_headers(self, headers):
        self._headers = headers

    def init_host(self):
        host = jumpserver_settings.JUMPSERVER_HOST
        self.set_host(host)

    def init_auth(self):
        if not os.path.exists(self._key_file):
            logger.error(f'AccessKey文件不存在({self._key_file})')
        try:
            with open(self._key_file, 'r') as f:
                access_key = f.read()
            access_key_id, access_key_secret = access_key.split(':')
            signature_headers = ['(request-target)', 'accept', 'date', 'host']
            auth = HTTPSignatureAuth(
                key_id=access_key_id, secret=access_key_secret,
                algorithm='hmac-sha256', headers=signature_headers
            )
            self.set_auth(auth)
        except Exception as exc:
            logger.error(f'初始化请求auth出现异常: {str(exc)}', exc_info=True)

    def init_headers(self):
        headers = {
            'Accept': 'application/json',
            'Date': "Mon, 17 Feb 2014 06:11:05 GMT",
            'X-JMS-ORG': 'ROOT'
        }
        self.set_headers(headers)

    def get_host(self):
        if self._host is None:
            self.init_host()
        return self._host

    def get_auth(self):
        if self._auth is None:
            self.init_auth()
        return self._auth

    def get_headers(self):
        if self._headers is None:
            self.init_headers()
        return self._headers

    def build_url(self, url):
        host = self.get_host()
        url = urljoin(host, url)
        return url

    def _raw_requests(self, method, url, *args, **kwargs):
        method = method.lower()
        if method not in self._allowed_method:
            logger.error('请求方法不被允许: {}'.format(method))
            return

        try:
            url = self.build_url(url)
            return getattr(requests, method)(url, *args, **kwargs)
        except Exception as exc:
            logger.error(f'请求异常: {str(exc)}')
            raise

    def _requests_by_access_key(self, method, url, *args, **kwargs):
        kwargs.update({'auth': self.get_auth(), 'headers': self.get_headers()})
        return self._raw_requests(method, url, *args, **kwargs)

    def get_terminal_profile(self):
        profile_url = urls.URL_USER_PROFILE
        return self._requests_by_access_key(method='get', url=profile_url)

    def get_user_profile_by_cookies(self, cookies):
        profile_url = urls.URL_USER_PROFILE
        return self._raw_requests(method='get', url=profile_url, cookies=cookies)

    def get_database_by_id(self, _id):
        database_url = urls.URL_DATABASE_DETAIL.format(database_id=_id)
        return self._requests_by_access_key(method='get', url=database_url)

    def get_system_user_by_id(self, _id):
        system_user_url = urls.URL_SYSTEM_USER_DETAIL.format(system_user_id=_id)
        return self._requests_by_access_key(method='get', url=system_user_url)

    def get_system_user_auth_info_by_id(self, _id):
        system_user_auth_info_url = urls.URL_SYSTEM_USER_AUTH_INFO.format(system_user_id=_id)
        return self._requests_by_access_key(method='get', url=system_user_auth_info_url)

    def get_user_database_permission_validate(self, user_id, database_id, system_user_id):
        user_database_permission_validate_url = urls.URL_USER_DATABASE_PERMISSION_VALIDATE
        query_string = f'user_id={user_id}&database_app_id={database_id}&system_user_id={system_user_id}'
        url = f'{user_database_permission_validate_url}?{query_string}'
        return self._requests_by_access_key(method='get', url=url)

    def post_session(self, data):
        session_url = urls.URL_SESSION
        return self._requests_by_access_key(method='post', url=session_url, data=data)

    def patch_session(self, _id, data):
        session_detail_url = urls.URL_SESSION_DETAIL.format(session_id=_id)
        return self._requests_by_access_key(method='patch', url=session_detail_url, data=data)

    def post_command(self, data):
        command_url = urls.URL_COMMAND
        if not isinstance(data, list):
            data = [data]
        return self._requests_by_access_key(method='post', url=command_url, json=data)

    def post_terminal(self):
        registry_terminal_url = urls.URL_TERMINAL_REGISTRATION
        data = {
            'name': '[OmniDB] {}'.format(socket.gethostname())
        }
        headers = {
            'Authorization': 'BootstrapToken {}'.format(jumpserver_settings.JUMPSERVER_BOOTSTRAP_TOKEN),
            'X-JMS-ORG': 'ROOT'
        }
        return self._raw_requests(method='post', url=registry_terminal_url, data=data, headers=headers)

    def get_terminal_config(self):
        terminal_config_url = urls.URL_TERMINAL_CONFIG
        return self._requests_by_access_key(method='get', url=terminal_config_url)

    def post_terminal_status(self, data):
        terminal_status_url = urls.URL_TERMINAL_STATUS
        return self._requests_by_access_key(method='post', url=terminal_status_url, json=data)

    def post_replay(self, session_id, files):
        session_replay_url = urls.URL_SESSION_REPLAY.format(session_id=session_id)
        return self._requests_by_access_key(method='post', url=session_replay_url, files=files)


class JumpServerClient(object):
    """ JumpServer Client (业务层面) """

    def __init__(self):
        self.requester = JumpServerRequester()

    def get_terminal_profile(self):
        return self.requester.get_terminal_profile()

    def get_user_profile_by_cookies(self, cookies):
        return self.requester.get_user_profile_by_cookies(cookies)

    def validate_user_database_permission(self, user_id, database_id, system_user_id):
        return self.requester.get_user_database_permission_validate(
            user_id=user_id, database_id=database_id, system_user_id=system_user_id
        )

    def get_database(self, database_id):
        return self.requester.get_database_by_id(database_id)

    def get_system_user(self, system_user_id):
        return self.requester.get_system_user_by_id(system_user_id)

    def get_system_user_auth_info(self, system_user_id):
        return self.requester.get_system_user_auth_info_by_id(system_user_id)

    def create_session(self, data):
        return self.requester.post_session(data)

    def update_session(self, _id, data):
        return self.requester.patch_session(_id, data)

    def registry_terminal(self):
        return self.requester.post_terminal()

    def check_terminal_validity(self):
        try:
            resp_terminal_profile = self.get_terminal_profile()
            if resp_terminal_profile.status_code == 200:
                return True
            else:
                return False
        except Exception as exc:
            logger.error(f'校验终端有效性异常: ({str(exc)})')
            return False

    def fetch_terminal_config(self):
        return self.requester.get_terminal_config()

    def keep_terminal_heartbeat(self):
        active_sessions = session_manager.get_active_sessions_ids()
        data = {'sessions': active_sessions}
        return self.requester.post_terminal_status(data)

    def upload_command(self, command):
        command['input'] = command['input'][:128]
        command['output'] = command['output'][:1024]
        return self.requester.post_command(command)

    def upload_replay(self, file_path_gz, target):
        session_id = os.path.basename(target).split('.')[0]
        with open(file_path_gz, 'rb') as f:
            files = {'file': f}
            return self.requester.post_replay(session_id, files=files)


jumpserver_client = JumpServerClient()
