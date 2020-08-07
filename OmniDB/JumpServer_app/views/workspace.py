import random
import string
import datetime
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
import JumpServer_app.server as Core_Service
from ..utils import get_request_ip

def index(request):
    """Connect to OmniDB"""

    # 从request中获取数据: database_id、system_user_id、cookies['sessionid']、cookies['csrftoken']
    session_id = request.COOKIES.get('sessionid', '')
    csrf_token = request.COOKIES.get('csrftoken', '')
    database_id = request.GET.get('database_id', '')
    system_user_id = request.GET.get('system_user_id', '')

    # 校验JumpServer用户权限
    #: 校验登录状态
    print('校验用户登录状态: session_id: {}'.format(session_id))
    cookies = {'sessionid': session_id, 'csrftoken': csrf_token}
    url = '{}{}'.format(settings.CORE_URL, '/api/v1/users/profile/')
    res_js_user_profile = requests.get(url, cookies=cookies)
    if res_js_user_profile.status_code != 200:
        error = '用户未登录'
        print(error)
        return HttpResponse(error)
    print('校验用户登录状态通过')
    #: 获取用户信息
    js_user_profile = res_js_user_profile.json()
    js_user_id = js_user_profile['id']
    js_user_name = js_user_profile['name']
    js_user_username = js_user_profile['username']
    #: 校验数据库权限
    print('校验用户数据库权限: user_id: {}, database_id: {}, system_user_id: {}'.format(js_user_id, database_id, system_user_id))
    has_permission = Core_Service.core_server.check_user_database_permission(js_user_id, database_id, system_user_id)
    if not has_permission:
        error = '校验用户数据库权限失败'
        print(error)
        return HttpResponse(error)
    print('校验用户数据库权限通过')

    # 获取JumpServer相关信息
    #: 获取数据库信息
    print('获取数据库信息: database_id: {}'.format(database_id))
    js_database_info = Core_Service.core_server.get_database_info(database_id)
    if js_database_info is None:
        error = '获取数据库信息失败'
        print(error)
        return HttpResponse(error)
    print('获取数据库信息成功')
    js_database_id = js_database_info['id']
    js_database_name = js_database_info['name']
    js_database_type = js_database_info['type']
    js_database_host = js_database_info['host']
    js_database_port = js_database_info['port']
    js_database_database = js_database_info['database']
    js_database_org_id = js_database_info['org_id']

    #: 获取系统用户信息
    print('获取系统用户信息: system_user_id: {}'.format(system_user_id))
    js_system_user_info = Core_Service.core_server.get_system_user_info(system_user_id)
    if js_system_user_info is None:
        error = '获取系统用户信息失败'
        print(error)
        return HttpResponse(error)
    print('获取系统用户信息成功')

    js_system_user_id = js_system_user_info['id']
    js_system_user_username = js_system_user_info['username']
    js_system_user_protocol = js_system_user_info['protocol']
    js_system_user_login_mode = js_system_user_info['login_mode']

    #: 获取系统用户、数据库应用认证信息
    print('获取系统用户登录方式: {}'.format(js_system_user_login_mode))
    if js_system_user_login_mode == 'auto':
        print('获取系统用户认证信息: system_user_id: {}'.format(system_user_id))
        js_system_user_auth_info = Core_Service.core_server.get_system_user_auth_info(system_user_id)
        if js_system_user_auth_info is None:
            error = '获取系统用户认证信息失败'
            print(error)
            return HttpResponse(error)
        print('获取系统用户认证信息成功')
        js_system_user_auth_password = js_system_user_auth_info['password']
    else:
        js_system_user_auth_password = None

    # 获取omnidb数据库连接
    print('创建omnidb数据库连接')
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

    omnidb_user_username = 'js_{}'.format(js_user_username)
    omnidb_user_password = js_user_profile['id']
    v_users = v_omnidb_database.v_connection.Query('''
        select * from users where user_name='{0}'
    '''.format(omnidb_user_username))
    if len(v_users.Rows) == 0:
        print('创建OmniDB数据库用户: {}'.format(omnidb_user_username))
        v_omnidb_database.v_connection.Execute('''
            insert into users values (
            (select coalesce(max(user_id), 0) + 1 from users),'{0}','{1}',1,'14',1,0,'utf-8',';','11',1)
        '''.format(omnidb_user_username, v_cryptor.Hash(v_cryptor.Encrypt(omnidb_user_password))))
    else:
        v_user = v_users.Rows[0]
        print('OmniDB数据库用户已存在: user_id: {}, user_name: {}'.format(v_user['user_id'], v_user['user_name']))

    # 创建OmniDB connections连接
    v_users = v_omnidb_database.v_connection.Query('''
        select * from users where user_name='{0}'
    '''.format(omnidb_user_username))
    if len(v_users.Rows) == 0:
        error = '未获取到OmniDB数据库用户: {}'.format(omnidb_user_username)
        print(error)
        return HttpResponse(error)
    v_user = v_users.Rows[0]
    v_user_id = v_user['user_id']
    v_user_name = v_user['user_name']

    print('创建OmniDB connections (user_id: {}, user_name: {}) '.format(v_user_id, v_user_name))
    omnidb_connection_dbt_st_name = js_database_type
    omnidb_connection_conn_string = ''
    omnidb_connection_server = js_database_host
    omnidb_connection_port = str(js_database_port)
    omnidb_connection_database = js_database_database
    omnidb_connection_user = js_system_user_username
    omnidb_connection_user_password = js_system_user_auth_password
    # 不支持中文
    # omnidb_connection_alias = js_database_name
    omnidb_connection_alias = ''
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
    print('创建OmniDB connections 成功')

    # 设置OmniDB用户Session信息
    if not request.session.get('omnidb_session'):
        print('设置用户session信息: {}'.format(v_user_name))
        num_connections = sign_in_automatic(request, omnidb_user_username, omnidb_user_password)
        if num_connections == -1:
            return HttpResponse("Set OmniDB Session Error")
        # 清空创建Session时自动添加的用户相关的所有connections，下面手动添加，手动添加时可以直接附上数据库用户密码
        request.session['omnidb_session'].v_databases = {}
    else:
        print('用户session已存在: {}'.format(v_user_name))

    # 添加connection到用户Session中
    v_session = request.session['omnidb_session']
    conn_id = v_omnidb_database.v_connection.ExecuteScalar('''
        select coalesce(max(conn_id), 0) from connections
    ''')
    print('添加OmniDB connection (conn_id: {}) 到用户session'.format(conn_id))
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

    # 创建JumpServer Session会话
    print('创建session会话')
    js_session_data = {
        'user': '{} ({})'.format(js_user_name, js_user_username),
        'asset': js_database_name,
        'org_id': js_database_org_id,
        'login_from': 'WT',
        'system_user': js_system_user_username,
        'protocol': js_system_user_protocol,
        'remote_addr': get_request_ip(request),
        'is_finished': False,
        'date_start': datetime.datetime.now(),
        'date_end': None,
        'user_id': js_user_id,
        'asset_id': js_database_id,
        'system_user_id': js_system_user_id,
        'is_success': False
    }
    js_session_info = Core_Service.core_server.create_session(data=js_session_data)
    if js_session_info is None:
        error = '创建session会话失败'
        print(error)
        return HttpResponse(error)
    # 获取js_session信息
    js_session_id = js_session_info['id']
    print('创建session会话成功: {}'.format(js_session_id))

    # 保存jumpserver相关数据 对应 conn_id
    v_session.js_v_default_open_conn_id = conn_id
    v_session.js_v_connections[conn_id] = dict([])
    v_session.js_v_connections[conn_id]['js_user'] = js_user_profile
    v_session.js_v_connections[conn_id]['js_system_user'] = js_system_user_info
    v_session.js_v_connections[conn_id]['js_database'] = js_database_info
    v_session.js_v_connections[conn_id]['js_session'] = js_session_info


    # 重新设置omnidb_session值
    print('重置用户session omnidb_session值')
    request.session['omnidb_session'] = v_session

    print('重定向workspace页面')
    #: TODO 同一个浏览器打开两个Tab页面，每个Tab页面中创建多个Conn Tab，前端自动生成Conn Tab ID， 且每个浏览器Tab中的Conn Tab一致，后台存放到v_session.v_tab_connections中， 会互相替换（在最后一个打开Workspace时）, 暂时无法解决
    # 重定向workspace页面（如果直接渲染，页面会创建web socket，然后报session丢失错误，可能在浏览器设置session之前
    return redirect('workspace')

