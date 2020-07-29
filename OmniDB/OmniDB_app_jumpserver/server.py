import os
import requests
from httpsig.requests_auth import HTTPSignatureAuth
from OmniDB import settings


class Server(object):
    CORE_URL = settings.CORE_URL

    def __init__(self):
        with open(settings.JUMPSERVER_KEY_FILE, 'r') as f:
            key_id_secret = f.read()

        self.key_id, self.secret = key_id_secret.split(':')

        signature_headers = ['(request-target)', 'accept', 'date', 'host']
        self.headers = {
            'Accept': 'application/json',
            'Date': "Mon, 17 Feb 2014 06:11:05 GMT",
            'X-JMS-ORG': 'ROOT',
        }
        self.auth = HTTPSignatureAuth(
            key_id=self.key_id, secret=self.secret,
            algorithm='hmac-sha256', headers=signature_headers
        )

    def get(self, url, *args, **kwargs):
        return requests.get(url, *args, **kwargs)

    def post(self, url, *args, **kwargs):
        return requests.post(url, *args, **kwargs)

    def request(self, method, url, *args, **kwargs):
        url = '{}{}'.format(settings.CORE_URL, url)
        kwargs.update({
            'auth': self.auth,
            'headers': self.headers
        })
        if method == 'get':
            return self.get(url, *args, **kwargs)
        elif method == 'post':
            return self.post(url, *args, **kwargs)

    def get_database_info(self, database_id):
        print('Get database info')
        url = '/api/v1/applications/database-apps/{}/'.format(database_id)
        res = self.request('get', url)
        if res.status_code == 200:
            print(res.json())
            return res.json()
        else:
            print(res.text)
            return None

    def get_system_user_info(self, system_user_id):
        print('Get system user info')
        url = '/api/v1/assets/system-users/{}/'.format(system_user_id)
        res = self.request('get', url)
        if res.status_code == 200:
            print(res.json())
            return res.json()
        else:
            print(res.text)
            return None

    def get_system_user_auth_info(self, system_user_id):
        print('Get system user auth info')
        url = '/api/v1/assets/system-users/{}/auth-info/'.format(system_user_id)
        res = self.request('get', url)
        if res.status_code == 200:
            print(res.json())
            return res.json()
        else:
            print(res.text)
            return None

    def check_user_database_permission(self, user_id, database_id, system_user_id):
        print('Check user database permission')
        url = '/api/v1/perms/database-app-permissions/user/validate/'
        params = 'user_id={}&database_app_id={}&system_user_id={}'.format(
            user_id, database_id, system_user_id
        )
        url = '{}?{}'.format(url, params)
        res = self.request('get', url)
        if res.status_code == 200:
            print(res.json())
            return True
        else:
            print(res.text)
            return False


core_server = Server()
