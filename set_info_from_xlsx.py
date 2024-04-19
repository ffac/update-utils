#!/usr/bin/env python

# SPDX-License-Identifier: BSD-2-Clause

import json

"""
This tool helps to create nginx update lists for Freifunk migrations.
Those are needed when wanting to migrate a community efficiently by first finding all the independent nodes
Then updating the leaf nodes and finally all other nodes.
It is recommended to use ffac-scheduled-sysupgrade and ffac-autoupdater-wifi-fallback packages in the firmware to help with the migration.
"""


# take the /var/lib/yanic/state.json and open it
with open("state.json", "r") as f:
    d = json.load(f)

import pandas as pd
df = pd.read_excel("aachen.xlsx")
df.hostname = "ffsg-" +df.hostname.str[3:15]
df.index=df.hostname
df = df.drop(["cmdb_id", "hostname"], axis=1)

df_dict = df.to_dict("index")

update_nodes = {}

for node, info in d["nodes"].items():
    connected = info["statistics"]["clients"]["total"]
    release = info["nodeinfo"]["software"]["firmware"].get("release")
    hostname = info["nodeinfo"]["hostname"]

    addresses = info["nodeinfo"]["network"]["addresses"]
    raw_address = list(filter(lambda x: x.startswith("2a03"), addresses))
    if raw_address:
        address = raw_address[0]
    else:
        print(f"no public ipv6 for {hostname}")
        address = addresses[0]
    
    if df_dict.get(hostname):
        node_data = df_dict[hostname]
        lat = node_data["geoloc_lat"]
        long = node_data["geoloc_long"]
        nodename = node_data["title"]
        primary_email = node_data["primary_email"]
        print(f"ssh root@{address}")
        if isinstance(nodename, str):
            print(f"pretty-hostname {nodename}")
        print(f"uci set gluon-node-info.@owner[0]=owner; uci set gluon-node-info.@owner[0].contact='{primary_email}'")
        print(f"uci set gluon-node-info.@location[0]='location'; uci set gluon-node-info.@location[0].share_location='1';uci set gluon-node-info.@location[0].latitude='{lat}';uci set gluon-node-info.@location[0].longitude='{long}';uci commit gluon-node-info")
        print("")