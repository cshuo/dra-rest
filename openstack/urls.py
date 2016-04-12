from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from openstack import views

urlpatterns = [
    url(r'^$', views.api_root),
    url(r'^vms$', views.vms_list, name='vms'),
    url(r'^pms$', views.pms_list, name='pms'),
    url(r'^vm/(?P<vm_id>\S+)$', views.vm_detail, name='vm'),
    url(r'^pm/(?P<pm_id>\S+)$', views.pm_detail, name='pm'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
