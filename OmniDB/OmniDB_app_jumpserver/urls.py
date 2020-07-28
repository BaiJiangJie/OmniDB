from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^connect/$', views.workspace.index, name='connect_workspace'),
]
