import os
from django.conf import settings


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


def read_access_key_from_file():
    key_file = settings.JUMPSERVER_KEY_FILE
    if os.path.exists(key_file):
        with open(key_file, 'r') as f:
            access_key = f.read()
    else:
        access_key = None

    return access_key

