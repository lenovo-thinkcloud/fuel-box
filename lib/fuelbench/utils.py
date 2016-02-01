
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
#            Xiang Yang <xiangyang1@lenovo.com>

from __future__ import print_function

import sys
import os
import tempfile
import subprocess
import netifaces
import yaml

from fuelbench.settings import *

def make_custom_iso_image(source, site, data_dir,
						  ipaddr, gateway, dns, netmask, hostname):
	iso_name = 'site{0}-custom'.format(site)
	image_dir = os.path.join(data_dir, iso_name)
	iso_file = tempfile.mkstemp(suffix='.iso', prefix=iso_name + '.')[1]

	cmdline = ' '.join([MAKE_ISO_SCRIPT,
						source, iso_file, image_dir,
						ipaddr, gateway, dns, netmask, hostname])

	retcode = subprocess.call('bash -xe ' + cmdline + ">>{0} 2>&1".format(CONSOLE_LOG), shell=True)

	if retcode != 0:
		raise RuntimeError('Script failed with exit code {0}'.format(retcode))

	return iso_file

def retrieve_iso_version(iso_file):

	version_file = os.path.join(TEMP_DIR, FUEL_VERSION_FILE)
	cmdline = 'bsdtar -xf {0} -C {1} {2}'.format(iso_file, TEMP_DIR, FUEL_VERSION_FILE)
	
	retcode = subprocess.call(cmdline + ">>{0} 2>&1".format(CONSOLE_LOG), shell=True)

	if retcode != 0:
		raise RuntimeError('Script failed with exit code {0}'.format(retcode))

	version_config=yaml.load(open(version_file))
	version = version_config['VERSION']['release']

	if os.path.exists(version_file):
		os.remove(version_file)
	
	return version

def get_primary_addr():
	devices = netifaces.interfaces()
	primary = None
	
	for dev in devices:
		info = netifaces.ifaddresses(dev)
		
		if info.has_key(netifaces.AF_INET):
			addr = info[netifaces.AF_INET][0]['addr']
			if addr and addr != '127.0.0.1':
				primary = addr
				break
	
	return primary
	
	
def getdefattr(object, name, default=None):
	value = getattr(object, name, default)
	
	if (not default is None) and (value is None):
		value = default
		
	return value

def make_list(value):
	if value is None:
		return list()
	elif isinstance(value, (list, tuple)):
		return list(value)
	else:
		return [value]
			
def filter_kwargs(old):
	kwargs = dict()
	
	for key, value in old.iteritems():
		if not value is None:
			kwargs[key] = value
			
	return kwargs

def parse_int(str):
	if str.isdigit():
		return int(str)
	else:
		return None
	
def parse_bool(str):
	if str:
		if str == 'None':
			return None
		elif str == 'True':
			return True
		else:
			return False
	else:
		return None	
	
def parse_list(str):
	result = list()
	
	for value in str.split(','):
		value = value.strip()
		
		if value:
			result.append(value)
	
	return result

def parse_eval(str):
	if not str:
		return None
	else:
		return eval(str)
	
def modify_yamlfile(file, callable, *args, **kwargs):
	with open(file, 'r') as fp:
		yaml_data = yaml.load(fp)
	
	callable(yaml_data, *args, **kwargs)
	
	with open(file, 'w') as fp:
		yaml.dump(yaml_data, fp, default_flow_style=False)
	
	return yaml_data
	
	
