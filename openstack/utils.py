# -*- coding: utf-8 -*-
import requests
import json
from . import config


def get_token_tenant(tenant, user, passwd):
    token_url = config.AUTH_URL + '/v2.0/tokens'
    post_d = {'auth': {'tenantName': tenant, 'passwordCredentials': {'username': user, 'password': passwd}}}
    r = requests.post(token_url, json=post_d, headers={'Content-type': 'application/json'})
    token_id = r.json()["access"]["token"]["id"]
    tenant_id = r.json()["access"]["token"]["tenant"]["id"]
    return token_id, tenant_id

