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

# Enable internet access on inside the VMs
echo "Setting up Fuel Master VM... "

fuel_version=`awk -F': ' '/release/ {print $2}' /etc/fuel/version.yaml | sed -e 's/^["]*//' | sed -e 's/["]*$//'`


if [ $fuel_version == "6.0" ]
then
    sed -i "s/DNS_UPSTREAM:.*/DNS_UPSTREAM: $(grep '^nameserver' /etc/dnsmasq.upstream | cut -d ' ' -f2)/g" /etc/fuel/astute.yaml
else
    sed -i "s/\"DNS_UPSTREAM\":.*/\"DNS_UPSTREAM\": \"$(grep '^nameserver' /etc/dnsmasq.upstream | cut -d ' ' -f2)\"/g" /etc/fuel/astute.yaml
    sed -i "s/\"dhcp_gateway\":.*/\"dhcp_gateway\": \"$admin_gw\"/g" /etc/fuel/astute.yaml
fi

dockerctl restart nailgun
dockerctl restart nginx
cobbler sync

dockerctl restart cobbler



