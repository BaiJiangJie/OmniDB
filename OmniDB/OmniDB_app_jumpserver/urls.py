from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^connection_url/$', views.get_connection_url_view, name='create_connection'),
    url(r'^connect/$', views.connect, name='create_connection'),
]
