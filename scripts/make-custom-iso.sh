#!/bin/bash

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


SOURCE_IMG=$1
CUSTOM_IMG=$2
IMAGE_DIR=$3
IP=$4
GATEWAY=$5
DNS=$6
NETMASK=$7
HOSTNAME=$8

rm -f $CUSTOM_IMG
rm -rf $IMAGE_DIR
mkdir -p $IMAGE_DIR

VOL_LABEL=`isoinfo -d -i $SOURCE_IMG | awk -F':' '/^Volume id:/ {print $2}' | sed -e 's/^[ \t]*//'`

bsdtar -xpf "$SOURCE_IMG" -C "$IMAGE_DIR"
chmod -R u+rw $IMAGE_DIR

ISOLINUX_CFG=$IMAGE_DIR/isolinux/isolinux.cfg

sed -i "s/timeout 300/timeout 30/g" $ISOLINUX_CFG
sed -i "s/ip=10.20.0.2/ip=${IP}/g" $ISOLINUX_CFG
sed -i "s/gw=10.20.0.1/gw=${GATEWAY}/g" $ISOLINUX_CFG
sed -i "s/dns1=10.20.0.1/dns1=${DNS}/g" $ISOLINUX_CFG
sed -i "s/netmask=255.255.255.0/netmask=${NETMASK}/g" $ISOLINUX_CFG
sed -i "s/hostname=fuel.domain.tld/hostname=${HOSTNAME}/g" $ISOLINUX_CFG
sed -i "s/showmenu=yes/showmenu=no/g" $ISOLINUX_CFG

cd $IMAGE_DIR
rm -rf '[BOOT]'

mkisofs -o $CUSTOM_IMG -V "$VOL_LABEL" -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -quiet -J -r $IMAGE_DIR
isohybrid $CUSTOM_IMG
implantisomd5 $CUSTOM_IMG

rm -rf $IMAGE_DIR
chmod a+r $CUSTOM_IMG

