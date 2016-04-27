from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from openstack import views

urlpatterns = [
    url(r'^$', views.api_root),
    url(r'^login$', views.login, name='login'),
    url(r'^vms$', views.vms_list, name='vms'),
    url(r'^pms$', views.pms_list, name='pms'),
    url(r'^infos$', views.infos, name='infos'),
    url(r'^flavors$', views.flavor_list, name='flavors'),
    url(r'^vnc/(?P<vm_id>\S+)$', views.vnc_url, name='vnc'),
    url(r'^usages$', views.usages, name='usages'),
    url(r'^vm/(?P<vm_id>\S+)$', views.vm_detail, name='vm'),
    url(r'^pm/(?P<pm_id>\S+)$', views.pm_detail, name='pm'),
    url(r'^meters/(?P<name>\S+)$', views.meters, name='meters'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
