import os
import socket
import requests
import logging
from django.conf import settings
from OmniDB import jumpserver_settings
from .. import service

logger = logging.getLogger('JumpServer_app.manager.terminal')


class TerminalManager(object):
    """ TODO: 终端管理器 """

    def __init__(self):
        self.key_file = settings.JUMPSERVER_KEY_FILE
        self.key_dir = os.path.dirname(self.key_file)

    def registry(self):
        """ 注册终端 """
        if os.path.exists(self.key_file):
            logger.info('终端AccessKey文件已存在, 跳过终端注册')
            return True
        else:
            logger.info('执行终端注册')
            return self.perform_registry()

    def perform_registry(self):
        """ 执行终端注册 """
        url = '{}{}'.format(jumpserver_settings.JUMPSERVER_HOST, service.urls.url_terminal_registration)
        data = {
            'name': '[OmniDB] {}'.format(socket.gethostname())
        }
        headers = {
            'Authorization': 'BootstrapToken {}'.format(jumpserver_settings.JUMPSERVER_BOOTSTRAP_TOKEN),
            'X-JMS-ORG': 'ROOT'
        }
        logger.debug('终端注册使用数据: url: {}, data: {}'.format(url, data))
        try:
            resp = requests.post(url=url, data=data, headers=headers)
        except Exception as exc:
            logger.error('终端注册请求异常, {}'.format(str(exc)), exc_info=True)
            return False
        else:
            if resp.status_code == 201:
                try:
                    logger.debug('获取终端AccessKey信息')
                    resp_json_data = resp.json()
                    access_key_id = resp_json_data['service_account']['access_key']['id']
                    access_key_secret = resp_json_data['service_account']['access_key']['secret']
                except Exception as exc:
                    logger.error('获取终端AccessKey信息异常: {}, resp_text: {}'.format(str(exc), resp.text), exc_info=True)
                    return False
                else:
                    try:
                        logger.debug('保存终端AccessKey信息')
                        if not os.path.isdir(self.key_dir):
                            logger.debug('创建终端AccessKey文件目录: {}'.format(self.key_dir))
                            os.makedirs(self.key_dir, exist_ok=True)
                        with open(self.key_file, 'w') as f:
                            message = '{}:{}'.format(access_key_id, access_key_secret)
                            f.write(message)
                    except Exception as exc:
                        logger.error('保存终端AccessKey信息异常: {}'.format(str(exc)), exc_info=True)
                        return False
                    else:
                        logger.debug('保存终端AccessKey信息成功')
                        return True
            else:
                logger.error('终端注册请求响应状态码不符合预期, 响应状态码: {}, text: {}'.format(resp.status_code, resp.text))
                return False

    @staticmethod
    def check_validity():
        """ 校验终端有效性 """
        return service.client.jumpserver_client.check_terminal_validity()


terminal_manager = TerminalManager()
