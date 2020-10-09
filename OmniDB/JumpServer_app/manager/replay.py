import os
import time
import json
import logging
import datetime
import threading
import jms_storage
from django.conf import settings
from .. import utils, service
from .terminal import terminal_manager

logger = logging.getLogger('JumpServer_app.manager.replay')


class Replay(object):

    def __init__(self, session_id, replay_date=None):

        self.session_id = session_id

        # 录像开始时间
        self.time_start = None
        # 录像文件对象
        self._f = None

        # 录像上传参数
        if replay_date is None:
            replay_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')
        replay_dir = os.path.join(settings.REPLAY_DIR, replay_date)
        if not os.path.isdir(replay_dir):
            os.makedirs(replay_dir, exist_ok=True)

        self.filename = session_id
        self.filepath = os.path.join(replay_dir, self.filename)

        self.gz_filename = f'{session_id}.replay.gz'
        self.gz_filepath = os.path.join(replay_dir, self.gz_filename)

        self.upload_target = f'{replay_date}/{self.gz_filename}'

        self.upload_failed_count = 0
        self.try_times = 3

    def _open(self):
        self._f = open(self.filepath, 'at')

    def _close(self):
        self._f.close()

    def _write(self, message):
        self._f.write(message)

    def write_record(self, message):
        timedelta = time.time() - self.time_start
        record = f'"{timedelta}":{json.dumps(message)},'
        self._write(record)

    def start(self):
        self.time_start = time.time()
        self._open()
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
        self._close()

    def gzip(self):
        logger.info(f'压缩录像文件({self.filepath})')
        utils.gzip_file(self.filepath, self.gz_filepath)
        logger.info(f'录像文件压缩完成({self.gz_filepath})')

    @staticmethod
    def get_storage_type():
        return terminal_manager.get_config_replay_storage_type()

    @staticmethod
    def get_storage_config():
        return terminal_manager.get_config_replay_storage()

    def upload_to_server(self):
        return service.client.jumpserver_client.upload_replay(self.gz_filepath, self.upload_target)

    @staticmethod
    def upload_to_null():
        logger.info('不上传录像(存储类型为null)')
        return True

    def upload_to_external(self):
        """ TODO: 上传录像到外部存储 """
        config = self.get_storage_config()
        logger.debug(f'录像存储配置: ({config})')
        storage = jms_storage.get_object_storage(config)
        ok, error = storage.upload(src=self.gz_filepath, target=self.upload_target)
        if not ok:
            logger.error(f'上传录像失败: ({error})')
        return ok

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

    def delete_gz_file(self):
        logger.info(f'删除录像压缩文件({self.gz_filepath})')
        os.unlink(self.gz_filepath)

    def upload(self):
        logger.info('上传录像')
        if not os.path.isfile(self.gz_filepath):
            self.gzip()

        if os.path.getsize(self.gz_filepath) == 0:
            logger.error(f'录像压缩文件大小为0({self.gz_filepath})')
            self.delete_gz_file()
            return

        while True:
            ok = self._upload()
            if ok:
                logger.info(f'录像上传成功({self.gz_filepath})')
                self.delete_gz_file()
                return True
            else:
                logger.error(f'录像上传失败({self.gz_filepath})')
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

    def remove_replay(self, session_id):
        self._replays.pop(session_id, None)

    def get_replay(self, session_id):
        return self._replays.get(session_id)

    def start_replay(self, session_id):
        replay = Replay(session_id)
        replay.start()
        self.add_replay(replay)

    def record_replay(self, command):
        session_id = command['session']
        replay = self.get_replay(session_id)
        replay.record(command)

    def end_replay(self, session_id):
        replay = self.get_replay(session_id)
        if replay:
            replay.end()
            replay.upload()
        else:
            logger.error(f'未获取到录像({session_id})')

    def start_remain_replay_upload_thread(self):
        """ 开启遗留录像上传处理线程 """
        t = threading.Thread(target=self.start_remain_replay_upload)
        t.setDaemon(True)
        t.start()
        return t

    def start_remain_replay_upload(self):
        """ 开启遗留录像上传处理 """
        logger.info('开启遗留录像上传处理')

        replay_dir = settings.REPLAY_DIR

        if not os.path.isdir(replay_dir):
            return

        for replay_date in os.listdir(replay_dir):
            replay_date_dir = os.path.join(replay_dir, replay_date)
            for replay_file in os.listdir(replay_date_dir):
                try:
                    replay_filepath = os.path.join(replay_date_dir, replay_file)
                    logger.info(f'上传遗留录像({replay_filepath})')
                    session_id = replay_file[:36]
                    replay = Replay(session_id=session_id, replay_date=replay_date)
                    replay.upload()
                except Exception as exc:
                    logger.error(f'上传遗留录像出现异常({str(exc)})')

            if len(os.listdir(replay_date_dir)) == 0:
                logger.info(f'录像文件目录({replay_date_dir})中的录像已全部上传完成, 删除目录')
                os.rmdir(replay_date_dir)


replay_manager = ReplayManager()
