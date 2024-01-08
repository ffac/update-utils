<!--
SPDX-License-Identifier: BSD-2-Clause
-->

# update-utils

This script helps to migrate multiple nodes.
It is very FFAC specific in a way that it requires:

* one single update server which is requested by all nodes
* this update server determines by the requesting client ipv6 in the mesh, if a node is eligible for an update
* nodes need to be selected based on their leaves or offloader role in the mesh

If this is also what you need to do.
This might help you with some adjustments.
