#!/bin/bash

#    Copyright 2013 Mirantis, Inc.
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

interface_id=${1} # ethX index (0-based)
public_ip=${2}
netmask=${3}
gateway_ip=${4}
nameserver=${5}
search_domain=${6}
master_pub_net=${7}

network_file=/etc/sysconfig/network
ifcfg_file=/etc/sysconfig/network-scripts/ifcfg-eth$interface_id

# Enable internet access on inside the VMs
echo "Enabling outbound network/internet access for the product VM... "

sed -i "s/^GATEWAY=.*/GATEWAY=$gateway_ip/g" $network_file
sed -i "s/^ONBOOT=.*/ONBOOT=yes/g" $ifcfg_file
sed -i "s/^NM_CONTROLLED=.*/NM_CONTROLLED=no/g" $ifcfg_file
sed -i "s/^BOOTPROTO=.*/BOOTPROTO=static/g" $ifcfg_file
grep -q "^IPADDR=" $ifcfg_file && sed -i "s/^IPADDR=.*/IPADDR=$public_ip/g" $ifcfg_file || sed -i "$ a\\IPADDR=$public_ip" $ifcfg_file
grep -q "^NETMASK=" $ifcfg_file && sed -i "s/^NETMASK=.*/NETMASK=$netmask/g" $ifcfg_file || sed -i "$ a\\NETMASK=$netmask" $ifcfg_file
grep -q "^DNS1=" $ifcfg_file && sed -i "s/^DNS1=.*/DNS1=$nameserver/g" $ifcfg_file || sed -i "$ a\\DNS1=$nameserver" $ifcfg_file
grep -q "^DOMAIN=" $ifcfg_file && sed -i "s/^DOMAIN=.*/DOMAIN=$search_domain/g" $ifcfg_file || sed -i "$ a\\DOMAIN=$search_domain" $ifcfg_file

service network restart

