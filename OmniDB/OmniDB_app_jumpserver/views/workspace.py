import random
import string
import requests
from django.http import HttpResponse
from django.shortcuts import redirect
from django.template import loader
from OmniDB import settings
from django.conf import settings
from OmniDB_app.include.Spartacus import Utils

from OmniDB_app.include import OmniDatabase
from OmniDB_app.views.login import sign_in_automatic
from ..server import core_server


def index(request):
    """Connect to OmniDB"""

    # 从request中获取数据: database_id、system_user_id、cookies['sessionid']、cookies['csrftoken']
    session_id = request.COOKIES.get('sessionid', '')
    csrf_token = request.COOKIES.get('csrftoken', '')
    database_id = request.GET.get('database_id', '')
    system_user_id = request.GET.get('system_user_id', '')

    # 校验JumpServer用户权限
    #: 校验登录状态
    cookies = {'sessionid': session_id, 'csrftoken': csrf_token}
    url = '{}{}'.format(settings.CORE_URL, '/api/v1/users/profile/')
    res_profile = requests.get(url, cookies=cookies)
    if res_profile.status_code != 200:
        return HttpResponse('JumpServer check user failure')
    #: 校验数据库权限
    profile = res_profile.json()
    user_id = profile['id']
    has_permission = core_server.check_user_database_permission(user_id, database_id, system_user_id)
    if not has_permission:
        return HttpResponse('JumpServer check user database permission failure')

    # 获取JumpServer相关信息
    #: 获取用户信息
    #: 获取数据库信息
    database_info = core_server.get_database_info(database_id)
    if database_info is None:
        return HttpResponse('JumpServer get database info failure')
    #: 获取系统用户信息
    system_user_info = core_server.get_system_user_info(system_user_id)
    if system_user_info is None:
        return HttpResponse('JumpServer get system user info failure')
    #: 获取系统用户、数据库应用认证信息
    system_user_auth_info = core_server.get_system_user_auth_info(system_user_id)
    if system_user_auth_info is None:
        return HttpResponse('JumpServer get system user auth info failure')

    # 获取omnidb数据库连接
    v_omnidb_database = OmniDatabase.Generic.InstantiateDatabase(
        'sqlite',
        '',
        '',
        settings.OMNIDB_DATABASE,
        '',
        '',
        '0',
        ''
    )

    # 创建OmniDB用户
    v_cryptor = Utils.Cryptor('omnidb', 'iso-8859-1')

    username = profile['username']
    omnidb_user_username = 'js_{}'.format(username)
    omnidb_user_password = profile['id']
    v_user = v_omnidb_database.v_connection.ExecuteScalar('''
        select * from users where user_name='{0}'
    '''.format(omnidb_user_username))

    if v_user is None:
        v_omnidb_database.v_connection.Execute('''
            insert into users values (
            (select coalesce(max(user_id), 0) + 1 from users),'{0}','{1}',1,'14',1,0,'utf-8',';','11',1)
        '''.format(omnidb_user_username, v_cryptor.Hash(v_cryptor.Encrypt(omnidb_user_password))))


    # 创建OmniDB connections连接
    v_users = v_omnidb_database.v_connection.Query('''
        select * from users where user_name='{0}'
    '''.format(omnidb_user_username))
    if len(v_users.Rows) == 0:
        return HttpResponse('OmniDB create user failure')
    v_user = v_users.Rows[0]
    v_user_id = v_user['user_id']

    omnidb_connection_dbt_st_name = database_info['type']
    # omnidb_connection_conn_string = database_info['name']
    omnidb_connection_conn_string = ''
    omnidb_connection_server = database_info['host']
    omnidb_connection_port = str(database_info['port'])
    omnidb_connection_database = database_info['database']
    omnidb_connection_user = system_user_info['username']
    omnidb_connection_user_password = system_user_auth_info['password']
    omnidb_connection_alias = database_info['name']
    omnidb_connection_ssh_server = ''
    omnidb_connection_ssh_port = '22'
    omnidb_connection_ssh_user = ''
    omnidb_connection_ssh_password = ''
    omnidb_connection_ssh_key = ''
    omnidb_connection_use_tunnel = 0

    v_omnidb_database.v_connection.Execute('''
        insert into connections values (
        (select coalesce(max(conn_id), 0) + 1 from connections),
        '{0}',
        '{1}',
        '{2}',
        '{3}',
        '{4}',
        '{5}',
        '{6}',
        '{7}',
        '{8}',
        '{9}',
        '{10}',
        '{11}',
        '{12}',
        '{13}')
    '''.format(
        v_user_id,
        omnidb_connection_dbt_st_name,
        v_cryptor.Encrypt(omnidb_connection_server),
        v_cryptor.Encrypt(omnidb_connection_port),
        v_cryptor.Encrypt(omnidb_connection_database),
        v_cryptor.Encrypt(omnidb_connection_user),
        v_cryptor.Encrypt(omnidb_connection_alias),
        v_cryptor.Encrypt(omnidb_connection_ssh_server),
        v_cryptor.Encrypt(omnidb_connection_ssh_port),
        v_cryptor.Encrypt(omnidb_connection_ssh_user),
        v_cryptor.Encrypt(omnidb_connection_ssh_password),
        v_cryptor.Encrypt(omnidb_connection_ssh_key),
        omnidb_connection_use_tunnel,
        v_cryptor.Encrypt(omnidb_connection_conn_string),
    ))

    # 设置OmniDB用户Session信息
    if not request.session.get('omnidb_session'):
        num_connections = sign_in_automatic(request, omnidb_user_username, omnidb_user_password)
        if num_connections == -1:
            return HttpResponse("Set OmniDB Session Error")
        # 清空创建Session时，自动添加的用户相关的所有connections，下面手动添加，手动添加时，直接附上数据库用户密码
        request.session['omnidb_session'].v_databases = {}

    # 添加connection到用户Session中
    v_session = request.session['omnidb_session']
    conn_id = v_omnidb_database.v_connection.ExecuteScalar('''
        select coalesce(max(conn_id), 0) from connections
    ''')
    database = OmniDatabase.Generic.InstantiateDatabase(
        omnidb_connection_dbt_st_name,
        omnidb_connection_server,
        omnidb_connection_port,
        omnidb_connection_database,
        omnidb_connection_user,
        omnidb_connection_user_password,
        conn_id,
        omnidb_connection_alias,
        p_conn_string=omnidb_connection_conn_string,
        p_parse_conn_string=True
    )
    tunnel_information = {
        'enabled': omnidb_connection_use_tunnel,
        'server': omnidb_connection_ssh_server,
        'port': omnidb_connection_ssh_port,
        'user': omnidb_connection_ssh_user,
        'password': omnidb_connection_ssh_password,
        'key': omnidb_connection_ssh_key
    }
    v_session.AddDatabase(
        conn_id, omnidb_connection_dbt_st_name, database, False,
        tunnel_information, omnidb_connection_alias
    )
    request.session['omnidb_session'] = v_session
    request.session['conn_id_default_open'] = conn_id

    # 创建JumpServer Session会话

    # 重定向workspace页面（如果直接渲染，页面会创建web socket，然后报session丢失错误，可能在浏览器设置session之前
    return redirect('workspace')

