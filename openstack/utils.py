# -*- coding: utf-8 -*-

from FuXi.SPARQL.BackwardChainingStore import TopDownSPARQLEntailingStore
from FuXi.Horn.HornRules import HornFromN3
from rdflib.Graph import Graph
from rdflib import Namespace
from FuXi.Rete.RuleStore import SetupRuleStore
from FuXi.Rete.Util import generateTokenSet
from pyzabbix import ZabbixAPI
import datetime
import time
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
        return {'code': 400, 'data': [None, None]}

    token_url = config.AUTH_URL
    post_d = {'auth': {'tenantName': tenant, 'passwordCredentials': {'username': user, 'password': passwd}}}
    r = requests.post(token_url, json=post_d, headers={'Content-type': 'application/json'})
    if r.status_code == 200:
        token_id = r.json()["access"]["token"]["id"]
        tenant_id = r.json()["access"]["token"]["tenant"]["id"]
        # print token_id
        return {'code': 200, 'data': [token_id, tenant_id]}
    else:
        return {'code': 401, 'data': [None, None]}


def get_id_name_maps():
    """
    获取vm的name, id对应映射, key是name, value是id;
    :return:
    """
    token_url = config.AUTH_URL
    post_d = {'auth': {'tenantName': config.TENANT,
                       'passwordCredentials': {'username': config.USER, 'password': config.PASSWORD}}}
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
    post_d = {'auth': {'tenantName': config.TENANT,
                       'passwordCredentials': {'username': config.USER, 'password': config.PASSWORD}}}
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
    """
    """
    _, inferedgraph, ns = build_graph()
    # print closureDeltaGraph.serialize(format='n3')
    rs = []
    if types == 'res':
        r_list = list(
            inferedgraph.query('SELECT ?RESULT {:%s :key_res ?RESULT}' % kwargs[types], initNs=ns))
        for r in r_list:
            rs.append(str(r.split('#')[1]))
    elif types == 'app':
        r_list = list(
            inferedgraph.query('SELECT ?RESULT {:%s :related_to ?RESULT}' % kwargs[types], initNs=ns))
        id_maps = get_id_name_maps()
        for r in r_list:
            name = str(r.split('#')[1])
            rs.append({'name': name, 'id': id_maps[name]})
    elif types == 'vm':
        r_list = list(
            inferedgraph.query('SELECT ?RESULT {:%s :related_to ?RESULT}' % kwargs[types], initNs=ns))
        host_ids = get_hosts_info()
        for r in r_list:
            name = str(r.split('#')[1])
            rs.append({'name': name, 'id': host_ids[name]})
    return rs


def get_maps(types, **kwargs):
    """
    get service-app maps and vm-app maps
    :param types:
    """
    factgraph, _, ns = build_graph()

    maps = {}
    if types == 'service':
        r_list = list(factgraph.query('SELECT ?RESULT {?RESULT rdf:type :Service}', initNs=ns))
        srvs = format_list(r_list)
        for s in srvs:
            r_list = list(factgraph.query('SELECT ?RESULT {:%s :has_component ?RESULT}' % s, initNs=ns))
            maps[s] = format_list(r_list)
    else:
        r_list = list(factgraph.query('SELECT ?RESULT {?RESULT :has_location :%s}' % kwargs['vm'], initNs=ns))
        apps = format_list(r_list)
        maps[kwargs['vm']] = apps

    return maps


def build_graph():
    """
    build factgraph from ontology, and build inferedGraph from rules and factgraph
    """
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

    return factGraph, closureDeltaGraph, nsMapping


def format_list(rs):
    """
    dealed with the results returned from reasoning
    """
    frs = []
    for r in rs:
        frs.append(str(r.split('#')[1]))
    return frs


def format_maps(pm_maps, vm_maps, service_maps):
    """
    generate required maps for frontend from map datas retrieved from backend
    :param pm_maps:
    :param vm_maps:
    :param service_maps:
    :return:
    """
    rs_data = []
    for key, val in pm_maps.items():
        pm_dict = {'id': key, 'data': {'cpu': 0, 'mem': 0, 'disk': 0, 'net': 0}, 'children': []}
        for vm in val:
            vm_dict = {'id': vm[0], 'name': vm[1], 'children': [], 'data': {'cpu': 0, 'mem': 0, 'disk': 0, 'net': 0}}
            for app in vm_maps[vm[0]]['apps']:
                app_dict = {'id': app, 'name': app}
                for srv, apps in service_maps.items():
                    if app in apps:
                        app_dict['service'] = srv
                vm_dict['children'].append(app_dict)
            pm_dict['children'].append(vm_dict)
        rs_data.append(pm_dict)
    return rs_data


