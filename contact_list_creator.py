#!/bin/python

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

from collections import defaultdict
addresses = defaultdict(list)

deprecated = [
    "A5-V11",
    "AP121",
    "AP121U",
    "D-Link DIR-615",
    "D-Link DIR-615 D",
    "AVM FRITZ!Box 7320",
    "AVM FRITZ!Box 7330",
    "AVM FRITZ!Box 7330 SL",
    "TP-Link TL-MR13U v1",
    "TP-Link TL-MR3020 v1",
    "TP-Link TL-MR3040 v1",
    "TP-Link TL-MR3040 v2",
    "TP-Link TL-MR3220 v1",
    "TP-Link TL-MR3220 v2",
    "TP-Link TL-MR3420 v1",
    "TP-Link TL-MR3420 v2",
    "TP-Link TL-WA701N/ND v1",
    "TP-Link TL-WA701N/ND v2",
    "TP-Link TL-WA730RE v1",
    "TP-Link TL-WA750RE v1",
    "TP-Link TL-WA801N/ND v1",
    "TP-Link TL-WA801N/ND v2",
    "TP-Link TL-WA801N/ND v3",
    "TP-Link TL-WA830RE v1",
    "TP-Link TL-WA830RE v2",
    "TP-Link TL-WA850RE v1",
    "TP-Link TL-WA860RE v1",
    "TP-Link TL-WA901N/ND v1",
    "TP-Link TL-WA901N/ND v2",
    "TP-Link TL-WA901N/ND v3",
    "TP-Link TL-WA901N/ND v4",
    "TP-Link TL-WA901N/ND v5",
    "TP-Link TL-WA7210N v2",
    "TP-Link TL-WA7510N v1",
    "TP-Link TL-WR703N v1",
    "TP-Link TL-WR710N v1",
    "TP-Link TL-WR710N v2",
    "TP-Link TL-WR710N v2.1",
    "TP-Link TL-WR740N/ND v1",
    "TP-Link TL-WR740N/ND v3",
    "TP-Link TL-WR740N/ND v4",
    "TP-Link TL-WR740N/ND v5",
    "TP-Link TL-WR741N/ND v1",
    "TP-Link TL-WR741N/ND v3",
    "TP-Link TL-WR741N/ND v4",
    "TP-Link TL-WR741N/ND v5",
    "TP-Link TL-WR743N/ND v1",
    "TP-Link TL-WR743N/ND v2",
    "TP-Link TL-WR840N v2",
    "TP-Link TL-WR841N/ND v3",
    "TP-Link TL-WR841N/ND v5",
    "TP-Link TL-WR841N/ND v7",
    "TP-Link TL-WR841N/ND v8",
    "TP-Link TL-WR841N/ND v9",
    "TP-Link TL-WR841N/ND v10",
    "TP-Link TL-WR841N/ND v11",
    "TP-Link TL-WR841N/ND v12",
    "TP-Link TL-WR841N/ND Mod (16M) v11",
    "TP-Link TL-WR841N/ND Mod (16M) v10",
    "TP-Link TL-WR841N/ND Mod (16M) v8",
    "TP-Link TL-WR841N/ND Mod (16M) v9",
    "TP-Link TL-WR841N/ND Mod (8M) v10",
    "TP-Link TL-WR842N/ND v1",
    "TP-Link TL-WR842N/ND v2",
    "TP-Link TL-WR843N/ND v1",
    "TP-Link TL-WR940N v1",
    "TP-Link TL-WR940N v2",
    "TP-Link TL-WR940N v3",
    "TP-Link TL-WR940N v4",
    "TP-Link TL-WR940N v5",
    "TP-Link TL-WR940N v6",
    "TP-Link TL-WR941N/ND v2",
    "TP-Link TL-WR941N/ND v3",
    "TP-Link TL-WR941N/ND v4",
    "TP-Link TL-WR941N/ND v5",
    "TP-Link TL-WR941N/ND v6",
    "TP-Link TL-WR1043N/ND v1",
    "D-Link DIR-615 D1",
    "D-Link DIR-615 D2",
    "D-Link DIR-615 D3",
    "D-Link DIR-615 D4",
    "D-Link DIR-615 H1",
    "Ubiquiti NanoStation loco M2",
    "Ubiquiti NanoStation M2",
    "Ubiquiti PicoStation M2",
    "Ubiquiti Bullet M",
    "Ubiquiti Bullet M2",
    "Ubiquiti AirRouter",
    "VoCore 8M",
    "VoCore 16M",
]

for node, info in d["nodes"].items():
    if not info["online"]:
        continue
    owner = info["nodeinfo"]["owner"]
    if not owner:
        continue
    owner = owner.get("contact")
    model = info["nodeinfo"]["hardware"].get("model")
    hostname = info["nodeinfo"]["hostname"]
    node_id = info["nodeinfo"]["node_id"]

    if model in deprecated:
        addresses[owner].append((model, hostname, node_id))
    

with open("contact_addresses.txt", "w") as f:
    with open("contact_addresses_single.txt", "w") as f_single:
        for address, old_nodes in addresses.items():
            for old_node in old_nodes:
                model, hostname, node = old_node
            if len(old_nodes) == 1:
                f_single.write(
                f"{address} \t\t# {model, hostname, node}\n"
            )
            else:
                f.write(
                    f"{address} \t\t# {old_nodes}\n"
                )
