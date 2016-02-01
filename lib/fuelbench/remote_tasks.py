
#    Copyright 2015 Lenovo, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
#    Author: Joey Zhang <zhangzhuo4@lenovo.com>

import os
import re
import StringIO
import logging
import yaml

from fabric.api import *

from fuelbench import utils
from fuelbench.error import *


logger = logging.getLogger(__name__)

@task
def get_all_fuel_nodes():
    nodes = dict()
    
    cmdline = "fuel node --list"
    logger.debug('Run: %s', cmdline)
    
    result = run(cmdline)
    logger.debug('Result: %s', result)
    
    buf = StringIO.StringIO(result)
    
    started = False
    
    for line in buf.readlines():
        if line.startswith('---'):
            started = True
            continue
        
        if started:
            fields = line.split('|')
            if len(fields) >= 10:
                id = int(fields[0].strip())
                status = fields[1].strip()
                name = fields[2].strip()
                cluster = fields[3].strip()
                ip = fields[4].strip()
                mac = fields[5].strip()
                roles = fields[6].strip()
                pending_roles = fields[7].strip()
                online = bool(fields[8].strip())
                group_id = fields[9].strip()
                
                nodes[id] = {'id': id,
                             'status': status,
                             'name': name,
                             'cluster': utils.parse_int(cluster),
                             'ip': ip,
                             'mac': mac,
                             'roles': utils.parse_list(roles),
                             'pending_roles': utils.parse_list(pending_roles),
                             'online': utils.parse_bool(online),
                             'group_id': utils.parse_int(group_id)}
    
    return nodes.values()

@task
def create_fuel_env(name, release, mode, network):
    cmdline = "fuel env create --name '{name}' --rel {release} --mode {mode}".format(name=name,
                                                                                     release=release,
                                                                                     mode=mode)
    if network == 'nova':
        network_opts = ' --net nova'
    elif network == 'neutron-vlan':
        network_opts = ' --net neutron --nst vlan'
    elif network == 'neutron-gre':
        network_opts = ' --net neutron --nst gre'
    else:
        raise ValueError('Unsupported network mode: {0}'.format(network))
    
    cmdline += network_opts
        
    
    logger.debug('Run: %s', cmdline) 
       
    result = run(cmdline)
    logger.debug('Result: %s', result)
    
    buf = StringIO.StringIO(result)
        
    id = None
    
    for line in buf.readlines():
        match = re.search(r'^Environment .*\bid=(\d+)\b', line)
        if match:
            id = int(match.group(1))
            break
    
    if id is None:
        raise RemoteTaskError('Environment ID not found')
    else:
        return id


def setup_site_network(cfg, public_vip, floating_ranges, public_cidr, public_gateway, public_ranges):
    cfg['networking_parameters']['floating_ranges'] = [list(floating_ranges)]
    cfg['public_vip'] = public_vip
    
    for info in cfg['networks']:
        meta = info['meta']
        
        if info.get('name') == 'public':
            info['cidr'] = public_cidr
            info['gateway'] = public_gateway
            info['ip_ranges'] = [list(public_ranges)]
            meta['cidr'] = public_cidr
            meta['ip_range'] = list(public_ranges)
    
    return cfg

def setup_site_settings(cfg, upstream_dns):
    
    cfg['editable']['common']['libvirt_type']['value'] = 'kvm'
    
    cfg['editable']['common']['debug']['value'] = True
    
    cfg['editable']['external_dns']['dns_list']['value'] = upstream_dns
    
    return cfg

def setup_node_network(cfg):
    iso_networks = ('management', 'storage', 'private')
    
    iso_interface = None
    for interface in cfg:
        if interface['name'] == 'eth2':
            iso_interface = interface
            break
    
    if iso_interface is None:
        raise ValueError("Interface 'eth2' not found")
    
    iso_assigned_networks = iso_interface['assigned_networks']
    
    for interface in cfg:
        if interface is iso_interface:
            continue
        
        assigned_networks = interface['assigned_networks']
        
        for assign in list(assigned_networks):
            name = assign['name'].strip()
            if name in iso_networks:
                assigned_networks.remove(assign)
                iso_assigned_networks.append(assign)
    
    return cfg