def get_metrics(host, num_minutes):
    """
    get monitoring statistics of hypervisors using zabbix;
    :param host:
    :param num_minutes:
    :return:
    """
    mem_rs, cpu_rs, disk_rs, net_rs = {}, {}, {}, {}
    mem_rs['time'], mem_rs['value'] = [], []
    cpu_rs['time'], cpu_rs['value'] = [], []
    disk_rs['time'], disk_rs['value'] = [], []
    net_rs['time'], net_rs['value'] = [], []

    zapi = ZabbixAPI(config.ZABBIX_URL)
    zapi.login(config.ZABBIX_USER, config.ZABBIX_PASSWD)
    time_till = time.mktime(datetime.datetime.now().timetuple())
    time_from = time_till - 60 * num_minutes

    cpu_idle_id = zapi.item.get(filter={'host': host, 'name': 'CPU idle time'})[0]['itemid']
    disk_free_id = zapi.item.get(filter={'host': host, 'name': 'disk_usage'})[0]['itemid']
    mem_avail_id = zapi.item.get(filter={'host': host, 'name': 'mem_avail_usage'})[0]['itemid']
    # net_in_id = zapi.item.get(filter={'host':host, 'name':'net_total_in'})[0]['itemid']

    # get statistics of memory usage
    mem_avail_datas = zapi.history.get(itemids=[mem_avail_id], time_from=time_from, time_till=time_till,
                                       output='extend', history=0)
    for item in mem_avail_datas:
        mem_rs['time'].append(item['clock'])
        mem_rs['value'].append(round(100 - float(item['value']), 2))

    # get statistics of cpu util
    cpu_idle_datas = zapi.history.get(itemids=[cpu_idle_id], time_from=time_from, time_till=time_till, output='extend',
                                      history=0)
    for item in cpu_idle_datas:
        cpu_rs['time'].append(item['clock'])
        cpu_rs['value'].append(round(100 - float(item['value']), 2))

    disk_free_datas = zapi.history.get(itemids=[disk_free_id], time_from=time_from, time_till=time_till,
                                       output='extend', history=0)
    for item in disk_free_datas:
        disk_rs['time'].append(item['clock'])
        disk_rs['value'].append(round(float(item['value']), 2))

    '''
    net_in_datas = zapi.history.get(itemids=[net_in_id], time_from=time_from, time_till=time_till, output='extend', history=0)
    for item in net_in_datas:
        net_rs['time'].append(item['clock'])
        net_rs['value'].append(round(float(item['value']), 2))
    '''

    return {'cpu': cpu_rs, 'mem': mem_rs, 'disk': disk_rs, 'net_in': net_rs}


def diagnosis_info(app):
    """
    根据本体推理获取相关联资源(关联的服务,应用,及虚拟机(关键资源显示));
    :param app:
    :return: array of dicts, containing all related objects and its detail info.
    """
    fact_graph, inferred_graph, ns = build_graph()

    info ={
        'vms': [],
        'apps': [],
        'services': []
    }
    # get relate service
    r_list = list(fact_graph.query('SELECT ?RESULT {?RESULT :has_component :%s}' % app, initNs=ns))
    info['services'] = format_list(r_list)

    r_list = list(inferred_graph.query('SELECT ?RESULT {:%s :has_sibling ?RESULT}' % app, initNs=ns))
    info['apps'] = format_list(r_list)

    r_list = list(inferred_graph.query('SELECT ?RESULT {:%s :related_to ?RESULT}' % app, initNs=ns))
    info['vms'] = format_list(r_list)

    r_list = list(inferred_graph.query('SELECT ?RESULT {:%s :key_res ?RESULT}' % app, initNs=ns))
    info['res'] = format_list(r_list)

    return info


def get_meters(vm_id, meters, interval=0.034):
    """
    given the id and the wanted meters of a vm, get the avg of most recent interval statistics of those meters.
    :param vm_id:
    :param meters:
    :param interval: default as 2 minutes.
    :return: dict data, like {'cpu': 80, 'mem': 80}
    """
    token_url = config.AUTH_URL
    post_d = {'auth': {'tenantName': config.TENANT, 'passwordCredentials': {'username': config.USER, 'password': config.PASSWORD}}}
    r = requests.post(token_url, json=post_d, headers={'Content-type': 'application/json'})
    if r.status_code == 200:
        token_id = r.json()["access"]["token"]["id"]
    else:
        return {}

    rs = {}
    for m in meters:
        rs[m] = get_statistics(vm_id, m, interval, token_id)
    return rs


def get_statistics(vm_id, meter, interval, token_id):
    """
    获取一个虚拟机指定meter的最近interval时间内的平均使用值.
    :param vm_id:
    :param meter:
    :param interval:
    :param token_id:
    :return:
    """
    meter_url = config.CEIL_URL + 'meters/' + meter + "/statistics"

    # cal time range to get meter samples
    now_t = time.gmtime()
    end_t = datetime.datetime(*now_t[:6])
    # TODO check validity of interval, must be number
    begin_t = end_t - datetime.timedelta(hours=float(interval))

    # query params
    req_payload = (
        ('q.field', 'resource_id'), ('q.op', 'eq'), ('q.value', vm_id),
        ('q.field', 'timestamp'), ('q.op', 'ge'), ('q.value', begin_t.isoformat()),
        ('q.field', 'timestamp'), ('q.op', 'lt'), ('q.value', end_t.isoformat())
    )
    headers = {'Content-type': 'application/json', 'X-Auth-Token': token_id}
    r = requests.get(meter_url, params=req_payload, headers=headers).json()
    if len(r) < 1:
        return 0
    return r[0]['avg']
