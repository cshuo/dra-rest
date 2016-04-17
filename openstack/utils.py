# -*- coding: utf-8 -*-
import requests
import json
from . import config


def get_token_tenant(request):
    try:
        tenant = request.GET['tenant']
        user = request.GET['username']
        passwd = request.GET['password']
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
