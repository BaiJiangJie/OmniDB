import os
import logging
from django.conf import settings
from .. import service

logger = logging.getLogger('JumpServer_app.manager.terminal')


class TerminalManager(object):
    """ 终端管理器 """

    def __init__(self):
        self.key_file = settings.JUMPSERVER_KEY_FILE

    def registry(self):
        """ 注册终端 """
        if os.path.exists(self.key_file):
            logger.info('终端AccessKey文件已存在, 跳过终端注册')
            return True
        else:
            return self.perform_registry()

    def perform_registry(self):
        """ 执行终端注册 """
        try:
            logger.info('执行终端注册')
            resp_terminal = service.client.jumpserver_client.registry_terminal()
            if resp_terminal.status_code == 201:
                logger.info('获取终端AccessKey信息')
                resp_json_data = resp_terminal.json()
                access_key_id = resp_json_data['service_account']['access_key']['id']
                access_key_secret = resp_json_data['service_account']['access_key']['secret']
                logger.info('保存终端AccessKey信息')
                key_dir = os.path.dirname(self.key_file)
                if not os.path.isdir(key_dir):
                    os.makedirs(key_dir, exist_ok=True)
                with open(self.key_file, 'w') as f:
                    message = f'{access_key_id}:{access_key_secret}'
                    f.write(message)
                return True
            else:
                error = f'注册终端响应不符合预期, 响应状态码: ({resp_terminal.status_code}), text: ({resp_terminal.text})'
                logger.error(error, exc_info=True)
                return False
        except Exception as exc:
            logger.error(f'执行终端注册异常: ({str(exc)})', exc_info=True)
            return False

    @staticmethod
    def check_validity():
        """ 校验终端有效性 """
        return service.client.jumpserver_client.check_terminal_validity()


terminal_manager = TerminalManager()
