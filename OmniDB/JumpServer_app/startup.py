import logging
from .manager.terminal import terminal_manager
from .manager.command import command_manager

logger = logging.getLogger('JumpServer_app.startup')


def register_terminal():
    """ 注册JumpServer终端: OmniDB """
    ok = terminal_manager.registry()
    if ok:
        logger.info('校验终端有效性')
        is_valid = terminal_manager.check_validity()
        if is_valid:
            logger.info('终端有效')
            return True
        else:
            logger.error('终端无效, 尝试删除AccessKey文件并重新启动服务 (文件路径: {})'.format(terminal_manager.key_file))
            return False
    else:
        return False


def start_timing_fetch_terminal_config_thread():
    """ 开启定时获取终端配置线程 """
    terminal_manager.start_timing_fetch_config_thread()


def start_keep_terminal_heartbeat_thread():
    """ 开启保持终端心跳线程 """
    terminal_manager.start_keep_heartbeat_thread()


def start_command_upload_thread():
    """ 开启命令上传线程 """
    command_manager.start_command_upload_thread()

