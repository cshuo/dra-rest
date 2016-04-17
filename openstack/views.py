from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import authenticate
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes
)
import ast
import requests
import time, datetime
from collections import OrderedDict

from . import config
from .utils import get_token_tenant


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
    print r.status_code
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    ret_info = r.json()
    r_data = {'access': {'token_id': ret_info['access']['token']['id'],
                         'tenant_id': ret_info['access']['token']['tenant']['id']}}
    return Response(r_data)


@api_view(['GET'])
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

    vms_url = config.NOVA_URL + tenant_id + '/servers/detail'
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    # TODO check whether return result is empty
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


@api_view(['GET'])
def vm_detail(request, vm_id, format=None):
    data = get_token_tenant(request)
    if data['code'] == 400:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)
    elif data['code'] == 401:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    token_id, tenant_id = data['data']
    vm_url = config.NOVA_URL + tenant_id + '/servers/' + vm_id
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(vm_url, headers=headers)
    if r.status_code != 200:
        return Response({}, status=status.HTTP_404_NOT_FOUND)
    r = r.json()['server']
    flavor_id = r['flavor']['id']
    flavor_url = config.NOVA_URL + tenant_id + '/flavors/' + flavor_id
    flavor_info = requests.get(flavor_url, headers=headers).json()['flavor']
    r['flavor_name'] = flavor_info['name']
    r['disk'] = flavor_info['disk']
    r['cpu'] = flavor_info['vcpus']
    r['ram'] = flavor_info['ram']
    return Response(r)


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
    begin_t = end_t - datetime.timedelta(hours=int(interval))
    print begin_t.isoformat()
    print end_t.isoformat()

    # query params
    req_payload = (
        ('q.field', 'resource_id'), ('q.op', 'eq'), ('q.value', resource_id),
        ('q.field', 'timestamp'), ('q.op', 'ge'), ('q.value', begin_t.isoformat()),
        ('q.field', 'timestamp'), ('q.op', 'lt'), ('q.value', end_t.isoformat())
    )
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(meter_url, params=req_payload, headers=headers)
    if r.status_code != 200:
        print r.status_code
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    ret_d = {'time': [], 'value': []}
    for s in r.json():
        ret_d['time'].append(s['timestamp'].split('.')[0].split('T')[1])
        ret_d['value'].append(float(s['counter_volume']))
    ret_d['time'].reverse()
    ret_d['value'].reverse()
    return Response(ret_d)


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'vms': reverse('vms', request=request, format=None),
        'pms': reverse('pms', request=request, format=None),
    })
