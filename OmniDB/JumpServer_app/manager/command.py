import queue
import logging
import threading
from .. import service
from ..manager.terminal import terminal_manager


logger = logging.getLogger('JumpServer_app.manager.command')


class CommandManager(object):
    """ 命令管理器 """

    def __init__(self):
        self._queue = queue.Queue(1000)

    def get_command_from_queue(self):
        """ 从队列中获取命令 """
        command = self._queue.get()
        return command

    def put_command_to_queue(self, command):
        """ 推送命令到队列中 """
        logger.info('推送命令到队列')
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
            if ok:
                logger.info('命令上传成功')
            else:
                # TODO: 重传机制
                pass

    @staticmethod
    def upload_command_to_core(command):
        try:
            logger.info('上传命令到server')
            resp_command = service.client.jumpserver_client.upload_command(command)
            if resp_command.status_code == 201:
                return True
            else:
                logger.error(f'命令上传失败, 响应状态码: ({resp_command.status_code}), text: ({resp_command.text})')
                return False
        except Exception as exc:
            error = f'命令上传出现异常: ({str(exc)})'
            logger.error(error, exc_info=True)
            return False

    @staticmethod
    def upload_command_to_null(command):
        logger.info('不上传命令(命令存储类型为null)')
        return True

    @staticmethod
    def upload_command_to_es(command):
        #: TODO: 上传命令到es
        logger.info('上传命令到es')
        return command

    @property
    def storage_type(self):
        return terminal_manager.get_config_command_storage_type()

    def upload_command(self, command):
        """ 上传命令 """
        if self.storage_type == 'es':
            ok = self.upload_command_to_es(command)
        elif self.storage_type == 'null':
            ok = self.upload_command_to_null(command)
        else:
            ok = self.upload_command_to_core(command)
        return ok

    def record_command(self, command):
        """ 记录命令 """
        self.put_command_to_queue(command)

    @staticmethod
    def filter_cmd_input(cmd_input):
        """ TODO: 过滤命令 """
        logger.info('过滤命令输入, 待开发: {}'.format(cmd_input))
        return cmd_input

    def pretty_cmd_input(self, cmd_input):
        """ 格式化cmd_input """
        pretty_cmd_input = cmd_input
        return pretty_cmd_input

    def pretty_cmd_output(self, cmd_output):
        """ 格式化cmd_output"""
        pretty_cmd_output = cmd_output
        return pretty_cmd_output


command_manager = CommandManager()
