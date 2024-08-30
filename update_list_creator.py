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
with open("state.json") as f:
    d = json.load(f)

update_nodes = {}

for node, info in d["nodes"].items():
    connected = info["statistics"]["clients"]["total"]
    release = info["nodeinfo"]["software"]["firmware"].get("release")
    addresses = info["nodeinfo"]["network"]["addresses"]
    raw_address = list(filter(lambda x: x.startswith("2a03"), addresses))
    hostname = info["nodeinfo"]["hostname"]
    if raw_address:
        address = raw_address[0]
    else:
        print(f"no public ipv6 for {hostname}")
        address = addresses[0]
    # of course, only online nodes are updated

    if not info["online"]:
        continue

    autoupdater_settings = info["nodeinfo"]["software"].get("autoupdater", {})
    autoupdater = autoupdater_settings.get("enabled", False)
    if not autoupdater:
        continue

    # if not "2a03:2260:3006" in address:
    if "2a03:2260:3006:" not in address:
        # filter for a segment/domain here
        continue

    if "UBNT-ERX" in info["nodeinfo"]["hardware"]["model"]:
        # Don't upgrade ERX due to this issue
        # https://github.com/oszilloskop/UBNT_ERX_Gluon_Factory-Image/blob/master/ERX-Sysupgrade-Problem.md
        continue

    # filter for a release
    if release and "202" in release:
        continue
    # only specific update branches?
    if autoupdater_settings["branch"] != "stable":
        continue

    try:
        meshifs = info["nodeinfo"]["network"]["mesh"]["bat0"]["interfaces"]
        macs = []
        for mesh_macs in meshifs.values():
            macs.extend(mesh_macs)
        update_nodes[tuple(macs)] = (address, node, hostname)
    except KeyError as e:
        # supernodes throw errors here if bat0 does not exist
        print(f"KeyError: {e} for {node}")

# sets allow values only once
nexthops = set()
leafs = set()

for node, info in d["nodes"].items():
    is_leaf = False
    gateway_nexthop = info["statistics"].get("gateway_nexthop")
    if not gateway_nexthop:
        # if we do not have a nexthop - assume we are a leaf
        is_leaf = True

    try:
        vpn_values = info["statistics"]["mesh_vpn"]["groups"]["backbone"][
            "peers"
        ].values()
        if not any(vpn_values):
            # if we did not establish a vpn connection, we are a leaf
            is_leaf = True
    except KeyError:
        # if we do not have mesh_vpn active, we are a leaf too
        is_leaf = True

    for macs in update_nodes.keys():
        if gateway_nexthop in macs:
            # add the nexthop to our nexthop list to remove it afterwards
            nexthops |= {macs}
            is_leaf = True
            break
    if is_leaf:
        # calculate our mac to move ourselves to the leafs list
        try:
            meshifs = info["nodeinfo"]["network"]["mesh"]["bat0"]["interfaces"]
            leaf_macs = []
            for mesh_macs in meshifs.values():
                leaf_macs.extend(mesh_macs)
            leafs |= {tuple(leaf_macs)}
        except KeyError as e:
            # supernodes throw errors here if bat0 does not exist
            if not "'bat0'" == str(e):
                print(f"KeyError: {e} for {node}")

# move leafs and offloaders to other lists
update_offloaders = {}
for nexthop_macs in nexthops:
    # move entry to update_leafs map
    if nexthop_macs in update_nodes:
        update_offloaders[nexthop_macs] = update_nodes.pop(nexthop_macs)

update_leafs = {}
for leaf_macs in leafs:
    # move entry to update_leafs map
    if leaf_macs in update_nodes:
        update_leafs[leaf_macs] = update_nodes.pop(leaf_macs)

outputs = []

# we are left with single nodes with own uplink
# which only have mesh partners, which do not rely on them
with open("update_hosts.txt", "w") as f:
    for macs, tuples in update_nodes.items():
        address, node, hostname = tuples
        f.write(
            f"allow {address}; # https://map.aachen.freifunk.net/#!/en/map/{node} - {hostname}\n"
        )

# write other lists too, so that we can verify them
# or use them later
with open("update_leafs.txt", "w") as f:
    for macs, tuples in update_leafs.items():
        address, node, hostname = tuples
        f.write(
            f"allow {address}; # https://map.aachen.freifunk.net/#!/en/map/{node} - {hostname}\n"
        )


with open("update_offloaders.txt", "w") as f:
    for macs, tuples in update_offloaders.items():
        address, node, hostname = tuples
        f.write(
            f"allow {address}; # https://map.aachen.freifunk.net/#!/en/map/{node} - {hostname}\n"
        )

whole_list = update_nodes | update_offloaders | update_leafs
with open("update_all.txt", "w") as f:
    for macs, tuples in sorted(whole_list.items(), key=lambda x: x[1][2]):
        address, node, hostname = tuples
        f.write(
            f"allow {address}; # https://map.aachen.freifunk.net/#!/en/map/{node} - {hostname}\n"
        )
