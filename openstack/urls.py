from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns
from openstack import views

urlpatterns = [
    url(r'^$', views.api_root),
    url(r'^login$', views.login, name='login'),
    url(r'^vms$', views.vms_list, name='vms'),
    url(r'^pms$', views.pms_list, name='pms'),
    url(r'^apps$', views.apps_list, name='apps'),
    url(r'^maps$', views.maps_list, name='maps'),
    url(r'^rules$', views.rules, name='rules'),
    url(r'^rule/(?P<name>\S+)$', views.rule, name='rule'),
    url(r'^infos$', views.infos, name='infos'),
    url(r'^flavors$', views.flavor_list, name='flavors'),
    url(r'^vnc/(?P<vm_id>\S+)$', views.vnc_url, name='vnc'),
    url(r'^usages$', views.usages, name='usages'),
    url(r'^vm/(?P<vm_id>\S+)$', views.vm_detail, name='vm'),
    url(r'^pm/(?P<pm_id>\S+)$', views.pm_detail, name='pm'),
    url(r'^meters/(?P<name>\S+)$', views.meters, name='meters'),
    url(r'^pmeters$', views.pmeters, name='pmeters'),
    url(r'^logs$', views.logs, name='logs'),
    url(r'^relatobj$', views.related, name='rels'),
    url(r'^diagnosis$', views.diagnosis, name='diags')

]

urlpatterns = format_suffix_patterns(urlpatterns)
