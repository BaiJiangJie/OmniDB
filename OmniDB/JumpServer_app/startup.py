import logging
from .manager.terminal import terminal_manager
from .manager.command import command_manager

logger = logging.getLogger('JumpServer_app.startup')


def register_terminal():
    """ 注册JumpServer终端: OmniDB """
    ok = terminal_manager.try_registry()
    if not ok:
        logger.error('终端注册失败, 尝试删除AccessKey文件并重新启动服务 (文件路径: {})'.format(terminal_manager.key_file))
        return False

    is_valid = terminal_manager.check_validity()
    if not is_valid:
        logger.error('终端无效, 尝试删除AccessKey文件并重新启动服务 (文件路径: {})'.format(terminal_manager.key_file))
        return False

    logger.info('终端注册成功')
    return True


def start_timing_fetch_terminal_config_thread():
    """ 开启定时获取终端配置线程 """
    terminal_manager.start_timing_fetch_config_thread()


def start_keep_terminal_heartbeat_thread():
    """ 开启保持终端心跳线程 """
    terminal_manager.start_keep_heartbeat_thread()


def start_command_upload_thread():
    """ 开启命令上传线程 """
    command_manager.start_command_upload_thread()

