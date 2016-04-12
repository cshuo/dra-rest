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

from . import config
from .utils import get_token_tenant


# Create your views here.
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
            'created': vm['created']
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
    flavor_url = config.NOVA_URL + tenant_id + '/flavors/' +flavor_id
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


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'vms': reverse('vms', request=request, format=None),
        'pms': reverse('pms', request=request, format=None),
    })
