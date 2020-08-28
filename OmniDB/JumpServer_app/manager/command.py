import queue
import time
import logging
import threading
from .. import service
from ..manager.terminal import terminal_manager


logger = logging.getLogger('JumpServer_app.manager.command')


class Command(object):

    def __init__(self, data):
        self.data = data
        self.upload_failed_count = 0
        self.try_times = 3

    @staticmethod
    def get_storage_type():
        return terminal_manager.get_config_command_storage_type()

    def upload_to_server(self):
        try:
            logger.info('上传命令到server')
            resp_command = service.client.jumpserver_client.upload_command(self.data)
            if resp_command.status_code == 201:
                return True
            else:
                logger.error(f'命令上传失败, 响应状态码: ({resp_command.status_code}), text: ({resp_command.text})')
                return False
        except Exception as exc:
            error = f'命令上传出现异常: ({str(exc)})'
            logger.error(error)
            return False

    @staticmethod
    def upload_to_null():
        logger.info('不上传命令(存储类型为null)')
        return True

    def upload_to_external(self):
        """ TODO: 上传命令到外部存储 """
        pass

    def _upload(self):
        storage_type = self.get_storage_type()
        if storage_type == 'server':
            ok = self.upload_to_server()
        elif storage_type == 'null':
            ok = self.upload_to_null()
        else:
            ok = self.upload_to_external()
        return ok

    def increase_upload_failed_count(self):
        self.upload_failed_count += 1

    def clear_upload_failed_count(self):
        self.upload_failed_count = 0

    def upload(self):
        while True:
            ok = self._upload()
            if ok:
                logger.info('命令上传成功')
                return True
            else:
                logger.error('命令上传失败')
                self.increase_upload_failed_count()
                if self.upload_failed_count <= self.try_times:
                    logger.info(f'重试上传命令({self.upload_failed_count}/{self.try_times})')
                    time.sleep(3)
                    continue
                else:
                    return False


class CommandManager(object):
    """ 命令管理器 """

    def __init__(self):
        self._queue = queue.Queue(1000)

    def get_command_from_queue(self):
        """ 从队列中获取命令 """
        return self._queue.get()

    def put_command_to_queue(self, command):
        """ 推送命令到队列中 """
        command.clear_upload_failed_count()
        self._queue.put(command)

    def start_command_upload_thread(self):
        """ 开启命令上传线程 """
        t = threading.Thread(target=self.start_command_upload)
        t.setDaemon(True)
        t.start()
        return t

    def start_command_upload(self):
        """ 开始命令上传 """
        while True:
            command = self.get_command_from_queue()
            logger.info('从队列获取到命令')
            ok = self.upload_command(command)
            if not ok:
                logger.info('再次将命令加入到队列')
                self.put_command_to_queue(command)

    def upload_command(self, command):
        """ 上传命令 """
        return command.upload()

    def record_command(self, data):
        """ 记录命令 """
        command = Command(data)
        logger.info('将命令加入到队列')
        self.put_command_to_queue(command)

    @staticmethod
    def filter_cmd_input(cmd_input):
        """ TODO: 过滤命令 """
        logger.info(f'过滤命令输入: {cmd_input}')
        return cmd_input

    def pretty_cmd_input(self, cmd_input, db_type):
        """ 格式化cmd_input """
        cmd_input = cmd_input.replace('\n', '\r\n')
        pretty_cmd_input = f'{db_type}> {cmd_input}'
        pretty_cmd_input = '\r\n' + pretty_cmd_input + '\r\n'
        return pretty_cmd_input

    def pretty_cmd_output(self, cmd_output):
        """ 格式化cmd_output"""
        cmd_output = cmd_output.replace('\n', '\r\n')
        pretty_cmd_output = '\r\n' + cmd_output + '\r\n'
        return pretty_cmd_output


command_manager = CommandManager()