def setup_node_provisioning(cfg, admin_gw):
    
    cfg['ks_meta']['gw'] = admin_gw
    
    return cfg    


@task
def configure_fuel_env(id, workdir, public_vip, floating_ranges, public_cidr, public_gateway, public_ranges, upstream_dns):
    
    run("mkdir -p ~/fuelbench")
    
    with cd('~/fuelbench'):        
        # network configuration
        cmdline = "fuel network --env {id} network --download".format(id=id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)
        
        buf = StringIO.StringIO(result)
        match = None
        
        for line in buf.readlines():
            match = re.search(r'^Network configuration .* downloaded to\s+(.+)', line)
            if match:
                break
            
        if not match:
            raise RemoteTaskError('Network configuration file not found')
        
        remote_path = match.group(1).strip()
        filelist = get(remote_path, workdir)        
        if len(filelist) != 1:
            raise RemoteTaskError('Unable to get {0}'.format(remote_path))
        
        local_path = filelist[0]
        network_cfg = utils.modify_yamlfile(local_path, setup_site_network, public_vip, floating_ranges, public_cidr, public_gateway, public_ranges)
        logger.debug('Saving %s: ', local_path)
        logger.debug(network_cfg)
        
        put(local_path, remote_path)
        
        cmdline = "fuel --env {id} network --upload".format(id=id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)

        # settings configuration
        cmdline = "fuel --env {id} settings --download".format(id=id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)
        
        buf = StringIO.StringIO(result)
        match = None
        
        for line in buf.readlines():
            match = re.search(r'^Settings configuration .* downloaded to\s+(.+)', line)
            if match:
                break
            
        if not match:
            raise RemoteTaskError('Settings configuration file not found')
        
        remote_path = match.group(1).strip()
        filelist = get(remote_path, workdir)        
        if len(filelist) != 1:
            raise RemoteTaskError('Unable to get {0}'.format(remote_path))
        
        local_path = filelist[0]
        settings_cfg = utils.modify_yamlfile(local_path, setup_site_settings, upstream_dns)
        logger.debug('Saving %s: ', local_path)
        logger.debug(settings_cfg)
        
        put(local_path, remote_path)
        
        cmdline = "fuel --env {id} settings --upload".format(id=id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)
        
    
@task
def get_all_fuel_env():
    env_list = dict()
    
    cmdline = "fuel env --list"
    logger.debug('Run: %s', cmdline)
    
    result = run(cmdline)
    logger.debug('Result: %s', result)
    
    buf = StringIO.StringIO(result)
    
    started = False
    
    for line in buf.readlines():
        if line.startswith('---'):
            started = True
            continue
        
        if started:
            fields = line.split('|')
            if len(fields) >= 7:
                id = int(fields[0].strip())
                status = fields[1].strip()
                name = fields[2].strip()
                mode = fields[3].strip()
                release_id = fields[4].strip()
                changes = fields[5].strip()
                pending_release_id = fields[6].strip()
                
                env_list[id] = {'id': id,
                                'status': status,
                                'name': name,
                                'mode': mode,
                                'release_id': utils.parse_int(release_id),
                                'changes': utils.parse_eval(changes),
                                'pending_release_id': utils.parse_int(pending_release_id)}
    
    return env_list.values()

@task
def set_fuel_node_roles(env_id, node_ids, node_roles):
    cmdline = "fuel --env {end_id} node set --node {node_ids} --role {roles}".format(end_id=env_id,
                                                                                     node_ids=','.join(map(str, node_ids)),
                                                                                     roles=','.join(map(str, node_roles)))
    logger.debug('Run: %s', cmdline)
       
    result = run(cmdline)
    logger.debug('Result: %s', result)


