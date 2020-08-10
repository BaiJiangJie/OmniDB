import os
import logging
from django.conf import settings
from werkzeug.local import LocalProxy
from httpsig.requests_auth import HTTPSignatureAuth
import OmniDB.jumpserver_settings
import requests
from . import urls


logger = logging.getLogger('JumpServer_app.service.client')


class JumpServerClient(object):

    def __init__(self):
        self.methods = ['get', 'post', 'put', 'patch']
        self._host = None
        self._auth = None
        self._headers = None

    def init_host(self):
        logger.info('初始化JumpServer Client host参数')
        self._host = OmniDB.jumpserver_settings.JUMPSERVER_HOST

    def init_auth(self):
        logger.info('初始化JumpServer Client auth参数')
        key_file = settings.JUMPSERVER_KEY_FILE
        if not os.path.exists(key_file):
            logger.error('Access Key文件不存在')
            return
        with open(key_file, 'r') as f:
            key = f.read()
        key_id, key_secret = key.split(':')
        signature_headers = ['(request-target)', 'accept', 'date', 'host']
        auth = HTTPSignatureAuth(
            key_id=key_id, secret=key_secret, algorithm='hmac-sha256', headers=signature_headers
        )
        self._auth = auth

    def init_headers(self):
        logger.info('初始化JumpServer Client headers参数')
        headers = {
            'Accept': 'application/json',
            'Date': "Mon, 17 Feb 2014 06:11:05 GMT",
            'X-JMS-ORG': 'ROOT'
        }
        self._headers = headers

    @property
    def host(self):
        if self._host is None:
            self.init_host()
        return self._host

    @property
    def auth(self):
        if self._auth is None:
            self.init_auth()
        return self._auth

    @property
    def headers(self):
        if self._headers is None:
            self.init_headers()
        return self._headers

    def request(self, method, url, *args, **kwargs):
        method = method.lower()
        if method not in self.methods:
            logger.error('请求方法不允许: {}'.format(method))
            return

        url = '{}{}'.format(self.host, url)
        params = {
            'auth': self.auth,
            'headers': self.headers
        }
        kwargs.update(params)
        logger.info('发送请求: {} {}'.format(method.upper(), url))
        return getattr(requests, method)(url, *args, **kwargs)

    def get_terminal_profile(self):
        logger.info('请求获取终端用户个人信息')
        url = urls.url_users_profile
        resp = self.request('get', url)
        if resp.status_code == 200:
            logger.info('获取终端用户个人信息成功')
            profile = resp.json()
            logger.debug(profile)
            return profile
        else:
            logger.error('获取终端用户个人信息失败: {}'.format(resp.text))
            return None

    def check_terminal_validity(self):
        logger.info('检测终端用户有效性')

        profile = self.get_terminal_profile()
        if profile is None:
            logger.info('终端用户已失效')
            return False

        role = profile.get('role')

        if role is None:
            logger.info('终端用户个人信息中缺少字段: role')
            return False

        if role != 'App':
            logger.info('终端用户角色({})不是App'.format(role))
            return False

        logger.info('终端用户有效')
        return True


def get_jumpserver_client():
    return JumpServerClient()


jumpserver_client = LocalProxy(get_jumpserver_client)
