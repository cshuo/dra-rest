# -*- coding: utf-8 -*-
import requests
import json
import urllib2
from . import config

header = {"Content-Type": "application/json"}

def get_token_tenant(request):
    if request.method == 'GET':
        req_json = request.GET
    else:
        req_json = request.data

    try:
        tenant = req_json['tenant']
        user = req_json['username']
        passwd = req_json['password']
    except:
        return {'code':400, 'data':[None, None]}

    token_url = config.AUTH_URL
    post_d = {'auth': {'tenantName': tenant, 'passwordCredentials': {'username': user, 'password': passwd}}}
    r = requests.post(token_url, json=post_d, headers={'Content-type': 'application/json'})
    if r.status_code == 200:
        token_id = r.json()["access"]["token"]["id"]
        tenant_id = r.json()["access"]["token"]["tenant"]["id"]
        return {'code':200, 'data':[token_id, tenant_id]}
    else:
        return {'code':401, 'data':[None, None]}


def zabbix_req(baseIP, data):
    # create request object
    url = "http://"+baseIP+"/zabbix/api_jsonrpc.php"
    request = urllib2.Request(url,data)
    for key in header:
       request.add_header(key,header[key])
    # get host list
    try:
       result = urllib2.urlopen(request)
    except URLError as e:
       if hasattr(e, 'reason'):
           print 'Fetch result failed: ', e.reason
       elif hasattr(e, 'code'):
           print 'Fatch result failed: ', e.code
       return None
    else:
       response = json.loads(result.read())
       result.close()
       if "error" in response:
           return None
       return response['result']

def get_zabbix_token(baseIP, username='Admin', password='zabbix'):
    # auth user and password
    data = json.dumps(
    {
        "jsonrpc": "2.0",
        "method": "user.login",
        "params": {
        "user": username,
        "password": password
    },
    "id": 0
    })
    return zabbix_req(baseIP, data)

def get_zabbix_warning(baseIP):
    token = get_zabbix_token(baseIP)
    if not token:
        return None
    data = json.dumps(
    {
       "jsonrpc":"2.0",
       "method":"trigger.get",
       "params":{
           "output":[
               "triggerid",
               "description",
               "priority"
           ],
           "filter": {
               "value": 1
           },
           "sortfield": "priority",
           "sortorder": "DESC"
       },
       "auth":token,
       "id":1,
    })
    # create request object
    warnings = zabbix_req(baseIP, data)
    for w in warnings:
        w['description'] = w['description'].replace('{HOST.NAME}', 'instance:ubuntu')
    return warnings


def get_zabbix_history(baseIP, item_id, limit=10):
    token = get_zabbix_token(baseIP)
    if not token:
        return None
    data = json.dumps(
    {
       "jsonrpc":"2.0",
       "method":"history.get",
       "params":{
           "output":"extend",
           "history":0,
           "itemids":item_id,
           "sortfield": "clock",
           "sortorder": "DESC",
           "limit":limit
       },
       "auth":token, # theauth id is what auth script returns, remeber it is string
       "id":1,
    })
    # create request object
    return zabbix_req(baseIP, data)
