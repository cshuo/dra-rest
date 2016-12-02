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
import json
import time, datetime
from collections import OrderedDict

from . import config
from .utils import (
    get_token_tenant,
    get_zabbix_warning
)
from .db.utils import(
    create_rules_table,
    RuleDb,
    DbUtil
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
            print type(server)
            print server
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

    maps = {}
    for vm in vms:
        if vm['OS-EXT-SRV-ATTR:host'] not in maps:
            maps[vm['OS-EXT-SRV-ATTR:host']] = []
        maps[vm['OS-EXT-SRV-ATTR:host']].append((vm['id'], vm['name']))
    return Response(maps)


@api_view(['GET', 'POST'])
def rules(request, format=None):
    if request.method == 'GET':
        rules = RuleDb.list_rules()
        if rules == None:
            return Response({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response(rules)
    elif request.method == 'POST':
        try:
            name = request.data['name']
            app_type = request.data['app_type']
            content = request.data['content']
        except:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        add_success = RuleDb.add_rule(name=name, app_type=app_type, content=content)
        if add_success:
            return Response({'log':'add rule successfully'})
        else:
            return Response({'log':'fail to add rule'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def warnings(request, format=None):
    if request.method == 'GET':
        try:
            base_ip = request.GET['baseip']
        except:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)

        warning_list = get_zabbix_warning(base_ip)
        if warning_list:
            return Response(warning_list)
        else:
            return Response({'Log': 'Zabbix internal error.'}, status=status.HTTP_404_NOT_FOUND)
    else:
        return Response({}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'DELETE'])
def rule(request, name, format=None):
    if request.method == 'GET':
        rule_info = RuleDb.query_rule(name)
        if not rule_info:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        return Response(rule_info)
    elif request.method == 'DELETE':
        delete_success = RuleDb.rm_rule(name)
        if not delete_success:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        return Response({})


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


@api_view(['GET','PUT','DELETE'])
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
            print r.json()
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
        print '404 here'
        return Response({}, status=status.HTTP_404_NOT_FOUND)

    ret_info['images'] = r_image.json()['images']
    ret_info['flavors'] = r_flavor.json()['flavors']
    ret_info['networks'] = r_net.json()['networks']
    ret_info['keys'] = r_key.json()['keypairs']
    return Response(ret_info)


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'vms': reverse('vms', request=request, format=None),
        'pms': reverse('pms', request=request, format=None),
    })
