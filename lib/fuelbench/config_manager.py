
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


import yaml
import getpass

from fuelbench import settings

def defaults():
	config = dict()
	config['default_iso'] = settings.DEFAULT_ISO
	config['fuel_version_file'] = settings.FUEL_VERSION_FILE
	config['max_site_id'] = settings.MAX_SITE_ID
	config['site_limit'] = settings.SITE_LIMIT
	config['node_limit'] = settings.NODE_LIMIT
	config['admin_network_ip'] = settings.ADMIN_NETWORK_IP
	config['public_network_ip'] = settings.PUBLIC_NETWORK_IP
	config['vm_install_wait'] = settings.VM_INSTALL_WAIT
	config['storage_pool'] = settings.STORAGE_POOL
	config['search_domain'] = settings.SEARCH_DOMAIN
	config['master_name'] = settings.MASTER_NAME
	config['master_cpu'] = settings.MASTER_CPU
	config['master_ram'] = settings.MASTER_RAM
	config['master_disk'] = settings.MASTER_DISK
	config['master_hostname'] = settings.MASTER_HOSTNAME
	config['master_user'] = settings.MASTER_USER
	config['master_pass'] = settings.MASTER_PASS 
	config['master_prompt'] = settings.MASTER_PROMPT
	config['default_controller'] = settings.DEFAULT_CONTROLLER
	config['default_compute'] = settings.DEFAULT_COMPUTE
	config['default_storage'] = settings.DEFAULT_STORAGE
	config['controller_cpu'] = settings.CONTROLLER_CPU
	config['controller_ram'] = settings.CONTROLLER_RAM
	config['controller_disk'] = settings.CONTROLLER_DISK
	config['compute_cpu'] = settings.COMPUTE_CPU
	config['compute_ram'] = settings.COMPUTE_RAM
	config['compute_disk'] = settings.COMPUTE_DISK
	config['storage_cpu'] = settings.STORAGE_CPU
	config['storage_ram'] = settings.STORAGE_RAM
	config['storage_disk'] = settings.STORAGE_DISK		
	config['fuelssh_adm_mapped_port'] = settings.FUELSSH_ADM_MAPPED_PORT
	config['fuelssh_pub_mapped_port'] = settings.FUELSSH_PUB_MAPPED_PORT
	config['fuelweb_adm_mapped_port'] = settings.FUELWEB_ADM_MAPPED_PORT
	config['fuelweb_pub_mapped_port'] = settings.FUELWEB_PUB_MAPPED_PORT
	config['horiweb_lt7_mapped_port'] = settings.HORIWEB_LT7_MAPPED_PORT
	config['horiweb_gt7_mapped_port'] = settings.HORIWEB_GT7_MAPPED_PORT
	config['horissl_lt7_mapped_port'] = settings.HORISSL_LT7_MAPPED_PORT
	config['horissl_gt7_mapped_port'] = settings.HORISSL_GT7_MAPPED_PORT
	
	return config


def load(user = None):
	if not user:
		user = getpass.getuser()
	
	with open(settings.CONFIG_FILE, 'r') as fp:
		local_cfg = yaml.load(fp)	
	
	config = defaults()
	config.update(local_cfg['global'])
	
	profiles = local_cfg['profiles']
	if profiles.has_key(user):
		config.update(profiles[user])
	
	return config
