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
    if types == 'res':
        r_list = list(closureDeltaGraph.query('SELECT ?RESULT {:%s :key_res ?RESULT}' % kwargs['app'], initNs=nsMapping))
    else:
        r_list = list(closureDeltaGraph.query('SELECT ?RESULT {:%s :related_to ?RESULT}' % kwargs[types], initNs=nsMapping))

    rs = []
    for r in r_list:
        rs.append(str(r.split('#')[1]))
    return rs
