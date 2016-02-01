
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


import sys
import os

DEBUG = True

PROG_NAME = 'fuelbench'
BASE_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', '..'))
LIB_PATH = os.path.realpath(os.path.join(BASE_DIR, 'lib'))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
GUEST_DIR = os.path.join(BASE_DIR, 'guest')
ISO_DIR = os.path.join(BASE_DIR, 'iso')
CONF_DIR = os.path.join(BASE_DIR, 'conf')

DATA_DIR = os.path.expanduser('~/.fuelbench')
LOG_DIR = os.path.join(DATA_DIR, 'log')
IMAGE_DIR = os.path.join(DATA_DIR, 'iso')
TEMP_DIR = os.path.join(DATA_DIR, 'tmp')
SITE_DIR = os.path.join(DATA_DIR, 'sites')

MAKE_ISO_SCRIPT = os.path.join(SCRIPTS_DIR, 'make-custom-iso.sh')
WAIT_FOR_PRODUCT_SCRIPT = os.path.join(SCRIPTS_DIR, 'wait-for-product-vm.sh')
RUN_REMOTE_SCRIPT = os.path.join(SCRIPTS_DIR, 'run-remote-script.sh')
ENABLE_VM_NETWORK_SCRIPT = os.path.join(GUEST_DIR, 'enable-vm-outbound-network.sh')
SETUP_FUEL_SCRIPT = os.path.join(GUEST_DIR, 'setup-fuel-master.sh')

CONFIG_FILE = os.path.join(CONF_DIR, 'fuelbench.yaml')
CONSOLE_LOG = os.path.join(LOG_DIR, 'console.log')
APP_LOG = os.path.join(LOG_DIR, 'fuelbench.log')

DEFAULT_ISO = os.path.join(ISO_DIR, 'MirantisOpenStack-6.0.iso')
FUEL_VERSION_FILE = 'version.yaml'
MAX_SITE_ID = 99
SITE_LIMIT = 10
NODE_LIMIT = 10	
	
NETWORK_NAT = 'nat'
NETWORK_ISOLATED = 'isolated'

ADMIN_NETWORK_IP = '10.20.{0}.{1}'
PUBLIC_NETWORK_IP = '172.16.{0}.{1}'

VM_INSTALL_WAIT = 45
STORAGE_POOL = 'default'
SEARCH_DOMAIN = 'lenovo.com'

MASTER_NAME = 'master'
MASTER_HOSTNAME = 'fuel.localdomain'
MASTER_USER = 'root'
MASTER_PASS = 'r00tme'
MASTER_PROMPT = 'root@fuel ~]#'
MASTER_CPU = 2
MASTER_RAM = 4096
MASTER_DISK = 80

DEFAULT_CONTROLLER = 1
DEFAULT_COMPUTE = 2
DEFAULT_STORAGE = 0

CONTROLLER_CPU = 2
CONTROLLER_RAM = 4096
CONTROLLER_DISK = 80

COMPUTE_CPU = 1
COMPUTE_RAM = 2048
COMPUTE_DISK = 80

STORAGE_CPU = 1
STORAGE_RAM = 1024
STORAGE_DISK = 128

FUELSSH_ADM_MAPPED_PORT = "122%02d"
FUELSSH_PUB_MAPPED_PORT = "123%02d"
FUELWEB_ADM_MAPPED_PORT = "188%02d"
FUELWEB_PUB_MAPPED_PORT = "189%02d"
HORIWEB_LT7_MAPPED_PORT = "180%02d"
HORIWEB_GT7_MAPPED_PORT = "181%02d"
HORISSL_LT7_MAPPED_PORT = "184%02d"
HORISSL_GT7_MAPPED_PORT = "185%02d"
		
FUEL_META_INFO = {
	'6.0': {
		'master': {
			'os': 'centos6.5'},
		'releases': {
			'centos': {
				'id': 1,
				'os': 'centos6.5'},
			'ubuntu': {
				'id': 2,
				'os': 'rhel6.5'}, # workaround for bug 1147662
			}
		},
	'6.1': {
		'master': {
			'os': 'centos6.5'},
		'releases': {
			'centos': {
				'id': 1,
				'os': 'centos6.5'},
			'ubuntu': {
				'id': 2,
				'os': 'rhel7.0'}, # workaround for bug 1147662
			}
		},
	'7.0': {
		'master': {
			'os': 'centos6.5'},
		'releases': {
			'ubuntu': {
				'id': 2,
				'os': 'rhel7.0'}, # workaround for bug 1147662
			}
		},
	}
