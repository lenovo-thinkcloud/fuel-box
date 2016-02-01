
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

from __future__ import print_function

import sys
import os
import string
import re
import time
import subprocess
import logging
import libvirt
from libvirt import libvirtError
from xml.etree import ElementTree as ET

from fuelbench import config_manager
from fuelbench import utils
from fuelbench.settings import *
from fuelbench.error import *

NAT_NETWORK_XML = """\
<network>
  <name>${name}</name>
  <forward mode='nat'/>
  <bridge stp='on' delay='0' />
  <ip address='${ipaddr}' netmask='${netmask}'>
  </ip>
</network>
"""

ISO_NETWORK_XML = """\
<network ipv6='yes'>
  <name>${name}</name>
  <bridge stp='on' delay='0' />
</network>
"""

logger = logging.getLogger(__name__)

class KvmProvider(object):
    
    def __init__(self, uri='qemu:///system', config=config_manager.defaults()):
        self.uri = uri
        self.config = config

    def __list_site_domains(self, conn, site):
        prefix = 'site' + str(site) + '-'
        domains = list()

        for dom in conn.listAllDomains(0x0):
            name = dom.name()
            if name.startswith(prefix):
                domains.append(dom)

        return domains
    
    def __list_all_domains(self, conn):
        pattern = re.compile(r'^site(\d+)-(.+)$')
        domains = list()

        for dom in conn.listAllDomains(0x0):
            name = dom.name()
            if pattern.match(name):
                domains.append(dom)

        return domains
        
    def __undefine_domain(self, name):
        cmdline = 'virsh --connect {uri} undefine {domain} --managed-save --snapshots-metadata --remove-all-storage'.format(uri=self.uri, domain=name)
        
        retcode = subprocess.call(cmdline + '>>{0} 2>&1'.format(CONSOLE_LOG), shell=True)
        
        if retcode != 0:
            raise RuntimeError('Command failed with exit code {0}'.format(retcode))
    
    def __delete_volume(self, name, pool):
        cmdline = 'virsh --connect {uri} vol-delete {vol} --pool {pool}'.format(uri=self.uri, vol=name, pool=pool)
        
        retcode = subprocess.call(cmdline + '>>{0} 2>&1'.format(CONSOLE_LOG), shell=True)
        
        if retcode != 0:
            raise RuntimeError('Command failed with exit code {0}'.format(retcode))
        
    def __snapshot_create_as(self, domain, name, desc=''):
        cmdline = 'virsh --connect {uri} snapshot-create-as {domain} {name} --description "{desc}"'.format(uri=self.uri, 
                                                                                                           domain=domain,
                                                                                                           name=name,
                                                                                                           desc=desc)
        logger.info('Execute: %s', cmdline)
        retcode = subprocess.call(cmdline + '>>{0} 2>&1'.format(CONSOLE_LOG), shell=True)
        logger.info('Return code: %d', retcode)
        
        if retcode != 0:
            raise CommandLineError(cmdline, retcode)
        
    def __snapshot_revert(self, domain, name):
        cmdline = 'virsh --connect {uri} snapshot-revert {domain} {name}'.format(uri=self.uri, 
                                                                                 domain=domain,
                                                                                 name=name)
        logger.info('Execute: %s', cmdline)
        retcode = subprocess.call(cmdline + '>>{0} 2>&1'.format(CONSOLE_LOG), shell=True)
        logger.info('Return code: %d', retcode)
        
        if retcode != 0:
            raise CommandLineError(cmdline, retcode)
        
    def __keep_pxe_boot(self, vm_name):
        conn = libvirt.open(self.uri)
                
        dom = conn.lookupByName(vm_name)
        xml_root = ET.fromstring(dom.XMLDesc())
        
        xml_os = xml_root.find('os')
        for item in xml_os.findall('boot'):
            xml_os.remove(item)
        
        ET.SubElement(xml_os, 'boot', {'dev': 'network'})
        ET.SubElement(xml_os, 'boot', {'dev': 'hd'})
        
        xml_desc = ET.tostring(xml_root)
        conn.defineXML(xml_desc)
        
        conn.close()

    def get_storage_pool_path(self):
        pool_name = self.config['storage_pool']
        
        conn = libvirt.openReadOnly(self.uri)
        
        pool = conn.storagePoolLookupByName(pool_name)
        pool_info_root = ET.fromstring(pool.XMLDesc())
        
        conn.close()
        
        return pool_info_root.find("./target/path").text

    def get_vm_nodes(self, site):
        conn = libvirt.openReadOnly(self.uri)

        domains = self.__list_site_domains(conn, site)
        name_list = [dom.name() for dom in domains]

        conn.close()

        return name_list
    
    def get_max_node_id(self, site):
        vm_nodes = self.get_vm_nodes(site)
        pattern = re.compile(r'^site(\d+)-node-(\d+)$')
        
        max_id = 0
        
        for vm in vm_nodes:
            match = pattern.match(vm)
            if match:
                id = int(match.group(2))
                if (id > max_id):
                    max_id = id
    
        return max_id
        
        
    def clean_vm_nodes(self, site):
        conn = libvirt.open(self.uri)

        domains = self.__list_site_domains(conn, site)

        for dom in domains:
            if dom.isActive():
                dom.destroy()
                
            name = dom.name()            
            self.__undefine_domain(name)
            
        conn.close()
        
    def clean_slave_nodes(self, site):
        conn = libvirt.open(self.uri)

        domains = self.__list_site_domains(conn, site)

        for dom in domains:
            name = dom.name()
            if name.endswith('-master'):
                continue
            
            if dom.isActive():
                dom.destroy()
                
            self.__undefine_domain(name)
            
        conn.close()    
        
    def clean_all_vm_nodes(self):
        conn = libvirt.open(self.uri)

        domains = self.__list_all_domains(conn)

        for dom in domains:
            if dom.isActive():
                dom.destroy()
                
            name = dom.name()            
            self.__undefine_domain(name)
            
        conn.close()  

    def install_vm_node(self, site, name,
                        vcpus=1, ram=2048,
                        boot='cdrom', iso_image='',
                        disk_format='qcow2', disk_size=40, disk_io='threads',
                        networks=[],
                        os_variant='centos6.5',
                        wait=0,
                        delete_media=False,
                        persistent_boot=False):
	
        vm_name = "site{0}-{1}".format(site, name)

        install_cmd = 'virt-install --connect {uri} --virt-type kvm --name {name} --vcpus {vcpus} --ram {ram}'.format(uri=self.uri, name=vm_name, vcpus=vcpus, ram=ram)
		
        pool_path = self.get_storage_pool_path()
        disk_opt = '--disk path={pool_path}/{disk_name}.img,format={disk_format},size={disk_size},bus=virtio,cache=writeback,io={disk_io}'.format(pool_path=pool_path, disk_name=vm_name, disk_format=disk_format, disk_size=disk_size, disk_io=disk_io)

        net_opt = ''
        for net in networks:
            if len(net_opt) > 0:
                net_opt += ' '
            net_opt += '--network network={network},model=virtio'.format(network=net)

        graphics_opt = '--graphics vnc --noautoconsole'

        if boot == 'cdrom':
            if iso_image:
                boot_opt = '--cdrom {iso}'.format(iso=iso_image)
            else:
                raise ValueError('A valid ISO file is required')
        elif boot == 'pxe':
            boot_opt = '--pxe'
        else:
            raise NotImplementedError('Unsupported boot mode: ' + boot)

        os_opt = '--os-variant {0}'.format(os_variant)
        
        misc_opt = '--wait={wait}'.format(wait=wait)

        cmdline = ' '.join([install_cmd,
                            disk_opt, net_opt,
                            graphics_opt, boot_opt, 
                            os_opt, misc_opt])
        
        try:
            with open(CONSOLE_LOG, 'a') as log:
                print(cmdline, file=log)            
               
            retcode = subprocess.call(cmdline + '>>{0} 2>&1'.format(CONSOLE_LOG), shell=True)
    
            if retcode != 0:
                raise RuntimeError('Command failed with exit code {0}'.format(retcode))
        
        finally:
            if delete_media and iso_image:
                self.__delete_volume(os.path.basename(iso_image), 'tmp')
                
        if persistent_boot:
            self.destroy_vm_node(site, name)
            
            if boot == 'pxe':
                self.__keep_pxe_boot(vm_name)
            
            time.sleep(1)            
            self.start_vm_node(site, name)
        
        return vm_name
    
    
    def start_vm_node(self, site, name):
        conn = libvirt.open(self.uri)
        
        vm_name = "site{0}-{1}".format(site, name)
        
        dom = conn.lookupByName(vm_name)
        ret = dom.create()
        
        conn.close()
        
        return ret == 0
    
    
    def destroy_vm_node(self, site, name):
        conn = libvirt.open(self.uri)
        
        vm_name = "site{0}-{1}".format(site, name)
        
        dom = conn.lookupByName(vm_name)
        ret = dom.destroy()
        
        conn.close()
        
        return ret == 0
    
    def restart_vm_node(self, site, name):
        conn = libvirt.open(self.uri)
        
        vm_name = "site{0}-{1}".format(site, name)
        
        dom = conn.lookupByName(vm_name)
        ret = dom.reset()
        
        conn.close()
        
        return ret == 0
    
    def delete_vm_node(self, site, name):
        
        vm_name = "site{0}-{1}".format(site, name)
                   
        self.__undefine_domain(vm_name)
    
    def check_vm_node_active(self, site, name):
        conn = libvirt.openReadOnly(self.uri)
        
        vm_name = "site{0}-{1}".format(site, name)
        
        dom = conn.lookupByName(vm_name)
        is_active = dom.isActive()
        
        conn.close()
        
        return is_active
    
    def create_vm_snapshot(self, site, name, snapshot, description=''):
        vm_name = "site{0}-{1}".format(site, name)
        success = False
        
        try:
            self.__snapshot_create_as(vm_name, snapshot, description)
            success = True
        except CommandError as e:
            logger.error(e)
            success = False
        
        return success
    
    def revert_vm_snapshot(self, site, name, snapshot):
        vm_name = "site{0}-{1}".format(site, name)
        success = False
        
        try:
            self.__snapshot_revert(vm_name, snapshot)
            success = True
        except CommandError as e:
            logger.error(e)
            success = False
        
        return success

    def __list_site_networks(self, conn, site):
        prefix = 'site' + str(site) + 'net'
        networks = list()

        for net in conn.listAllNetworks(0x0):
            name = net.name()
            if name.startswith(prefix):
                networks.append(net)

        return networks
    
    def __list_all_networks(self, conn):
        pattern = re.compile(r'^site(\d+)net(\d+)$')
        networks = list()

        for net in conn.listAllNetworks(0x0):
            name = net.name()
            if pattern.match(name):
                networks.append(net)

        return networks

    def __create_nat_network(self, conn, name, ipaddr, netmask):

        template = string.Template(NAT_NETWORK_XML)
        xml = template.substitute(name=name,
                                  ipaddr=ipaddr,
                                  netmask=netmask)

        net = conn.networkDefineXML(xml)
        net.setAutostart(1)
        net.create()

        return net

    def __create_isolated_network(self, conn, name):

        template = string.Template(ISO_NETWORK_XML)
        xml = template.substitute(name=name)

        net = conn.networkDefineXML(xml)
        net.setAutostart(1)
        net.create()

        return net

    def get_networks(self, site):
        conn = libvirt.openReadOnly(self.uri)

        networks = self.__list_site_networks(conn, site)
        name_list = [net.name() for net in networks]

        conn.close()

        return name_list

    def clean_networks(self, site):
        conn = libvirt.open(self.uri)

        networks = self.__list_site_networks(conn, site)

        for net in networks:
            if net.isActive():
                net.destroy()

            net.undefine()

        conn.close()
        
    def clean_all_networks(self):
        conn = libvirt.open(self.uri)

        networks = self.__list_all_networks(conn)

        for net in networks:
            if net.isActive():
                net.destroy()

            net.undefine()

        conn.close()

    def create_networks(self, site, networks):
        conn = libvirt.open(self.uri)
        name_list = list()

        for idx, info in enumerate(networks, start=1):
            name = 'site{0}net{1}'.format(site, idx)
            if info['type'] == NETWORK_NAT:
                ipaddr = info['gateway']
                netmask = info['netmask']
                self.__create_nat_network(conn, name, ipaddr, netmask)
            elif info['type'] == NETWORK_ISOLATED:
                self.__create_isolated_network(conn, name)
            else:
                raise NotImplementedError("Unsupported network type: '{0}'".format(info.type))

            name_list.append(name)

        conn.close()
        return name_list
