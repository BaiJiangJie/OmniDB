from django.shortcuts import redirect
from django.http import HttpResponse
import logging
import requests
import datetime
from OmniDB import jumpserver_settings, settings
from OmniDB_app.views.login import sign_in_automatic
import OmniDB_app.include.OmniDatabase as OmniDatabase
import OmniDB_app.include.Spartacus.Utils as Utils
from . import service, utils

logger = logging.getLogger('JumpServer_app.views')


def workspace(request):
    """
    说明:
        JumpServer通过调用此API接口，使用OmniDB。
    URL调用:
        /omnidb/connect/workspace/?system_user_id={SystemUserID}&database_id={DatabaseID}
    功能:
        - 校验用户登录状态: Check JumpServer User Login status: Through session
        - 获取信息: JumpServer User
        - 校验权限: JumpServer User / Database / SystemUser
        - 获取信息: JumpServer Database
        - TODO: 获取信息: JumpServer Database Domain
        - 获取信息: JumpServer SystemUser
        - 获取信息: JumpServer SystemUserAuthInfo
        - 连接数据库: OmniDB Database
        - 创建用户: OmniDB User
        - 创建Connection: OmniDB Connection
        - 获取Connection: OmniDB Connection: 上面创建
        - 注册Session: OmniDB Request User Session
        - 添加Connection: OmniDB Connection append to OmniDB Request User Session
        - 创建会话: JumpServer Terminal Session
        - 保存信息: JumpServer Related Resource Info save to OmniDB Request User Session
        - 设置默认打开的conn_id: OmniDB Page default open conn_id
        - 设置Session: OmniDB Request User Session
        - TODO: 保存会话: 维护全局会话列表: 心跳使用
        - 重定向: Redirect to omnidb ('workspace') Page
    """
    logger.info('收到连接请求')
    logger.info('请求处理开始')

    #: 参数: Request
    logger.info('获取请求参数')
    js_session_id = request.COOKIES.get('sessionid')
    if js_session_id is None:
        message = '请求参数Cookie中缺少session_id字段'
        logger.error(message)
        return HttpResponse(message)
    js_csrf_token = request.COOKIES.get('csrftoken')
    if js_csrf_token is None:
        message = '请求参数Cookie中缺少csrftoken字段'
        logger.error(message)
        return HttpResponse(message)
    js_database_id = request.GET.get('database_id')
    if js_database_id is None:
        message = '请求参数GET中缺少database_id字段'
        logger.error(message)
        return HttpResponse(message)
    js_system_user_id = request.GET.get('system_user_id')
    if js_system_user_id is None:
        message = '请求参数GET中缺少system_user_id字段'
        logger.error(message)
        return HttpResponse(message)
    logger.info('获取请求参数: 完成')
    logger.debug(
        '获取到请求参数值: session_id: {}, csrf_token: {}, database_id: {}, system_user_id: {}'.format(
            js_session_id, js_csrf_token, js_database_id, js_system_user_id
        )
    )

    #: 用户: JumpServer
    logger.info('校验用户登录状态')
    logger.info('请求用户个人信息')
    js_cookies = {
        'sessionid': js_session_id, 'csrftoken': js_csrf_token
    }
    url = '{}{}'.format(jumpserver_settings.JUMPSERVER_HOST, service.urls.url_user_profile)
    logger.debug('请求用户个人信息: 使用参数: url: {}, cookies: {}'.format(url, js_cookies))
    try:
        js_user_resp = requests.get(url, cookies=js_cookies)
    except Exception as exc:
        message = '请求用户个人信息异常: {}; 请求处理结束, 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        if js_user_resp.status_code != 200:
            message = '请求用户个人信息: 失败: 用户未登录; 请求处理结束, 拒绝连接'
            logger.info(message)
            logger.debug(
                '请求返回响应信息: status_code: {}, text: {}'
                ''.format(js_user_resp.status_code, js_user_resp.text)
            )
            return HttpResponse(message)
        else:
            logger.info('请求用户个人信息: 完成')

    logger.info('获取用户个人信息')
    try:
        js_user_json = js_user_resp.json()
        js_user_id = js_user_json['id']
        js_user_name = js_user_json['name']
        js_user_username = js_user_json['username']
    except Exception as exc:
        message = '获取用户个人信息: 异常: {}; 请求处理结束, 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        logger.info('获取用户个人信息: 完成')

    logger.info('校验用户连接数据库权限')
    ok = service.client.jumpserver_client.validate_user_database_permission(
        user_id=js_user_id, database_id=js_database_id, system_user_id=js_system_user_id
    )
    if not ok:
        message = '校验用户连接数据库权限: 未通过; 请求处理结束, 拒绝连接'
        logger.info(message)
        return HttpResponse(message)
    else:
        logger.info('校验用户连接数据库权限: 通过')

    #: 数据库: JumpServer
    logger.info('请求数据库信息')
    js_database_json = service.client.jumpserver_client.get_database(database_id=js_database_id)
    if js_database_json is None:
        message = '请求数据库信息: 失败; 请求处理结束, 拒绝连接'
        logger.info(message)
        return HttpResponse(message)
    else:
        logger.info('请求数据库信息: 成功')

    logger.info('获取数据库信息')
    try:
        js_database_id = js_database_json['id']
        js_database_name = js_database_json['name']
        js_database_type = js_database_json['type']
        js_database_host = js_database_json['host']
        js_database_port = js_database_json['port']
        js_database_database = js_database_json['database']
        js_database_org_id = js_database_json['org_id']
    except Exception as exc:
        message = '获取数据库信息: 异常: {}; 请求处理结束, 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        logger.info('获取数据信息: 完成')

    #: TODO: 数据库: 网域

    #: 系统用户: JumpServer
    logger.info('请求系统用户信息')
    js_system_user_json = service.client.jumpserver_client.get_system_user(system_user_id=js_system_user_id)
    if js_system_user_json is None:
        message = '请求系统用户信息: 失败; 请求处理结束, 拒绝连接'
        logger.info(message)
        return HttpResponse(message)
    else:
        logger.info('请求系统用户信息: 成功')

    logger.info('获取系统用户信息')
    try:
        js_system_user_id = js_system_user_json['id']
        js_system_user_username = js_system_user_json['username']
        js_system_user_protocol = js_system_user_json['protocol']
        js_system_user_login_mode = js_system_user_json['login_mode']
    except Exception as exc:
        message = '获取系统用户信息: 异常: {}; 请求处理结束, 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        logger.info('获取系统用户信息: 完成')

    #: 系统用户: 认证信息: JumpServer
    logger.info('系统用户登录方式: {}'.format(js_system_user_login_mode))
    if js_system_user_login_mode == 'auto':
        logger.info('请求系统用户认证信息')
        js_system_user_auth_info_json = service.client.jumpserver_client.get_system_user_auth_info(system_user_id=js_system_user_id)
        if js_system_user_auth_info_json is None:
            message = '请求系统用户认证信息: 失败; 请求处理结束, 拒绝连接'
            logger.info(message)
            return HttpResponse(message)
        else:
            logger.info('请求系统用户认证信息: 成功')

        logger.info('获取系统用户认证信息')
        try:
            js_system_user_auth_info_password = js_system_user_auth_info_json['password']
        except Exception as exc:
            message = '获取系统用户认证信息: 异常: {}; 请求处理结束, 拒绝连接'.format(str(exc))
            logger.error(message, exc_info=True)
            return HttpResponse(message)
        else:
            logger.info('获取系统用户认证信息: 完成')
    else:
        js_system_user_auth_info_password = None

    #: 连接数据库: OmniDB
    logger.info('建立OmniDB数据库连接')
    v_omnidb_database = OmniDatabase.Generic.InstantiateDatabase(
        'sqlite',
        '',
        '',
        settings.OMNIDB_DATABASE,
        '',
        '',
        '0',
        '',
        True
    )

    #: 创建用户: OmniDB
    #: :查询用户
    logger.info('查询OmniDB用户')
    omnidb_user_username = 'js_{}'.format(js_user_username)
    omnidb_user_password = js_user_id
    v_cryptor = Utils.Cryptor('omnidb', 'iso-8859-1')
    try:
        v_users = v_omnidb_database.v_connection.Query('''
            select * from users where user_name='{}'
        '''.format(omnidb_user_username))
    except Exception as exc:
        message = '查询OmniDB用户: 异常: {}; 请求处理结束, 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        if len(v_users.Rows) == 0:
            #: :创建用户
            logger.info('查询到OmniDB用户: 用户名: {}; 不存在'.format(omnidb_user_username))
            logger.info('创建OmniDB用户: 用户名: {}'.format(omnidb_user_username))
            try:
                v_omnidb_database.v_connection.Execute('''
                    insert into users values (
                    (select coalesce(max(user_id), 0) + 1 from users),
                    '{0}','{1}',1,'14',1,0,'utf-8',';','11',1
                    )
                '''.format(omnidb_user_username, v_cryptor.Hash(v_cryptor.Encrypt(omnidb_user_password))))
            except Exception as exc:
                message = '创建OmniDB用户: 用户名: {}; 异常: {}; 请求处理结束, 拒绝连接'.format(omnidb_user_username, str(exc))
                logger.error(message)
                return HttpResponse(message)
            else:
                logger.info('创建OmniDB用户: 用户名: {}; 完成'.format(omnidb_user_username))
        else:
            logger.info('查询到OmniDB用户: 用户名: {}; 已存在;'.format(omnidb_user_username))

    #: :获取用户
    logger.info('获取OmniDB用户: 用户名: {}'.format(omnidb_user_username))
    try:
        v_users = v_omnidb_database.v_connection.Query('''
            select * from users where user_name='{0}'
        '''.format(omnidb_user_username))
    except Exception as exc:
        message = '获取OmniDB用户: 用户名: {}; 异常: {}; 请求处理结束, 拒绝连接'.format(omnidb_user_username, str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        if len(v_users.Rows) == 0:
            message = '获取OmniDB用户: 用户名: {}: 失败: 未获取到; 请求处理结束, 拒绝连接'.format(omnidb_user_username)
            logger.info(message)
            return HttpResponse(message)
        else:
            logger.info('获取OmniDB用户: 用户名: {}; 成功'.format(omnidb_user_username))
            v_user = v_users.Rows[0]

    #: :获取用户: 信息
    logger.info('获取OmniDB用户信息')
    try:
        v_user_id = v_user['user_id']
        v_user_name = v_user['user_name']
    except Exception as exc:
        message = '获取OmniDB用户信息: 异常: {}; 请求处理结束, 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        logger.info('获取OmniDB用户信息: 完成')

    #: 创建Connection: OmniDB
    logger.info('创建OmniDB Connection')
    omnidb_connection_db_type = utils.convert_to_omnidb_db_type(js_database_type)
    if omnidb_connection_db_type is None:
        message = '创建OmniDB Connection: 失败: 不支持的数据库类型: {}; 请求处理结束, 拒绝连接'.format(js_database_type)
        logger.info(message)
        return HttpResponse(message)
    omnidb_connection_dbt_st_name = omnidb_connection_db_type
    omnidb_connection_conn_string = ''
    omnidb_connection_server = js_database_host
    omnidb_connection_port = str(js_database_port)
    omnidb_connection_database = js_database_database
    omnidb_connection_user = js_system_user_username
    omnidb_connection_user_password = js_system_user_auth_info_password
    # 不支持中文
    # omnidb_connection_alias = js_database_name
    omnidb_connection_alias = ''
    #: TODO: 网域
    omnidb_connection_ssh_server = ''
    omnidb_connection_ssh_port = '22'
    omnidb_connection_ssh_user = ''
    omnidb_connection_ssh_password = ''
    omnidb_connection_ssh_key = ''
    omnidb_connection_use_tunnel = 0

    try:
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
    except Exception as exc:
        message = '创建OmniDB Connection: 异常: {}; 请求处理结束; 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        logger.info('创建OmniDB Connection: 完成')

    #: 获取Connection: 上面创建: OmniDB
    logger.info('获取OmniDB Connection')
    try:
        conn_id = v_omnidb_database.v_connection.ExecuteScalar('''
            select coalesce(max(conn_id), 0) from connections where user_id = {0}
        '''.format(v_user_id))
    except Exception as exc:
        message = '获取OmniDB Connection: 异常: {}; 请求处理结束; 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        logger.info('获取OmniDB Connection: conn_id: {}; 完成'.format(conn_id))

    #: 注册Session: OmniDB
    logger.info('检测OmniDB用户Session状态')
    v_session = request.session.get('omnidb_session')
    if v_session is None:
        logger.info('检测到OmniDB用户Session状态: 不存在')
        logger.info('注册OmniDB用户Session')
        connections_count = sign_in_automatic(request=request, username=omnidb_user_username, pwd=omnidb_user_password)
        if connections_count == -1:
            message = '注册OmniDB用户Session: 失败; 请求处理结束; 拒绝连接'
            logger.info(message)
            return HttpResponse(message)
        else:
            logger.info('注册OmniDB用户Session: 完成')
    else:
        logger.info('检测到OmniDB用户Session状态: 已存在')

    #: 添加Connection: OmniDB
    #: :获取用户Session
    logger.info('获取OmniDB用户Session')
    try:
        v_session = request.session['omnidb_session']
    except Exception as exc:
        message = '获取OmniDB用户Session: 异常: {}; 请求处理结束; 拒绝连接'.format(str(exc))
        logger.error(message, exc_info=True)
        return HttpResponse(message)
    else:
        logger.info('获取OmniDB用户Session: 完成')

    #: :创建Connection Database
    logger.info('创建OmniDB Connection Database')
    logger.debug(
        '创建OmniDB Connection Database: 使用信息: '
        'db_type: {}, server: {}, port: {}, database: {}, user: {}, conn_id: {}, alias: {}'.format(
            omnidb_connection_dbt_st_name,
            omnidb_connection_server,
            omnidb_connection_port,
            omnidb_connection_database,
            omnidb_connection_user,
            conn_id,
            omnidb_connection_alias
        )
    )
    #: TODO: 数据库密码: 初始赋值: 研究
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
    logger.info('创建OmniDB Connection Database: 完成')

    #: :添加Connection Database
    logger.info('添加OmniDB Connection Database到OmniDB用户Session')
    tunnel_information = {
        'enabled': omnidb_connection_use_tunnel,
        'server': omnidb_connection_ssh_server,
        'port': omnidb_connection_ssh_port,
        'user': omnidb_connection_ssh_user,
        'password': omnidb_connection_ssh_password,
        'key': omnidb_connection_ssh_key
    }
    #: TODO: 数据库密码: 密码有效时限: prompt_password: 研究
    v_session.AddDatabase(
        conn_id, omnidb_connection_dbt_st_name, database, False,
        tunnel_information, omnidb_connection_alias
    )
    logger.info('添加OmniDB Connection Database到OmniDB用户Session: 完成')
    logger.info('当前OmniDB用户Session中存在的Connection Database个数为: {}'.format(len(v_session.v_databases)))

    #: 创建会话: JumpServer
    logger.info('请求创建JumpServer会话')
    js_terminal_session_data = {
        'user': '{} ({})'.format(js_user_name, js_user_username),
        'user_id': js_user_id,
        'asset': js_database_name,
        'asset_id': js_database_id,
        'system_user': js_system_user_username,
        'system_user_id': js_system_user_id,
        'protocol': js_system_user_protocol,
        'login_from': 'WT',
        'remote_addr': utils.get_request_ip(request),
        'is_success': False,
        'is_finished': False,
        'org_id': js_database_org_id,
        'date_start': datetime.datetime.now(),
        'date_end': None,
    }
    logger.debug('请求创建JumpServer会话: 使用信息: {}'.format(js_terminal_session_data))
    js_terminal_session_json = service.client.jumpserver_client.create_session(js_terminal_session_data)
    if js_terminal_session_json is None:
        message = '请求创建JumpServer会话: 失败; 请求处理结束, 拒绝连接'
        logger.info(message)
        return HttpResponse(message)
    else:
        logger.info('请求创建JumpServer会话: 成功')

    #: 保存信息: JumpServer相关信息到OmniDB用户Session中
    logger.info('保存JumpServer相关信息到OmniDB用户Session')
    js_v_connection = {
        'js_user': js_user_json,
        'js_system_user': js_system_user_json,
        'js_database': js_database_json,
        'js_session': js_terminal_session_json
    }
    logger.debug('保存的JumpServer相关信息为: {}'.format(js_v_connection))
    v_session.js_v_connections[conn_id] = js_v_connection

    #: 设置默认打开的conn_id
    #: TODO: 默认打开的conn_id: workspace: 页面: 修改
    logger.info('设置OmniDB默认打开conn_id: {}'.format(conn_id))
    v_session.js_v_default_open_conn_id = conn_id

    #: 设置用户Session: OmniDB
    logger.info('设置OmniDB用户Session: omnidb_session')
    request.session['omnidb_session'] = v_session

    #: TODO: 保存会话
    logger.info('请求处理完成')
    logger.info('重定向到workspace页面')
    response = redirect('workspace')
    return response
