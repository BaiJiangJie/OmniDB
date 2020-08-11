import os
import socket
import logging
import requests
from django.conf import settings

from OmniDB import jumpserver_settings
from . import service

logger = logging.getLogger('JumpServer_app.startup')


def register_terminal():
    logger.info('开始注册终端')

    logger.info('检测Access Key文件是否存在')
    key_file = settings.JUMPSERVER_KEY_FILE
    if os.path.exists(key_file):
        logger.info('Access Key文件已存在, 检测终端用户有效性')
        ok = service.client.jumpserver_client.check_terminal_validity()
        if not ok:
            logger.info('检测到终端用户已失效: 尝试删除Access Key文件并重新启动服务, 文件路径: {}'.format(key_file))
            return False
        else:
            logger.info('检测到终端用户有效, 跳过终端注册')
            return True

    logger.info('Access Key文件不存在, 执行终端注册')
    url = '{}{}'.format(jumpserver_settings.JUMPSERVER_HOST, service.urls.url_terminal_registration)
    data = {
        'name': '[OmniDB] {}'.format(socket.gethostname())
    }
    headers = {
        'Authorization': 'BootstrapToken {}'.format(jumpserver_settings.JUMPSERVER_BOOTSTRAP_TOKEN),
        'X-JMS-ORG': 'ROOT'
    }
    try:
        resp = requests.post(url, data=data, headers=headers)
    except Exception as exc:
        logger.error('注册终端请求异常: {}'.format(exc), exc_info=True)
        logger.debug('注册终端使用数据: url: {}, data: {}, headers: {}'.format(url, data, headers))
        return False
    if resp.status_code != 201:
        logger.error('注册终端失败: status_code: {} text: {}'.format(resp.status_code, resp.text))
        return False
    logger.info('注册终端请求完成, status_code: {}'.format(resp.status_code))

    try:
        logger.info('获取终端Access Key信息')
        resp_json_data = resp.json()
        access_key_id = resp_json_data['service_account']['access_key']['id']
        access_key_secret = resp_json_data['service_account']['access_key']['secret']
    except Exception as exc:
        logger.error('获取终端Access Key信息失败: {}'.format(str(exc)))
        logger.error('注册终端失败: {}'.format(resp.text))
        return False
    else:
        logger.info('将Access Key写入文件')
        key_filename = settings.JUMPSERVER_KEY_FILE
        key_dir = os.path.dirname(key_filename)
        if not os.path.isdir(key_dir):
            logger.info('创建Access Key文件目录')
            os.makedirs(key_dir, exist_ok=True)
        with open(key_filename, 'w') as f:
            message = "{}:{}".format(access_key_id, access_key_secret)
            f.write(message)
            logger.info('Access Key写入文件成功')

        logger.info('检测终端用户有效性')
        ok = service.client.jumpserver_client.check_terminal_validity()
        if not ok:
            logger.info('检测到终端用户已失效: 尝试删除Access Key文件并重新启动服务, 文件路径: {}'.format(key_file))
            logger.error('注册终端失败: {}'.format(resp.text))
            return False
        else:
            logger.info('检测到终端用户有效')
            logger.info('注册终端完成')
            return True