@task
def configure_fuel_node(node_id, workdir, env_id, admin_gw):
    
    run("mkdir -p ~/fuelbench")
    
    with cd('~/fuelbench'):
        # node network configuration
        cmdline = "fuel node --node-id {node_id} --network --download".format(node_id=node_id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)
        
        buf = StringIO.StringIO(result)
        path_found = False
        
        for line in buf.readlines():
            if path_found:
                remote_path = line.strip()
            
            if re.search(r'^Node attributes for interfaces were written to', line):
                path_found = True
                continue
            
        if not path_found:
            raise RemoteTaskError('Node network configuration file not found')

        filelist = get(remote_path, workdir)        
        if len(filelist) != 1:
            raise RemoteTaskError('Failed to get {0}'.format(remote_path))
        
        local_path = filelist[0]
        network_cfg = utils.modify_yamlfile(local_path, setup_node_network)
        logger.debug('Saving %s: ', local_path)
        logger.debug(network_cfg)
        
        put(local_path, remote_path)
        
        cmdline = "fuel node --node-id {node_id} --network --upload".format(node_id=node_id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)
        
        # node provisioning configuration
        cmdline = "fuel --env {env_id} provisioning --default --node {node_id}".format(env_id=env_id,
                                                                                       node_id=node_id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)
        
        buf = StringIO.StringIO(result)
        match = None
        
        for line in buf.readlines():
            match = re.search(r'^Default provisioning info .*downloaded to\s+(.+)', line)
            if match:
                remote_dir = match.group(1).strip()
                remote_path = os.path.join(remote_dir, 'node-{0}.yaml'.format(node_id))
                break
            
        if not match:
            raise RemoteTaskError('Node provisioning configuration file not found')

        filelist = get(remote_path, workdir)        
        if len(filelist) != 1:
            raise RemoteTaskError('Failed to get {0}'.format(remote_path))
        
        local_path = filelist[0]
        network_cfg = utils.modify_yamlfile(local_path, setup_node_provisioning, admin_gw)
        logger.debug('Saving %s: ', local_path)
        logger.debug(network_cfg)
        
        put(local_path, remote_path)
        
        cmdline = "fuel --env {env_id} provisioning --upload".format(env_id=env_id)
        logger.debug('Run: %s', cmdline)    
        result = run(cmdline)
        logger.debug('Result: %s', result)

@task
def fuel_deploy_changes(env_id):
    cmdline = "fuel --env {env_id} deploy-changes".format(env_id=env_id)
    logger.debug('Run: %s', cmdline)
    
    run(cmdline)
   
@task
def get_fuel_version():
    cmdline = "awk -F': ' '/release/ {print $2}' /etc/fuel/version.yaml | sed -e 's/^[\"]*//' | sed -e 's/[\"]*$//'"
    logger.debug('Run: %s', cmdline)
    
    result = run(cmdline)
    logger.debug('Result: %s', result)
    
    buf = StringIO.StringIO(result)
    line = buf.readline()
    
    return line.strip()
    
@task
def check_vm_operational():
    cmdline = "grep 'Fuel node deployment' /var/log/puppet/bootstrap_admin_node.log"
    
    logger.debug('Run: %s', cmdline)
    
    result = run(cmdline)
    logger.debug('Result: %s', result)
    
    buf = StringIO.StringIO(result)
    
    for line in buf.readlines():
        if re.search(r'^Fuel.*complete.*', line):
            return True
    
    return False

@task
def power_off():
    cmdline = "poweroff"
    logger.debug('Run: %s', cmdline)
    
    sudo(cmdline)

@task
def run_remote_script(local_script, args):
    
    filelist = put(local_script, '~/')       
    if len(filelist) != 1:
            raise RemoteTaskError('Failed to put {0}'.format(local_script))
        
    remote_path = filelist[0]
    
    cmdline = 'sh {0} '.format(remote_path) + ' '.join(map(str, args))
    logger.debug('Run: %s', cmdline)
    
    result = run(cmdline)
    logger.debug('Result: %s', result)
    
    run("rm -rf '{0}'".format(remote_path))
    