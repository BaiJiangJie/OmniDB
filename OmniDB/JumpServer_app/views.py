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
from .manager.session import session_manager
from .manager.omnidb import omnidb_manager

logger = logging.getLogger('JumpServer_app.views')


def workspace(request):
    """
    说明: JumpServer通过调用此API接口，使用OmniDB。
    URL调用: /omnidb/connect/workspace/?system_user_id={SystemUserID}&database_id={DatabaseID}
    """
    logger.info('收到连接请求')
    session_id = request.COOKIES.get('sessionid')
    csrf_token = request.COOKIES.get('csrftoken')
    database_id = request.GET.get('database_id')
    system_user_id = request.GET.get('system_user_id')
    if not all([session_id, csrf_token, database_id, system_user_id]):
        if not session_id or not csrf_token:
            error = '用户未登录(请求中缺少sessionid或csrftoken字段)'
            logger.error(error)
            return HttpResponse(error)
        if not database_id or not system_user_id:
            error = 'URL查询参数中缺少database_id或system_user_id字段'
            logger.error(error)
            return HttpResponse(error)

    try:
        logger.info('获取用户信息')
        cookies = {'sessionid': session_id, 'csrftoken': csrf_token}
        resp_profile = service.client.jumpserver_client.get_user_profile_by_cookies(cookies=cookies)
        if resp_profile.status_code == 200:
            js_user = resp_profile.json()
            js_user_id = js_user['id']
            js_user_name = js_user['name']
            js_user_username = js_user['username']
        else:
            error = f'获取用户信息失败, ' \
                    f'响应状态码: {resp_profile.status_code}, ' \
                    f'text: {resp_profile.text}, ' \
                    f'连接失败'
            logger.error(error)
            return HttpResponse(error)
    except Exception as exc:
        error = f'获取用户信息异常: {str(exc)}, 连接失败'
        logger.error(error)
        return HttpResponse(error)

    try:
        logger.info('校验用户数据库权限')
        resp_permission = service.client.jumpserver_client.validate_user_database_permission(
            user_id=js_user_id, database_id=database_id, system_user_id=system_user_id
        )
        if resp_permission.status_code == 200:
            pass
        elif resp_permission.status_code == 403:
            error = '校验用户数据库权限未通过, 无权限, 连接失败'
            logger.error(error)
            return HttpResponse(error)
        elif resp_permission.status_code == 404:
            error = f'校验用户数据库权限失败, 资源未找到: {resp_permission.text}, 连接失败'
            logger.error(error)
            return HttpResponse(error)
        else:
            error = f'校验用户数据库权限失败, ' \
                    f'响应状态码: {resp_permission.status_code}, ' \
                    f'text: {resp_permission.text}, ' \
                    f'连接失败'
            logger.error(error)
            return HttpResponse(error)
    except Exception as exc:
        error = f'校验用户数据库权限异常: {str(exc)}, 连接失败'
        logger.error(error)
        return HttpResponse(error)

    #: 数据库: JumpServer
    try:
        logger.info('获取数据库信息')
        resp_database = service.client.jumpserver_client.get_database(database_id=database_id)
        if resp_database.status_code == 200:
            js_database = resp_database.json()
            js_database_id = js_database['id']
            js_database_name = js_database['name']
            js_database_type = js_database['type']
            js_database_host = js_database['host']
            js_database_port = js_database['port']
            js_database_database = js_database['database']
            js_database_org_id = js_database['org_id']
        else:
            error = f'获取数据库信息失败, ' \
                    f'响应状态码: {resp_database.status_code}, ' \
                    f'text: {resp_database.text}, ' \
                    f'连接失败'
            logger.error(error)
            return HttpResponse(error)
    except Exception as exc:
        error = f'获取数据库信息异常: {str(exc)}, 连接失败'
        logger.error(error)
        return HttpResponse(error)

    try:
        logger.info('获取系统用户信息')
        resp_system_user = service.client.jumpserver_client.get_system_user(system_user_id)
        if resp_system_user.status_code == 200:
            js_system_user = resp_system_user.json()
            js_system_user_id = js_system_user['id']
            js_system_user_username = js_system_user['username']
            js_system_user_protocol = js_system_user['protocol']
            js_system_user_login_mode = js_system_user['login_mode']
            if js_system_user_login_mode == 'auto':
                logger.info(f'系统用户登录模式为: {js_system_user_login_mode}, 获取系统用户认证信息')
                resp_system_user_auth_info = service.client.jumpserver_client.get_system_user_auth_info(js_system_user_id)
                if resp_system_user_auth_info.status_code == 200:
                    resp_system_user_auth_info_json = resp_system_user_auth_info.json()
                    js_system_user_auth_info_password = resp_system_user_auth_info_json['password']
                else:
                    error = f'获取系统用户认证信息失败, ' \
                            f'响应状态码: {resp_system_user_auth_info.status_code}, ' \
                            f'text: {resp_system_user_auth_info.text}, ' \
                            f'连接失败'
                    logger.error(error)
                    return HttpResponse(error)
            else:
                js_system_user_auth_info_password = None
        else:
            error = f'获取系统用户信息失败, ' \
                    f'响应状态码: {resp_system_user.status_code}, ' \
                    f'text: {resp_system_user.text}, ' \
                    f'连接失败'
            logger.error(error)
            return HttpResponse(error)
    except Exception as exc:
        error = f'获取系统用户信息异常: {str(exc)}, 连接失败'
        logger.error(error)
        return HttpResponse(error)

    # TODO: 操作过程中，如果出现异常，则删除OmniDB中对应数据
    try:
        v_cryptor = Utils.Cryptor('omnidb', 'iso-8859-1')
        omnidb_user_username = 'js_{}'.format(js_user_username)
        omnidb_user_password = js_user_id
        logger.info(f'获取OmniDB用户信息({omnidb_user_username})')
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
        logger.info(f'查询OmniDB用户({omnidb_user_username})')
        v_users = v_omnidb_database.v_connection.Query('''
            select * from users where user_name='{}'
        '''.format(omnidb_user_username))
        if len(v_users.Rows) == 0:
            logger.info(f'创建OmniDB用户({omnidb_user_username})')
            v_omnidb_database.v_connection.Execute('''
                insert into users values (
                (select coalesce(max(user_id), 0) + 1 from users),
                '{0}','{1}',17,'14',1,0,'utf-8',';','11',1
                )
            '''.format(omnidb_user_username, v_cryptor.Hash(v_cryptor.Encrypt(omnidb_user_password))))
        logger.info(f'获取OmniDB用户({omnidb_user_username})')
        v_users = v_omnidb_database.v_connection.Query('''
            select * from users where user_name='{0}'
        '''.format(omnidb_user_username))
        if len(v_users.Rows) == 0:
            error = f'未获取到OmniDB用户({omnidb_user_username}), 连接失败'
            logger.error(error, exc_info=True)
            return HttpResponse(error)
        v_user = v_users.Rows[0]
        v_user_id = v_user['user_id']
    except Exception as exc:
        error = f'获取OmniDB用户信息异常({exc}), 连接失败'
        logger.error(error, exc_info=True)
        return HttpResponse(error)

    conn_id = None
    try:
        logger.info('将OmniDB-Connection-Database添加到OmniDB-User-Session')
        db_type = utils.convert_db_type(js_database_type)
        if db_type is None:
            error = '不支持数据库类型({}), 连接失败'.format(js_database_type)
            logger.error(error, exc_info=True)
            omnidb_manager.database_manager.delete_user(v_user_id)
            return HttpResponse(error)
        omnidb_connection_dbt_st_name = db_type
        omnidb_connection_conn_string = ''
        omnidb_connection_server = js_database_host
        omnidb_connection_port = str(js_database_port)
        omnidb_connection_database = js_database_database
        omnidb_connection_user = js_system_user_username
        omnidb_connection_user_password = js_system_user_auth_info_password
        # omnidb_connection_alias = js_database_name ## 不支持中文
        omnidb_connection_alias = ''
        omnidb_connection_ssh_server = ''
        omnidb_connection_ssh_port = '22'
        omnidb_connection_ssh_user = ''
        omnidb_connection_ssh_password = ''
        omnidb_connection_ssh_key = ''
        omnidb_connection_use_tunnel = 0
        logger.info('创建OmniDB-Connection')
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
        logger.info('获取OmniDB-Connection')
        conn_id = v_omnidb_database.v_connection.ExecuteScalar('''
            select coalesce(max(conn_id), 0) from connections where user_id = {0}
        '''.format(v_user_id))
        logger.info('创建OmniDB-Connection-Database')
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
        logger.info(f'获取OmniDB-User-Session({omnidb_user_username})')
        v_session = request.session.get('omnidb_session')
        if v_session is None:
            logger.info(f'注册OmniDB-User-Session({omnidb_user_username})')
            connections_count = sign_in_automatic(
                request=request, username=omnidb_user_username, pwd=omnidb_user_password
            )
            v_session = request.session.get('omnidb_session')
            if connections_count == -1 or v_session is None:
                error = f'注册OmniDB-User-Session({omnidb_user_username})失败, 连接失败'
                logger.error(error, exc_info=True)
                # delete
                omnidb_manager.database_manager.delete_user(v_user_id)
                omnidb_manager.database_manager.delete_connection(conn_id)
                return HttpResponse(error)
        logger.info(f'添加OmniDB-Connection-Database到OmniDB-User-Session({omnidb_user_username})')
        v_session.AddDatabase(
            conn_id, omnidb_connection_dbt_st_name, database, True,
            tunnel_information, omnidb_connection_alias
        )
        v_session.v_databases[conn_id]['prompt_timeout'] = datetime.datetime.now()
    except Exception as exc:
        error = f'添加OmniDB-Connection-Database到OmniDB-User-Session时出现异常({str(exc)}), 连接失败'
        logger.error(error, exc_info=True)
        # delete
        omnidb_manager.database_manager.delete_user(v_user_id)
        omnidb_manager.database_manager.delete_connection(conn_id)
        return HttpResponse(error)

    try:
        logger.info('创建JumpServer会话')
        data = {
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
        resp_session = session_manager.create_session(data)
        if resp_session.status_code == 201:
            js_session = resp_session.json()
        else:
            error = f'创建JumpServer会话失败, ' \
                    f'响应状态码: {resp_session.status_code}, ' \
                    f'text: {resp_session.text}, ' \
                    f'连接失败'
            logger.error(error)
            # delete
            omnidb_manager.database_manager.delete_user(v_user_id)
            omnidb_manager.database_manager.delete_connection(conn_id)
            return HttpResponse(error)
    except Exception as exc:
        error = f'创建JumpServer会话异常({str(exc)})'
        logger.error(error)
        # delete
        omnidb_manager.database_manager.delete_user(v_user_id)
        omnidb_manager.database_manager.delete_connection(conn_id)
        return HttpResponse(error)

    logger.info('保存JumpServer信息到OmniDB用户Session')
    js_v_connection = {
        'js_user': js_user,
        'js_system_user': js_system_user,
        'js_database': js_database,
        'js_session': js_session
    }
    v_session.js_v_connections[conn_id] = js_v_connection

    logger.info(f'设置默认打开的conn_id({conn_id})')
    v_session.js_v_default_open_conn_id = conn_id

    request.session['omnidb_session'] = v_session
    logger.info('请求处理完成, 重定向到WorkSpace页面')
    return redirect('workspace')
