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
    try:
        tenant = request.GET['tenant']
        username = request.GET['username']
        password = request.GET['password']
    except:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    token_id, tenant_id = get_token_tenant(tenant, username, password)
    if not token_id:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    vms_url = config.NOVA_URL + '/v2/' + tenant_id + '/servers/detail'
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    # TODO check whether return result is empty
    r = requests.get(vms_url, headers=headers).json()
    vms = r['servers']
    ret_info = {'total': len(vms), 'vms': []}
    for vm in vms:
        ret_info['vms'].append({
            'name': vm['name'],
            'ip': vm['addresses'].values()[0][0]['addr'],
            'host': vm['OS-EXT-SRV-ATTR:host'],
            'status': vm['status'],
            'created': vm['created']
        })
    return Response(ret_info)


@api_view(['GET'])
def pms_list(request, format=None):
    try:
        tenant = request.GET['tenant']
        username = request.GET['username']
        password = request.GET['password']
    except:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)

    token_id, tenant_id = get_token_tenant(tenant, username, password)
    if not token_id:
        return Response({}, status=status.HTTP_401_UNAUTHORIZED)

    pms_url = config.NOVA_URL + '/v2/' + tenant_id + '/os-hypervisors'
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(pms_url, headers=headers).json()
    pms = r['hypervisors']
    ret_info = {'total': len(pms), 'pms': pms}
    return Response(ret_info)


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'vms': reverse('vms', request=request, format=None),
        'pms': reverse('pms', request=request, format=None)
    })
