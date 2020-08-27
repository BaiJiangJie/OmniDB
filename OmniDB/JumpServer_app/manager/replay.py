import json
import os
import datetime
import logging
import time
from django.conf import settings
from .. import utils, service
from .terminal import terminal_manager

logger = logging.getLogger('JumpServer_app.manager.replay')


class Replay(object):

    def __init__(self, session_id):
        self.session_id = session_id
        self.time_start = time.time()
        self.filename = self.session_id
        self.filename_gz = f'{self.filename}.replay.gz'
        self.base_dir = settings.REPLAY_DIR
        date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        self.file_dir = os.path.join(self.base_dir, date)
        self.make_file_dir()
        self.file_path = os.path.join(self.file_dir, self.filename)
        self.file_path_gz = os.path.join(self.file_dir, self.filename_gz)
        self.upload_target = f'{date}/{self.filename_gz}'
        self._f = open(self.file_path, 'at')

        self.upload_failed_count = 0
        self.try_times = 3

    def make_file_dir(self):
        if not os.path.isdir(self.file_dir):
            os.makedirs(self.file_dir, exist_ok=True)

    def _write(self, message):
        self._f.write(message)

    def write_record(self, message):
        timedelta = time.time() - self.time_start
        record = f'"{timedelta}":{json.dumps(message)},'
        self._write(record)

    def start(self):
        self._write('{')

    def record(self, command):
        cmd_input = command['input']
        cmd_output = command['output']
        self.write_record(cmd_input)
        self.write_record(cmd_output)

    def end(self):
        logger.info('结束记录录像')
        self._write('"0":""')
        self._write('}')
        self._f.close()

    def gzip(self):
        logger.info('压缩录像文件')
        utils.gzip_file(self.file_path, self.file_path_gz)
        logger.info(f'压缩录像文件路径({self.file_path_gz})')

    @staticmethod
    def get_storage_type():
        return terminal_manager.get_config_replay_storage_type()

    def upload_to_server(self):
        return service.client.jumpserver_client.upload_replay(self.file_path_gz, self.upload_target)

    @staticmethod
    def upload_to_null():
        logger.info('不上传录像(存储类型为null)')
        return True

    def upload_to_external(self):
        """ TODO: 上传录像到外部存储 """
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

    def delete_file_gz(self):
        logger.info(f'删除录像压缩文件({self.file_path_gz})')
        os.unlink(self.file_path_gz)

    def upload(self):
        logger.info('上传录像文件')
        if not os.path.isfile(self.file_path_gz):
            logger.error(f'没有发现录像文件({self.file_path_gz})')
            return
        if os.path.getsize(self.file_path_gz) == 0:
            logger.error(f'录像文件大小为0({self.file_path_gz})')
            self.delete_file_gz()
            return
        while True:
            ok = self._upload()
            if ok:
                logger.info('录像上传成功')
                self.delete_file_gz()
                return True
            else:
                logger.error('录像上传失败')
                self.increase_upload_failed_count()
                if self.upload_failed_count <= self.try_times:
                    logger.info(f'重试上传录像({self.upload_failed_count}/{self.try_times})')
                    time.sleep(3)
                    continue
                else:
                    return False


class ReplayManager(object):
    """ 录像管理器 """

    def __init__(self):
        self._replays = {}

    def add_replay(self, replay):
        self._replays[replay.session_id] = replay

    def get_replay(self, session_id):
        return self._replays.get(session_id)

    def start_replay(self, session_id):
        replay = Replay(session_id)
        self.add_replay(replay)
        replay.start()

    def record_replay(self, command):
        session_id = command['session']
        replay = self.get_replay(session_id)
        replay.record(command)

    def end_replay(self, session_id):
        replay = self.get_replay(session_id)
        replay.end()
        replay.gzip()
        replay.upload()


replay_manager = ReplayManager()
