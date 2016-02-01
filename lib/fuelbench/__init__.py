
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
#            Yang Xiang <xiangyang1@lenovo.com>

from __future__ import print_function

__all__ = ['FuelBench', 'DefaultFuelBench']


import sys
import os
import time
import stat
import string
import getpass
import tempfile
import logging

from fuelbench import config_manager
from fuelbench import utils
from fuelbench import remote_tasks
from fuelbench.providers import KvmProvider
from fuelbench.settings import *
from fuelbench.error import *

from fabric.api import execute
from fabric.context_managers import settings as fab_context
from fabric.context_managers import hide

logger = logging.getLogger(__name__)

class FuelBench(object):

	def __init__(self, site, provider, config=config_manager.defaults(), base_iso=None):
		self.site = site
		self.provider = provider
		self.config = config
		self.base_iso = base_iso
		self.local_workdir = os.path.join(SITE_DIR, str(self.site))

		self.iso_fuel_version = ''	
		self.master_fuel_version = ''
		self.disable_master_public = False
		#self.__generate_network_settings(site)

	def __generate_network_settings(self, site):
		self.networks = list()

		if self.master_fuel_version:
			fuel_version = self.master_fuel_version
		elif self.iso_fuel_version:
			fuel_version = self.iso_fuel_version
		else:
			fuel_version = ''
	
		admin_network_ip = self.config['admin_network_ip']
		public_network_ip = self.config['public_network_ip']

		self.admin_net_id = 0
		self.networks.append({'type': NETWORK_NAT,
							'cidr': admin_network_ip.format(site, 0) + '/24',
							'gateway': admin_network_ip.format(site, 1),
							'netmask': '255.255.255.0'})

		self.public_net_id = 1
		self.networks.append({'type': NETWORK_NAT,
							'cidr': public_network_ip.format(site, 0) + '/24',
							'gateway': public_network_ip.format(site, 1),
							'netmask': '255.255.255.0'})
		
		self.networks.append({'type': NETWORK_ISOLATED})

		self.master_ip = admin_network_ip.format(site, 2)
		self.public_master_ip = public_network_ip.format(site, 2)
		#self.public_vip = public_network_ip.format(site, 3)
		#self.public_vip = public_network_ip.format(site, 2)
		self.floating_ranges = [public_network_ip.format(site, 130), public_network_ip.format(site, 254)]
		self.public_ranges = [public_network_ip.format(site, 3), public_network_ip.format(site, 126)]

		# TODO: parse and compare fuel version
		if fuel_version in ('7.0',):
			self.public_vip = public_network_ip.format(site, 4)
		else:
			self.public_vip = public_network_ip.format(site, 3)

	def __get_admin_network(self):
		return self.networks[self.admin_net_id]
	
	def __get_public_network(self):
		return self.networks[self.public_net_id]
	
	def __get_master_ssh_context(self, show_output=False):
		config = self.config
		
		master_user = config['master_user']
		master_pass = config['master_pass']
		self.__generate_network_settings(self.site)
		master_ip = self.master_ip
		
		master_host = '{0}@{1}'.format(master_user, master_ip)
		
		if show_output:
			hide_groups = ['warnings', 'running', 'user', 'exceptions', 'aborts']
		else:
			hide_groups = ['everything', 'aborts']
		
		return fab_context(hide(*hide_groups),
					       user=master_user,
				           password=master_pass,
					       hosts=[master_host],
					       disable_known_hosts=True,
					       abort_exception=RemoteTaskError)
		
	def make_workspace(self):
		if not os.path.exists(self.local_workdir):
			os.makedirs(self.local_workdir)
	
	def check_iso(self):
		self.iso_fuel_version = utils.retrieve_iso_version(self.base_iso)
				
		fuel_version = self.iso_fuel_version
		if fuel_version not in FUEL_META_INFO.keys():
			raise ValueError('Unsupported fuel version: {0}'.format(fuel_version))

		self.__generate_network_settings(self.site)
		
	def check_master(self):
		self.master_fuel_version = self.get_fuel_version()
				
		fuel_version = self.master_fuel_version
		if fuel_version not in FUEL_META_INFO.keys():
			raise ValueError('Unsupported fuel version: {0}'.format(fuel_version))

		self.__generate_network_settings(self.site)
	
	def get_vm_nodes(self):
		provider = self.provider
		return provider.get_vm_nodes(self.site)
	
	def get_master_nodes(self):
		vm_nodes = self.get_vm_nodes()
		results = list()
		
		for vm in vm_nodes:
			if vm.endswith('-master'):
				results.append(vm)
				
		return results
	
	def get_slave_nodes(self):
		vm_nodes = self.get_vm_nodes()
		results = list()
		
		for vm in vm_nodes:
			if not vm.endswith('-master'):
				results.append(vm)
				
		return results

	def get_networks(self):
		provider = self.provider
		return provider.get_networks(self.site)
	
	def print_access_info(self, show_horizon=False):
		site = self.site
		
		config = self.config
		
		host_ip = utils.get_primary_addr()
		
		fuelssh_adm_port = config['fuelssh_adm_mapped_port'] % site
		fuelssh_pub_port = config['fuelssh_pub_mapped_port'] % site
		fuelweb_adm_port = config['fuelweb_adm_mapped_port'] % site
		fuelweb_pub_port = config['fuelweb_pub_mapped_port'] % site
		horiweb_lt7_port = config['horiweb_lt7_mapped_port'] % site
		horiweb_gt7_port = config['horiweb_gt7_mapped_port'] % site
		horissl_lt7_port = config['horissl_lt7_mapped_port'] % site
		horissl_gt7_port = config['horissl_gt7_mapped_port'] % site
		
		master_ip = self.master_ip
		public_vip = self.public_vip
		disable_master_public = self.disable_master_public
		fuel_version = self.iso_fuel_version
		
		print()
		print("Fuel Master Internal IP: {0}".format(master_ip))
		print("Fuel UI is avaliable on http://{0}:8000/".format(master_ip))			
		print()
		if show_horizon:
			print("OpenStack Virtual Internal IP: {0}".format(public_vip))
			print("Access the OpenStack dashboard (Horizon) at http://{0}/".format(public_vip))	
			print()
			
		if disable_master_public:
			print("External Fuel Web Link: http://{0}:{1}/".format(host_ip, fuelweb_adm_port))
			print("SSH to Fuel Master: {0} on port {1}".format(host_ip, fuelssh_adm_port))
		else:
			print("External Fuel Web Link: http://{0}:{1}/".format(host_ip, fuelweb_pub_port))
			print("SSH to Fuel Master: {0} on port {1}".format(host_ip, fuelssh_pub_port))
		
		if show_horizon:
			logger.info("fuel version: {0}".format(fuel_version))
			#TODO: version parse
			if fuel_version in ("7.0",):
				print("External Horizon Link: https://{0}:{1}/horizon/".format(host_ip, horissl_gt7_port))
			else:
				print("External Horizon Link: http://{0}:{1}/horizon/".format(host_ip, horiweb_lt7_port))

	def create_master(self, **kwargs):
		site = self.site
		provider = self.provider
		
		config = self.config.copy()
		config.update(utils.filter_kwargs(kwargs))
		
		base_iso = self.base_iso
		fuel_version = self.iso_fuel_version
		meta_info = FUEL_META_INFO[fuel_version]
		master_os = meta_info['master']['os']
		
		vm_install_wait = config['vm_install_wait']
		search_domain = config['search_domain']
				
		admin_net = self.__get_admin_network()
		admin_cidr = admin_net['cidr']
		admin_gw = admin_net['gateway']
		admin_mask = admin_net['netmask']
		public_net = self.__get_public_network()
		public_net_id = self.public_net_id
		public_cidr = public_net['cidr']
		public_gw = public_net['gateway']
		public_mask = public_net['netmask']		
		
		master_ip = self.master_ip
		public_ip = self.public_master_ip
		master_hostname = config['master_hostname']
		master_name = config['master_name']
		master_user = config['master_user']
		master_pass = config['master_pass']
		master_prompt = config['master_prompt']
		master_cpu = config['master_cpu']
		master_ram = config['master_ram']
		master_disk = config['master_disk']
		
		disable_public = config['disable_public']
		disable_snapshot = config['disable_snapshot']
		
		iso_image = None

		try:
			print('Cleaning up... ', end='')
			sys.stdout.flush()
			provider.clean_vm_nodes(site)
			provider.clean_networks(site)
			print('OK')
	
			print('Creating virtual networks... ', end='')
			sys.stdout.flush()
			network_list = provider.create_networks(site, self.networks)
			print('OK')
	
			print('Making the custom ISO image... ', end='')
			sys.stdout.flush()
			iso_image = utils.make_custom_iso_image(base_iso, site,
													data_dir=IMAGE_DIR,
													ipaddr=master_ip,
													gateway=admin_gw,
													dns=admin_gw,
													netmask=admin_mask,
													hostname=master_hostname)
			print('OK')
	
			print('Installing Fuel Master node... ', end='')
			sys.stdout.flush()
			provider.install_vm_node(site, master_name,
									vcpus=master_cpu, ram=master_ram,
									iso_image=iso_image,
									disk_size=master_disk,
									networks=network_list,
									os_variant=master_os,
									wait=vm_install_wait,
									delete_media=True)
			print('OK')
			
			self.wait_for_product_vm(45*60)
			
			self.disable_master_public = disable_public
			if not disable_public:
				print('Enabling outbound network/internet access for the product VM... ', end='')
				sys.stdout.flush()
				self.run_remote_script(ENABLE_VM_NETWORK_SCRIPT, 
									public_net_id, public_ip, public_mask, 
									public_gw, public_gw, search_domain,
									public_cidr)
				print('OK')
			
			print('Setting up Fuel Master VM... ', end='')
			sys.stdout.flush()	
			self.run_remote_script(SETUP_FUEL_SCRIPT)
			print('OK')
			
			if not disable_snapshot:
				self.shutdown_master()
				print('Creating snapshot for Fuel Master recovery... ', end='')
				sys.stdout.flush()	
				provider.create_vm_snapshot(site, master_name, 'fuel_recovery', 'snapshot for fuel recovery')
				print('OK')
				self.start_master()
				self.wait_for_product_vm()			
			
		finally:
			if iso_image and os.path.exists(iso_image):
				try:
					os.remove(iso_image)
				except Exception, e:
					print(str(e))
					print('Warning: ISO image {0} still exists!'.format(iso_image))
					
	def create_slave(self, **kwargs):
		site = self.site
		provider = self.provider
		
		fuel_version = self.master_fuel_version
		current_release = self.current_release
		meta_info = FUEL_META_INFO[fuel_version]
		slave_os = meta_info['releases'][current_release]['os']
		
		config = self.config.copy()
		config.update(utils.filter_kwargs(kwargs))
		
		slave_cpu = config['slave_cpu']
		slave_ram = config['slave_ram']
		slave_disk = config['slave_disk']
		
		node_id = provider.get_max_node_id(site) + 1
		node_name = 'node-' + str(node_id)
		
		network_list = provider.get_networks(site)
		
		try:
			print('Creating {0} on site {1}... '.format(node_name, site), end='')
			sys.stdout.flush()
			provider.install_vm_node(site, node_name, slave_cpu, slave_ram,
									boot='pxe',
									disk_size=slave_disk,
									networks=network_list,
									os_variant=slave_os,
									persistent_boot=True)
			print('OK')			
		finally:
			pass
							
	def clean(self):
		site = self.site
		provider = self.provider

		print('Cleaning up... ', end='')
		sys.stdout.flush()
		provider.clean_vm_nodes(site)
		provider.clean_networks(site)
		print('OK')
		
	def clean_slaves(self):
		site = self.site
		provider = self.provider

		print('Removing slave nodes... ', end='')
		sys.stdout.flush()
		provider.clean_slave_nodes(site)
		print('OK')
		
	def get_all_fuel_nodes(self):
		fuel_nodes = list()
		
		with self.__get_master_ssh_context():
			results = execute(remote_tasks.get_all_fuel_nodes)
			
		for item in results.values():
			fuel_nodes.extend(item)
			
		return fuel_nodes
	
	def get_pending_fuel_nodes(self):
		pending_nodes = list()
		all_nodes = self.get_all_fuel_nodes()
		
		for node in all_nodes:
			if node['status'] == 'discover':
				pending_nodes.append(node)
				
		return pending_nodes			
	
	def create_fuel_env(self, name=None, release='ubuntu', deploy_mode='ha', network_mode='neutron-vlan'):
		self.make_workspace()
		
		fuel_version = self.master_fuel_version
		meta_info = FUEL_META_INFO[fuel_version]
		release_id = meta_info['releases'][release]['id']
		
		public_vip = self.public_vip
		floating_ranges = self.floating_ranges
		public_ranges = self.public_ranges
		public_net = self.__get_public_network()
		public_cidr = public_net['cidr']
		public_gateway = public_net['gateway']
		
		if not name:
			name = 'OpenStack Lab {0}'.format(self.site)
		
		with self.__get_master_ssh_context():
			results = execute(remote_tasks.create_fuel_env, 
							name=name, 
							release=release_id, 
							mode=deploy_mode, 
							network=network_mode)
  			
			if len(results) > 0:
				id = results.values()[0]
			else:
				raise FuelServerError('Environment not found')
			
			results = execute(remote_tasks.configure_fuel_env, id=id, workdir=self.local_workdir, 
							public_vip=public_vip, floating_ranges=floating_ranges, 
							public_cidr=public_cidr, public_gateway=public_gateway, public_ranges=public_ranges,
							upstream_dns=public_gateway)

		self.current_env_name = name
		self.current_env_id = id
		self.current_release = release
					
		return (name, id)
	
	def get_fuel_env(self):
		fuel_env = list()
		
		with self.__get_master_ssh_context():
			results = execute(remote_tasks.get_all_fuel_env)
			
		for item in results.values():
			fuel_env.extend(item)
			
		return fuel_env
	
	def get_fuel_version(self):
		with self.__get_master_ssh_context():
			results = execute(remote_tasks.get_fuel_version)
			
		for item in results.values():
			return item
			
		return None
	
	def run_remote_script(self, script, *args):
		with self.__get_master_ssh_context():
			execute(remote_tasks.run_remote_script,
				local_script=script,
				args=args)
	
	def add_fuel_nodes(self, node_ids, roles):
		self.make_workspace()
		
		env_id = self.current_env_id
		admin_net = self.__get_admin_network()
		admin_gateway = admin_net['gateway']
		
		if len(node_ids) == 0:
			return
		
		with self.__get_master_ssh_context():
			execute(remote_tasks.set_fuel_node_roles,
				env_id=env_id,
				node_ids=node_ids,
				node_roles=roles)
			
			for node_id in node_ids:
				execute(remote_tasks.configure_fuel_node,
					node_id=node_id,
					workdir=self.local_workdir,
					env_id=env_id,
					admin_gw=admin_gateway)
			
		print("Nodes {node_ids} with roles {node_roles} were added to environment {env_id}".format(env_id=env_id,
																								node_ids=str(node_ids),
																								node_roles=str(roles)))

	def deploy_changes(self):
		env_id = self.current_env_id
		
		print('Deploying changes to environment... ', end='')
		sys.stdout.flush()
		
		with self.__get_master_ssh_context():
			execute(remote_tasks.fuel_deploy_changes,
				env_id=env_id)
			
		print('done')
				
	def wait_for_product_vm(self, timeout=5*60):
		current = start = time.time()
		is_operational = False
		
		print('Waiting for product VM operational... ', end='')
		sys.stdout.flush()
			
		while (current - start) < timeout:
			
			try:
				with self.__get_master_ssh_context():
					results = execute(remote_tasks.check_vm_operational)
					
				if len(results) > 0 and all(item == True for item in results.values()):
					is_operational = True
					break
			except RemoteTaskError as e:
				logger.warn(e)
				
			current = time.time()
			time.sleep(5)
			
		if is_operational:
			print('OK')
			return True
		else:
			print('timeout')
			raise FuelServerError('Wait for product VM timeout')
		
	def wait_for_fuel_server(self, timeout=15*60):
		current = start = time.time()
		is_ready = False
		
		print('Waiting for Fuel server ready... ', end='')
		sys.stdout.flush()
			
		while (current - start) < timeout:
			
			is_ready = self.is_fuel_server_ready()
			
			if is_ready:
				break
				
			current = time.time()
			time.sleep(20)
			
		if is_ready:
			print('OK')
			return True
		else:
			print('timeout')
			raise FuelServerError('Wait for fuel server timeout')
		
	def is_fuel_server_ready(self):
		is_ready = False
		
		try:
			with self.__get_master_ssh_context():
				results = execute(remote_tasks.get_all_fuel_env)
					
			if len(results) > 0:
				is_ready = True
				
		except RemoteTaskError as e:
			logger.warn(e)
			
		return is_ready
		
	def shutdown_master(self, timeout=5*60):
		config = self.config
		provider = self.provider
		site = self.site
		
		master_name = config['master_name']
		
		if not provider.check_vm_node_active(site, master_name):
			return
		
		print('Shutting down fuel master.', end='')
		sys.stdout.flush()
		
		with self.__get_master_ssh_context():
			execute(remote_tasks.power_off)
			
		current = start = time.time()
		is_active = True
		
		while (current - start) < timeout:
			print('.', end='')
			sys.stdout.flush()
			
			is_active = provider.check_vm_node_active(site, master_name)
			
			if is_active == False:
				break
				
			current = time.time()
			time.sleep(5)
			
		if is_active == False:
			print(' OK')
			return True
		else:
			print(' timeout')
			raise FuelServerError('Shutdown fuel master timeout')
	
	def start_master(self):
		config = self.config
		provider = self.provider
		site = self.site
		
		master_name = config['master_name']
		
		print('Starting fuel master... ', end='')
		sys.stdout.flush()
		
		is_active = provider.check_vm_node_active(site, master_name)
		if is_active == False:
			provider.start_vm_node(site, master_name)
		
		print('OK')		
	
	def restore_master(self):
		config = self.config
		provider = self.provider
		site = self.site
		
		master_name = config['master_name']
		
		provider.revert_vm_snapshot(site, master_name, 'fuel_recovery')
		
		self.start_master()
		self.wait_for_product_vm()		
		

def DefaultFuelBench(site, base_iso=None):
	
	config = config_manager.load()	
	provider = KvmProvider()
	
	if base_iso is None:
		return FuelBench(site, provider, config)
	else:
		return FuelBench(site, provider, config, base_iso)

