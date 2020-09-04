from django.conf.urls import url

from . import views


urlpatterns = [
    url(r'^connect/workspace/$', views.workspace, name='connect_workspace'),
]
