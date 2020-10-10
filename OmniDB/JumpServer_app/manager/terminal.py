import os
import time
import logging
import threading
from django.conf import settings
from .. import service
from .session import session_manager

logger = logging.getLogger('JumpServer_app.manager.terminal')


class TerminalManager(object):
    """ 终端管理器 """

    def __init__(self):
        self.key_file = settings.JUMPSERVER_KEY_FILE
        self.config = {}

    def try_registry(self):
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
                logger.error(error)
                return False
        except Exception as exc:
            logger.error(f'执行终端注册异常: ({str(exc)})')
            return False

    @staticmethod
    def check_validity():
        """ 校验终端有效性 """
        logger.info('检测终端有效性')
        return service.client.jumpserver_client.check_terminal_validity()

    def set_config(self, config):
        if isinstance(config, dict):
            self.config = config

    def get_config(self):
        return self.config

    def get_config_heartbeat_interval(self):
        config = self.get_config()
        heartbeat_interval = config['TERMINAL_HEARTBEAT_INTERVAL']
        return heartbeat_interval

    def get_config_command_storage(self):
        config = self.get_config()
        return config['TERMINAL_COMMAND_STORAGE']

    def get_config_command_storage_type(self):
        config_command_storage = self.get_config_command_storage()
        return config_command_storage['TYPE']

    def get_config_replay_storage(self):
        config = self.get_config()
        return config['TERMINAL_REPLAY_STORAGE']

    def get_config_replay_storage_type(self):
        config_replay_storage = self.get_config_replay_storage()
        return config_replay_storage['TYPE']

    def start_timing_fetch_config_thread(self):
        t = threading.Thread(target=self.start_timing_fetch_config)
        t.setDaemon(True)
        t.start()

    def start_timing_fetch_config(self):
        while True:
            logger.debug('定时获取终端配置')
            config = self.fetch_config()
            self.set_config(config)
            time.sleep(10)

    @staticmethod
    def fetch_config():
        try:
            logger.info('获取终端配置')
            resp_config = service.client.jumpserver_client.fetch_terminal_config()
            if resp_config.status_code == 200:
                config = resp_config.json()
                return config
            else:
                logger.error(f'获取终端配置失败, 响应状态码: ({resp_config.status_code}), text: ({resp_config.text})')
                return None
        except Exception as exc:
            logger.error(f'获取终端配置出现异常: ({str(exc)})')
            return None

    def start_keep_heartbeat_thread(self):
        t = threading.Thread(target=self.start_keep_heartbeat)
        t.setDaemon(True)
        t.start()

    def start_keep_heartbeat(self):
        while True:
            try:
                logger.debug('保持终端心跳')
                resp_heartbeat = service.client.jumpserver_client.keep_terminal_heartbeat()
                if resp_heartbeat.status_code == 201:
                    session_tasks = resp_heartbeat.json()
                    logger.debug(f'保持终端心跳响应: ({session_tasks})')
                    self.handle_terminal_tasks(session_tasks)
                else:
                    logger.error(f'保持终端心跳失败, 响应状态码: ({resp_heartbeat.status_code}), text: ({resp_heartbeat.text})')
            except Exception as exc:
                logger.error(f'保持终端心跳出现异常: ({str(exc)})')
            heartbeat_interval = self.get_config_heartbeat_interval()
            logger.debug(f'终端心跳间隔: ({heartbeat_interval})')
            time.sleep(heartbeat_interval)

    def handle_terminal_tasks(self, session_tasks):
        for task in session_tasks:
            task_id = task['id']
            task_name = task['name']
            session_id = task['args']
            if task_name == 'kill_session':
                self.handle_terminal_task_kill_session(task_id, session_id)

    def handle_terminal_task_kill_session(self, task_id, session_id):
        try:
            msg = f'处理终端任务[kill_session](task_id:{task_id};session_id:{session_id}))'
            logger.info(msg)
            logger.info(f'终断WebSocket(session_id:{session_id})')
            session_manager.terminate_ws_object(session_id)
            logger.info(f'完成终端任务(task_id:{task_id})')
            service.client.jumpserver_client.finish_terminal_task(task_id)
        except Exception as exc:
            logger.error(f'处理终端任务[kill_session]出现异常({str(exc)})')


terminal_manager = TerminalManager()
