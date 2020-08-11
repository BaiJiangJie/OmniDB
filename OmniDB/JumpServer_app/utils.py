
def convert_to_omnidb_db_type(db_type):
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
