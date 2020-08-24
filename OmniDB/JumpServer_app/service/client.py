import os
import logging
from django.conf import settings
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
        # logger.debug('初始化JumpServer Client host参数')
        self._host = OmniDB.jumpserver_settings.JUMPSERVER_HOST

    def init_auth(self):
        # logger.debug('初始化JumpServer Client auth参数')
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
        # logger.debug('初始化JumpServer Client headers参数')
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
            logger.debug('请求方法不允许: {}'.format(method))
            return None

        url = '{}{}'.format(self.host, url)
        params = {
            'auth': self.auth, 'headers': self.headers
        }
        kwargs.update(params)
        # logger.debug('发送请求: method: {}, url: {}, args: {}, kwargs: {}'.format(method.upper(), url, args, kwargs))
        try:
            resp = getattr(requests, method)(url, *args, **kwargs)
        except Exception as exc:
            logger.error('请求异常: {}'.format(str(exc)), exc_info=True)
            return None
        else:
            return resp

    def get_terminal_profile(self):
        logger.info('请求终端用户个人信息')
        url = urls.url_user_profile
        resp = self.request('get', url)
        if resp is None:
            logger.info('请求终端用户个人信息: 失败')
            return None
        elif resp.status_code == 200:
            logger.info('请求终端用户个人信息: 成功')
            resp_json = resp.json()
            logger.debug('响应数据: {}'.format(resp_json))
            return resp_json
        else:
            logger.info('请求终端用户个人信息: 失败')
            logger.debug('响应信息: {}'.format(resp.text))
            return None

    def check_terminal_validity(self):
        logger.info('检测终端用户有效性')
        profile = self.get_terminal_profile()
        if profile is None:
            logger.info('终端用户: 无效')
            return False
        role = profile.get('role')
        if role is None:
            logger.info('终端用户个人信息中缺少字段: role')
            return False
        elif role != 'App':
            logger.info('终端用户角色({})不是App'.format(role))
            return False
        else:
            logger.info('终端用户: 有效')
            return True

    def validate_user_database_permission(self, user_id, database_id, system_user_id):
        logger.info('校验用户数据库权限')
        params = 'user_id={}&database_app_id={}&system_user_id={}'.format(
            user_id, database_id, system_user_id
        )
        url = '{}?{}'.format(urls.url_user_database_permission_validate, params)
        resp = self.request('get', url)
        if resp is None:
            logger.info('校验数据库权限: 失败')
            return False
        elif resp.status_code == 200:
            logger.info('校验用户数据库权限: 成功')
            resp_json = resp.json()
            logger.debug('响应数据: {}'.format(resp_json))
            return True
        else:
            logger.info('校验用户数据库权限: 失败')
            logger.debug('响应信息: {}'.format(resp.text))
            return False

    def get_database(self, database_id):
        logger.info('请求数据库信息')
        url = urls.url_database_detail.format(database_id=database_id)
        resp = self.request('get', url)
        if resp is None:
            logger.info('请求数据库信息: 失败')
            return None
        elif resp.status_code == 200:
            logger.info('请求数据库信息: 成功')
            resp_json = resp.json()
            logger.debug('响应数据: {}'.format(resp_json))
            return resp_json
        else:
            logger.info('请求数据库信息: 失败')
            logger.debug('响应信息: {}'.format(resp.text))
            return None

    def get_system_user(self, system_user_id):
        logger.info('请求系统用户信息')
        url = urls.url_system_user_detail.format(system_user_id=system_user_id)
        resp = self.request('get', url)
        if resp is None:
            logger.info('请求系统用户信息: 失败')
            return None
        elif resp.status_code == 200:
            logger.info('请求系统用户信息: 成功')
            resp_json = resp.json()
            logger.debug('响应数据: {}'.format(resp_json))
            return resp_json
        else:
            logger.info('请求系统用户信息: 失败')
            logger.debug('响应信息: {}'.format(resp.text))
            return None

    def get_system_user_auth_info(self, system_user_id):
        logger.info('请求系统用户认证信息')
        url = urls.url_system_user_auth_info.format(system_user_id=system_user_id)
        resp = self.request('get', url)
        if resp is None:
            logger.info('请求系统用户认证信息: 失败')
            return None
        elif resp.status_code == 200:
            logger.info('请求系统用户认证信息: 成功')
            resp_json = resp.json()
            logger.debug('响应数据: {}'.format(resp_json))
            return resp_json
        else:
            logger.info('请求系统用户认证信息: 失败')
            logger.debug('响应信息: {}'.format(resp.text))
            return None

    def create_session(self, data):
        logger.info('请求创建会话')
        url = urls.url_session
        resp = self.request('post', url, data=data)
        if resp is None:
            logger.info('请求创建会话: 失败')
            return None
        elif resp.status_code == 201:
            logger.info('请求创建会话: 成功')
            resp_json = resp.json()
            logger.debug('响应数据: {}'.format(resp_json))
            return resp_json
        else:
            logger.info('请求创建会话: 失败')
            logger.debug('响应信息: {}'.format(resp.text))
            return None

    def upload_command(self, command):
        """ TODO: 上传命令 """
        logger.info('请求上传命令')
        if isinstance(command, dict):
            command = [command]
        url = urls.url_command
        resp = self.request('post', url, json=command)
        if resp is None:
            logger.info('请求上传命令: 失败')
            return None
        if resp.status_code == 201:
            logger.info('请求上传命令: 成功')
            resp_json = resp.json()
            logger.debug('响应数据: {}'.format(resp_json))
            return resp_json
        else:
            logger.info('请求上传命令: 失败')
            logger.debug('响应信息: {}'.format(resp.text))
            return None


jumpserver_client = JumpServerClient()
