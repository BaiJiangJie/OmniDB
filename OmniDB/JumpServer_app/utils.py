import os
import gzip
from django.conf import settings
import logging

logger = logging.getLogger('JumpServer_app.utils')


def convert_db_type(db_type):
    if not isinstance(db_type, str):
        return None
    db_type = db_type.lower()
    if db_type not in ['postgresql', 'oracle', 'mariadb', 'mysql', 'sqlite']:
        return None
    omnidb_db_type = db_type
    return omnidb_db_type


def get_request_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')
    if x_forwarded_for and x_forwarded_for[0]:
        login_ip = x_forwarded_for[0]
    else:
        login_ip = request.META.get('REMOTE_ADDR', '')
    return login_ip


def gzip_file(src_path, dst_path, unlink_ori=True):
    with open(src_path, 'rt') as src, gzip.open(dst_path, 'at') as dst:
        dst.writelines(src)
    if unlink_ori:
        os.unlink(src_path)
