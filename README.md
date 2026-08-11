<!--
SPDX-License-Identifier: BSD-2-Clause
-->
#  update-utils

This repository contains some scripts used for the operation of Freifunk Aachen.

## allow updates allowance 

The `update_list_creator.py` script helps to migrate multiple nodes.
It is very FFAC specific in a way that it requires:

* one single update server which is requested by all nodes
* this update server determines by the requesting client ipv6 in the mesh, if a node is eligible for an update
* nodes need to be selected based on their leaves or offloader role in the mesh

If this is also what you need to do.
This might help you with some adjustments.


## Mail Sending Usage

To use this one can adjust the filters in `contact_list_creator.py` to your needs, which will create two lists - one for addresses which are only existing as contact in a single device - and one for addresses referenced in multiple devices.

These two jsons can then be adjusted manually if needed or looked through.

A third json `local_addresses.json` is created containing all contact entries which do no look like a mail address.
These might be phone numbers, plain text or nicknames.

Finally, you can use `contact_list_sender.py` and adjust the message text to your needs.
Which is used to send messages to the participants of your list.

### Usage

```
git clone $this_repo
scp ffac-monitor:/var/lib/yanic/state.json .
python contact_list_creator.py

# check resulting json files - adjust or inspect

# fill in relevant SMTP secrets in .env
export $(cat .env | xargs)
python contact_list_sender.py
```

Eventually, you need to do this from a priviliged IP address to avoid the mailcow SMTP ratelimit.

## nameserver update script

1. update the UPDATENS_KEY_SECRET (and others) in the .env file and load it using `export $(cat .env | xargs)`
2. run the `updatens.py` script

You can also run this hourly as a cron job like this:
`7 * * * * cd /home/ffac/nsupdater && export $(cat .env | xargs) && python3 updatens.py`
