# -*- coding: utf-8 -*-

from FuXi.SPARQL.BackwardChainingStore import TopDownSPARQLEntailingStore
from FuXi.Horn.HornRules import HornFromN3
from rdflib.Graph import Graph
from rdflib import Namespace
from FuXi.Rete.RuleStore import SetupRuleStore
from FuXi.Rete.Util import generateTokenSet

import requests
import json
from . import config


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

def get_id_name_maps():
    token_url = config.AUTH_URL
    post_d = {'auth': {'tenantName': config.TENANT, 'passwordCredentials': {'username': config.USER, 'password': config.PASSWORD}}}
    r = requests.post(token_url, json=post_d, headers={'Content-type': 'application/json'})
    token_id = r.json()["access"]["token"]["id"]
    tenant_id = r.json()["access"]["token"]["tenant"]["id"]
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}

    url = config.NOVA_URL + tenant_id + '/servers'
    r = requests.get(url, headers=headers)
    rs = {}
    if r.status_code != 200:
        return rs
    vms = r.json()['servers']
    for v in vms:
        rs[str(v['name'])] = str(v['id'])
    return rs

def get_hosts_info():
    token_url = config.AUTH_URL
    post_d = {'auth': {'tenantName': config.TENANT, 'passwordCredentials': {'username': config.USER, 'password': config.PASSWORD}}}
    r = requests.post(token_url, json=post_d, headers={'Content-type': 'application/json'})
    token_id = r.json()["access"]["token"]["id"]
    tenant_id = r.json()["access"]["token"]["tenant"]["id"]
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}

    url = config.NOVA_URL + tenant_id + '/os-hypervisors'
    r = requests.get(url, headers=headers)
    rs = {}
    if r.status_code != 200:
        return rs
    hosts = r.json()['hypervisors']
    for h in hosts:
        rs[str(h['hypervisor_hostname'])] = h['id']
    return rs

'''
the vms/res an app/vm related.
'''
def get_related(types, **kwargs):
    famNs = Namespace('http://cetc/onto.n3#')
    nsMapping = {'': famNs}
    rule_store, rule_graph, network = SetupRuleStore(makeNetwork=True)
    closureDeltaGraph=Graph()
    closureDeltaGraph.bind('', famNs)
    network.inferredFacts = closureDeltaGraph

    for rule in HornFromN3('openstack/ontology/rule.n3'):
        network.buildNetworkFromClause(rule)

    factGraph = Graph().parse('openstack/ontology/resource.n3', format='n3')
    factGraph.bind('', famNs)
    network.feedFactsToAdd(generateTokenSet(factGraph))

    # print closureDeltaGraph.serialize(format='n3')
    rs = []
    if types == 'res':
        r_list = list(closureDeltaGraph.query('SELECT ?RESULT {:%s :key_res ?RESULT}' % kwargs['app'], initNs=nsMapping))
        for r in r_list:
            rs.append(str(r.split('#')[1]))
    elif types == 'app':
        r_list = list(closureDeltaGraph.query('SELECT ?RESULT {:%s :related_to ?RESULT}' % kwargs[types], initNs=nsMapping))
        id_maps = get_id_name_maps()
        for r in r_list:
            name = str(r.split('#')[1])
            rs.append({'name': name, 'id': id_maps[name]})
    elif types == 'vm':
        r_list = list(closureDeltaGraph.query('SELECT ?RESULT {:%s :related_to ?RESULT}' % kwargs[types], initNs=nsMapping))
        host_ids = get_hosts_info()
        for r in r_list:
            name = str(r.split('#')[1])
            rs.append({'name': name, 'id': host_ids[name]})
    return rs
