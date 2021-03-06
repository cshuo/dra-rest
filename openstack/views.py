# -*- coding:utf-8 -*-
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from openstack.models import Log
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes
)
import ast
import requests
import json
import time, datetime
from collections import OrderedDict
from django.utils import timezone

from . import config
from .utils import (
    get_token_tenant,
    get_related,
    get_metrics,
    get_maps,
    format_maps,
    get_id_name_maps,
    diagnosis_info,
    get_meters,
    get_apps
)


@api_view(['POST'])
def login(request, format=None):
    try:
        username = request.data['username']
        passwd = request.data['password']
    except:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    payload = {'auth': {'tenantName': config.TENANT, 'passwordCredentials': {'username': username, 'password': passwd}}}
    headers = {'Content-type': 'application/json'}
    r = requests.post(config.AUTH_URL, json=payload, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    ret_info = r.json()
    r_data = {'access': {'token_id': ret_info['access']['token']['id'],
                         'tenant_id': ret_info['access']['token']['tenant']['id']}}
    return Response(r_data)


@api_view(['GET'])
def apps_list(request, format=None):
    """
    根据本体文件, 获取所有的web类型应用 (主要dra用来对zabbix的 web scenario 和 web trigger 进行初始化)
    :param request:
    :param format:
    :return:
    """
    return Response(get_apps())


@api_view(['GET', 'POST'])
def vms_list(request, format=None):
    """
    get vms overview list
    :param request:
    :param format:
    :return:
    """
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    token_id, tenant_id = data['data']

    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}

    if request.method == 'GET':
        vms_url = config.NOVA_URL + tenant_id + '/servers/detail?all_tenants=true'
        r = requests.get(vms_url, headers=headers)
        if r.status_code != 200:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        vms = r.json()['servers']
        ret_info = {'total': len(vms), 'vms': []}
        for vm in vms:
            ret_info['vms'].append({
                'id': vm['id'],
                'name': vm['name'],
                'ip': vm['addresses'].values()[0][0]['addr'],
                'host': vm['OS-EXT-SRV-ATTR:host'],
                'status': vm['status'],
                'created': vm['created'],
                'flavor': vm['flavor']['id']
            })
        return Response(ret_info)

    elif request.method == 'POST':
        post_url = config.NOVA_URL + tenant_id + '/servers'
        try:
            server = request.data['server']
        except:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        post_val = {'server': json.loads(server)}

        r = requests.post(post_url, json=post_val, headers=headers)
        if r.status_code != 202:
            return Response(r.json(), status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({})


@api_view(['GET'])
def maps_list(request, format=None):
    """
    return maps of pm->vms, vm->apps, service->apps
    :param request:
    :param format:
    :return:
    """
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)
    token_id, tenant_id = data['data']
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}

    if request.method != 'GET':
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    vms_url = config.NOVA_URL + tenant_id + '/servers/detail?all_tenants=true'
    r = requests.get(vms_url, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    vms = r.json()['servers']

    pms_url = config.NOVA_URL + tenant_id + '/os-hypervisors'
    r = requests.get(pms_url, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    pms = r.json()['hypervisors']

    pm_maps, vm_maps = {}, {}
    for pm in pms:
        pm_maps[pm['hypervisor_hostname']] = []
    for vm in vms:
        pm_maps[vm['OS-EXT-SRV-ATTR:host']].append((vm['id'], vm['name']))
        vm_maps[vm['id']] = {}
        vm_maps[vm['id']]['name'] = vm['name']
        vm_maps[vm['id']]['apps'] = get_maps('vm', vm=vm['name'])[vm['name']]

    service_maps = get_maps('service')
    return Response(format_maps(pm_maps, vm_maps, service_maps))
    # return Response({'pm': pm_maps, 'service': service_maps, 'vm': vm_maps})


@api_view(['GET'])
def pms_list(request, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    token_id, tenant_id = data['data']

    pms_url = config.NOVA_URL + tenant_id + '/os-hypervisors'
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(pms_url, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    pms = r.json()['hypervisors']
    ret_info = {'total': len(pms), 'pms': pms}
    return Response(ret_info)


@api_view(['GET'])
def flavor_list(request, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)
    token_id, tenant_id = data['data']
    flavors_url = config.NOVA_URL + tenant_id + '/flavors/detail'
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(flavors_url, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    flavors = r.json()['flavors']
    flavor_dict = dict()
    for f in flavors:
        flavor_dict[f['id']] = {
            'name': f['name'],
            'cpu': f['vcpus'],
            'ram': f['ram'],
            'disk': f['disk']
        }
    return Response(flavor_dict)


@api_view(['GET'])
def vnc_url(request, vm_id, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)
    token_id, tenant_id = data['data']

    vnc_url = config.NOVA_URL + tenant_id + '/servers/' + vm_id + '/action'
    params = {"os-getVNCConsole": {"type": "novnc"}}
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    post = requests.post(vnc_url, json=params, headers=headers)
    r = dict()
    if post.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    else:
        r['vnc'] = post.json()['console']['url']
        return Response(r)


@api_view(['GET'])
def usages(request, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)
    token_id, tenant_id = data['data']

    usages_url = config.NOVA_URL + tenant_id + '/os-hypervisors/statistics'
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(usages_url, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    return Response(r.json()['hypervisor_statistics'])


@api_view(['GET', 'PUT', 'DELETE'])
def vm_detail(request, vm_id, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    token_id, tenant_id = data['data']
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    if request.method == 'GET':
        # get detail info of a vm
        vm_url = config.NOVA_URL + tenant_id + '/servers/' + vm_id
        r = requests.get(vm_url, headers=headers)
        if r.status_code != 200:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        r = r.json()['server']

        ips = []
        for key in r['addresses'].keys():
            for net in r['addresses'][key]:
                ips.append(net['addr'])
        r['ips'] = ips

        flavor_id = r['flavor']['id']
        flavor_url = config.NOVA_URL + tenant_id + '/flavors/' + flavor_id
        flavor_info = requests.get(flavor_url, headers=headers).json()['flavor']
        r['flavor_name'] = flavor_info['name']
        r['disk'] = flavor_info['disk']
        r['cpu'] = flavor_info['vcpus']
        r['ram'] = flavor_info['ram']
        return Response(r)
    elif request.method == 'PUT':
        # exec actions(start, stop) on a vm
        cmd = request.data['cmd']
        action_url = config.NOVA_URL + tenant_id + '/servers/' + vm_id + '/action'
        if cmd == 'stop':
            post_val = {'os-stop': 'null'}
        elif cmd == 'start':
            post_val = {'os-start': 'null'}
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        r = requests.post(action_url, json=post_val, headers=headers)
        if r.status_code == 202:
            return Response({})
        else:
            return Response(r.json(), status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        # delete a vm
        vm_url = config.NOVA_URL + tenant_id + '/servers/' + vm_id
        r = requests.delete(vm_url, headers=headers)
        if r.status_code == 204:
            return Response({})
        else:
            return Response(r.json(), status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def pm_detail(request, pm_id, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    token_id, tenant_id = data['data']
    pm_url = config.NOVA_URL + tenant_id + '/os-hypervisors/' + pm_id
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(pm_url, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    return Response(r.json()['hypervisor'])


@api_view(['GET'])
def pmeters(request, format=None):
    """
    获取物理机监控信息,基于zabbix
    :param request:
    :param format:
    :return:
    """
    try:
        host = request.GET['host']
        numMnt = request.GET['num']
    except:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    data = get_metrics(host=host, num_minutes=int(numMnt))

    for metric, val in data.items():
        utctime = val['time']
        time = []
        for t in utctime:
            time.append(datetime.datetime.utcfromtimestamp(int(t)).strftime('%H:%M:%S'))
        data[metric]['time'] = time
    # print "######################\n", data
    return Response(data)


@api_view(['GET'])
def meters(request, name, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)
    token_id, _ = data['data']

    try:
        resource_id = request.GET['resource']
        interval = request.GET['interval']
    except:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    meter_url = config.CEIL_URL + 'meters/' + name

    # cal time range to get meter samples
    now_t = time.gmtime()
    end_t = datetime.datetime(*now_t[:6])
    # TODO check validity of interval, must be number
    begin_t = end_t - datetime.timedelta(hours=float(interval))

    # query params
    req_payload = (
        ('q.field', 'resource_id'), ('q.op', 'eq'), ('q.value', resource_id),
        ('q.field', 'timestamp'), ('q.op', 'ge'), ('q.value', begin_t.isoformat()),
        ('q.field', 'timestamp'), ('q.op', 'lt'), ('q.value', end_t.isoformat())
    )
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(meter_url, params=req_payload, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    ret_d = {'time': [], 'value': []}
    for s in r.json():
        ret_d['time'].append(s['timestamp'].split('.')[0].split('T')[1])
        ret_d['value'].append(float(s['counter_volume']))
    ret_d['time'].reverse()
    ret_d['value'].reverse()
    return Response(ret_d)


@api_view(['GET'])
def infos(request, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    token_id, tenant_id = data['data']

    images_url = config.NOVA_URL + tenant_id + '/images/detail'
    flavors_url = config.NOVA_URL + tenant_id + '/flavors/detail'
    nets_url = config.NOVA_URL + tenant_id + '/os-networks'
    keys_url = config.NOVA_URL + tenant_id + '/os-keypairs'
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}

    ret_info = {}
    r_image = requests.get(images_url, headers=headers)
    r_flavor = requests.get(flavors_url, headers=headers)
    r_net = requests.get(nets_url, headers=headers)
    r_key = requests.get(keys_url, headers=headers)
    if r_key.status_code != 200 or r_net.status_code != 200 \
            or r_flavor.status_code != 200 or r_image.status_code != 200:
        # print '404 here'
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    ret_info['images'] = r_image.json()['images']
    ret_info['flavors'] = r_flavor.json()['flavors']
    ret_info['networks'] = r_net.json()['networks']
    ret_info['keys'] = r_key.json()['keypairs']
    return Response(ret_info)


@api_view(['GET', 'POST', 'DELETE'])
def logs(request, format=None):
    if request.method == 'GET':
        try:
            holder = request.GET['holder']
            num = request.GET['num']
            types = request.GET['type']
        except:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        if holder == 'all':
            logs = Log.objects.all().order_by('-time')[:int(num)]
        elif types == 'all':
            logs = Log.objects.filter(holder=holder).order_by('-time')[:int(num)]
        else:
            logs = Log.objects.filter(holder=holder, log_type=types).order_by('-time')[:int(num)]

        rs = []
        for log in logs:
            log_dict = {'holder': log.holder, 'type': log.log_type, 'info': log.log_info, 'time': log.time}
            rs.append(log_dict)
        return Response(rs)

    elif request.method == 'POST':
        try:
            holder = request.data['holder']
            types = request.data['type']
            info = request.data['info']
        except:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        log = Log(holder=holder, log_type=types, log_info=info, time=timezone.now())
        log.save()
        return Response({})

    elif request.method == 'DELETE':
        try:
            holder = request.data['holder']
            types = request.data['type']
        except:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        Log.objects.filter(holder=holder, log_type=types).delete()
        return Response({})


@api_view(['GET'])
def related(request, format=None):
    try:
        types = request.GET['type']
        objects = request.GET['object']
    except:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    if types == 'vm':
        rs = get_related(types, vm=objects)
    else:
        rs = get_related(types, app=objects)
    return Response(rs)


@api_view(['GET'])
def diagnosis(request, format=None):
    """
    应用性能出现异常, 根据本体推理得到关联资源(所在服务, 关联的应用, 关联的虚拟机(及其关键资源).)
    :param request:
    :param format:
    :return:
    """
    try:
        app = request.GET['app']
    except:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    rs = []
    id_maps = get_id_name_maps()
    d_info = diagnosis_info(app)

    for a in d_info['apps']:
        rs.append({
            'type': 'status',
            'id': a,
            'target': 'app',
            'status': 'warning'
        })

    for s in d_info['services']:
        rs.append({
            'type': 'status',
            'id': s,
            'target': 'service',
            'status': 'warning'
        })

    for vm in d_info['vms']:
        vm_id = id_maps[vm['vm']]
        rs.append({
            'type': 'status',
            'id': vm_id,
            'target': 'vms',
            'status': 'warning',
            'warning': get_meters(vm_id, vm['res'])
        })
    return Response(rs)


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'vms': reverse('vms', request=request, format=None),
        'pms': reverse('pms', request=request, format=None),
    })
