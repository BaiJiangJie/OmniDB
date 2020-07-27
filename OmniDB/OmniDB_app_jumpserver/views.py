from django.http import JsonResponse
from django.shortcuts import redirect


def get_connection_url_view(request):
    """获取 connection url"""

    v_return = {
        'url': 'https://www.google.com/'
    }
    return JsonResponse(v_return)


def get_omnidb_session():
    pass


def connect(request):
    return redirect('workspace')
