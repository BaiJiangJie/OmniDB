from django.shortcuts import redirect
import logging

logger = logging.getLogger('JumpServer_app.views')


def workspace(request):
    return redirect('workspace')
