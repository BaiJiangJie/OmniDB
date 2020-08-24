import queue
import logging
import threading
from .. import service


logger = logging.getLogger('JumpServer_app.manager.command')


class CommandManager(object):
    """ TODO: 命令管理器 """

    def __init__(self):
        self._queue = queue.Queue(1000)

    def get_command_from_queue(self):
        """ 从队列中get命令 """
        command = self._queue.get()
        return command

    def put_command_to_queue(self, command):
        """ put命令到队列中 """
        logger.info('添加命令到队列')
        self._queue.put(command)
        logger.info('添加命令到队列: 完成')

    def start_command_upload_thread(self):
        """ 开启命令上传线程 """
        logger.info('创建命令上传线程')
        t = threading.Thread(target=self.start_command_upload)
        t.setDaemon(True)
        t.start()
        logger.info('启动命令上传线程')
        return t

    def start_command_upload(self):
        """ 开始命令上传 """
        logger.info('开启命令上传')
        while True:
            logger.info('等待从队列中获取命令')
            command = self.get_command_from_queue()
            logger.info('从队列中获取到命令, 执行上传')
            logger.debug('获取到命令: {}'.format(command))
            self.upload_command(command)

    def _upload_command_to_core(self, command):
        """ 上传命令: JumpServer """
        ret = service.client.jumpserver_client.upload_command(command)
        return ret

    def _upload_command_to_es(self, command):
        """ TODO: 上传命令: ES"""
        return command

    def upload_command(self, command):
        """ TODO: 上传命令 """
        logger.info('开始上传命令')
        command_storage_type = 'core'
        if command_storage_type == 'es':
            logger.info('开始上传命令到ES Server')
            self._upload_command_to_es(command)
        else:
            logger.info('开始上传命令到Core Server')
            self._upload_command_to_core(command)
        logger.info('命令上传成功')

    def record_command(self, command):
        """ 记录命令 """
        logger.info('记录命令')
        self.put_command_to_queue(command)

    def filter_cmd_input(self, cmd_input):
        """ TODO: 过滤命令 """
        logger.info('过滤命令输入: 待开发: {}'.format(cmd_input))
        pass

    def pretty_cmd_input(self, cmd_input):
        """ TODO: 美化输入命令格式 """
        pretty_cmd_input = cmd_input
        return pretty_cmd_input

    def pretty_cmd_output(self, cmd_output):
        """ TODO: 美化输出命令格式 """
        pretty_cmd_output = cmd_output
        return pretty_cmd_output


command_manager = CommandManager()
