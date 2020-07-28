from django.http import JsonResponse
from datetime import datetime
from django.http import HttpResponse
from django.shortcuts import redirect

from OmniDB_app.views.login import sign_in_automatic


def index(request):
    """获取 connection url"""

    # 获取数据: database_id、system_user_id、cookie
    database_id = ''
    system_user_id = ''
    cookie = ''

    # 校验JumpServer用户权限
    #: 校验登录状态
    #: 校验数据库权限

    # 获取JumpServer相关信息
    #: 获取用户信息
    #: 获取数据库信息
    #: 获取系统用户信息

    # 获取或创建OmniDB用户

    # 创建OmniDB connections连接

    # 设置OmniDB用户Session信息
    username = 'bai'
    password = 'bai'
    p_conn_id = 3
    num_connections = sign_in_automatic(request, username, password)
    if num_connections == -1:
        return HttpResponse("Set OmniDB Session Error")
    request.session['omnidb_session'].v_databases[p_conn_id]['database'].v_connection.v_password = 'root'
    # request.session['omnidb_session'].v_databases[p_conn_id]['prompt_timeout'] = datetime.now()

    # 创建JumpServer Session会话

    # 渲染workspace页面

    return redirect('workspace')

