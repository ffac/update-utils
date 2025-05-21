#! /usr/bin/env python3
# requires requests, dnspython
import os
import socket
from itertools import islice

import dns
import dns.query
import dns.resolver
import dns.tsigkeyring
import dns.update
import requests
import logging

###
### Takes the following environment variables into account
###
#
# UPDATENS_XFR_USE_AUTH=0
# whether to use tsig authentication for zone transfers, too. update actions are always authenticated by tsig.
#
# UPDATENS_BATCH_SIZE=400
# the message size of a dns update might be limited.
#
# UPDATENS_ZONE=nodes.ffac.rocks.
# the (sub)domain used for the dns updates. usually ends in "."
#
# UPDATENS_NODES_URL=https://map.aachen.freifunk.net/data/nodes.json
# location of the nodes.json where the data is taken from.
#
# UPDATENS_TARGET=SOA
# the fqdn of the dns server which will be queried. if none is given the SOA from the zone is asked.
#
# UPDATENS_KEY_NAME=
# the key name for the tsig. defaults to the value from UPDATENS_ZONE.
#
# UPDATENS_KEY_ALGO=hmac-sha512
# the key algorithm used with tsig.
#
# UPDATENS_KEY_SECRET=
# the secret used with tsig.
#
# UPDATENS_FILTER_ADDR=f
# filter out ip addresses from the nodes.json. the filter expression is applied with "startswith".
#
# UPDATENS_FILTER_INVERT=1
# the filter expression is inverted with a not. in combination with the default filter addr every
# address starting with "f" will not be transferred to the dns.
#
# UPDATENS_NOOP=0
# UPDATENS_DEBUG=0

zone = os.getenv("UPDATENS_ZONE", "nodes.ffac.rocks.")
# url from which the current state is crawled
url = os.getenv("UPDATENS_NODES_URL", "https://map.aachen.freifunk.net/data/nodes.json")

key_secret = os.getenv("UPDATENS_KEY_SECRET", os.getenv("ZONE_SECRET_KEY", ""))
assert len(key_secret) > 10
key_algorithm = os.getenv("UPDATENS_KEY_ALGO", "hmac-sha512")
key_name = os.getenv("UPDATENS_KEY_NAME", zone)
# Parse the key data and create a TSIG keyring
KEYRING = dns.tsig.Key(key_name, key_secret, key_algorithm)

# nsupdate can only handle 300-400 requests at once
# so we are running in batches of 300
BATCH_SIZE = int(os.getenv("UPDATENS_BATCH_SIZE", "400"))


def is_idna_compliant(string):
    try:
        string.encode("idna")
        return True
    except Exception:
        return False


def to_idna_conform(string):
    # Filter out non-IDNA compliant characters
    cleaned_string = "".join(char for char in string if is_idna_compliant(char))
    # Encode to IDNA
    return cleaned_string.encode("idna").decode("utf-8")


def batched(iterable: list, n: int) -> list:
    # if python >= 3.12:
    # from itertools import batched
    # https://docs.python.org/3/library/itertools.html#itertools.batched
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


def crawl_pairs_from_map(url: str) -> list[tuple[str, str]]:
    t = requests.get(url)
    t.raise_for_status()
    nodes = t.json()["nodes"]

    addr_filter = os.getenv("UPDATENS_FILTER_ADDR", "f")
    addr_filter_invert = True if os.getenv("UPDATENS_FILTER_INVERT", "1") else False

    pairs = []
    for node in nodes:
        nodeinfo = node["nodeinfo"]
        addrs = nodeinfo["network"]["addresses"]
        if addr_filter_invert:
            addrs = list(filter(lambda x: not x.startswith(addr_filter), addrs))
        else:
            addrs = list(filter(lambda x: x.startswith(addr_filter), addrs))
        host = nodeinfo["hostname"].strip()
        replacements = ["`", "´", ".", " ", "#", "_", "'", "+", "&", "/"]
        for rep in replacements:
            host = host.replace(rep, "-")
        host = host.strip("-").lower()
        host = to_idna_conform(host)
        pairs.append((host, addrs))

    return list(sorted(pairs))


def crawl_stat_from_xfr(host_ip: str, zone: str) -> dict[str, list[str]]:
    if os.getenv("UPDATENS_XFR_USE_AUTH", "0") == "1":
        zone_entries = list(dns.query.xfr(host_ip, zone, keyring=KEYRING))
    else:
        zone_entries = list(dns.query.xfr(host_ip, zone))
    current_entries: dict[str, list[str]] = {}
    for dns_message in zone_entries:
        # dns_message has 4 sections
        # second section contains dns names, others are irrelevant
        filt = filter(lambda e: e.rdtype == dns.rdatatype.AAAA, dns_message.sections[1])
        for entry in filt:
            host = str(entry.name).lower()
            keys = list(map(lambda x: str(x), entry.items.keys()))
            if host in current_entries.keys():
                current_entries[host].extend(keys)
            else:
                current_entries[host] = keys
    return current_entries


def replace_changed_entries(
    changed_pairs: list[dict[str, list[str]]],
    zone: str,
    host_ip: str,
):
    try:
        for batch in batched(changed_pairs, BATCH_SIZE):
            update = dns.update.Update(zone, keyring=KEYRING)
            delete = dns.update.Update(zone, keyring=KEYRING)
            for host, addrs in batch:
                dns_name = f"{host}.{zone}"
                # to add multiple for a single host, we need this Rdataset type
                # otherwise this would also work:
                # update.replace(dns_name, 300, "AAAA", addr[0])
                if addrs and host:
                    rdataset = dns.rdataset.Rdataset(
                        dns.rdataclass.IN, dns.rdatatype.AAAA, ttl=300
                    )
                    for addr in addrs:
                        rdata = dns.rdata.from_text(
                            dns.rdataclass.IN, dns.rdatatype.AAAA, addr
                        )
                        rdataset.add(rdata)
                    delete.delete(dns_name)
                    update.add(dns_name, rdataset)
            response = dns.query.tcp(delete, host_ip)
            if response.rcode() > 0:
                logging.error(f"error in replace_changed - {update} {response} - for {delete}")
            response = dns.query.tcp(update, host_ip)
            if response.rcode() > 0:
                logging.error(f"error in {update} {response}")
    except dns.exception.TooBig:
        logging.error(f"dns message is too big with {len(update.index)}")
    except Exception:
        logging.error("something went wrong")
        logging.error(batch)
        raise

def delete_leftover_hosts(to_remove: list, zone: str, dns_server: str):
    try:
        for batch in batched(to_remove, BATCH_SIZE):
            update = dns.update.Update(zone, keyring=KEYRING)
            for host, _ in batch:
                dns_name = f"{host}.{zone}"
                update.delete(dns_name, dns.rdatatype.AAAA)
            response = dns.query.tcp(update, dns_server)
            if response.rcode() > 0:
                logging.error(f"error in delete_leftover - {update} {response} - for {update}")
    except dns.exception.TooBig:
        logging.error(f"dns message is too big with {len(update.index)}")


if __name__ == "__main__":
    DEBUG = True if os.getenv("UPDATENS_DEBUG", "0") == "1" else False
    NOOP = True if os.getenv("UPDATENS_NOOP", "0") == "1" else False
    logging.basicConfig(level="INFO" if DEBUG else None)
    # resolve the IP of the AXFR target dynamically by reading the SOA record
    resolver = dns.resolver.Resolver()
    try:
        target_env = os.getenv("UPDATENS_TARGET", "SOA")
        if target_env == "SOA":
          soa_answer = resolver.resolve(zone, dns.rdatatype.SOA)
          host_ip = str(socket.gethostbyname(str(soa_answer[0].mname)))
        else:
          host_ip = str(socket.gethostbyname(str(target_env)))
    except Exception as e:
        logging.error(f"error: {e}")
        exit(1)
    # xfr is only allowed coming from the monitor or DNS host
    pairs = crawl_pairs_from_map(url)
    current_entries = crawl_stat_from_xfr(host_ip, zone)
    # gives TransferError: Zone transfer error: REFUSED
    # if sent from IP address which is not eligible

    # now copy the current_entries and check which are still as needed
    entries = current_entries.copy()
    to_replace = []
    for host, addrs in pairs:
        try:
            # in any case, remove the entry, so that everything else can be deleted
            current_addrs = entries.pop(host.lower())
        except KeyError:
            current_addrs = [None]

        # if the addresses are not as expected - we need to replace them
        if sorted(addrs) != sorted(current_addrs):
            to_replace.append((host.encode("utf-8").decode("utf-8"), addrs))

    to_remove = []
    # we can now add the leftovers to our remove list
    for host, addrs in entries.items():
        to_remove.append((host, addrs))
    # to_remove now only contains entries which are not valid anymore

    logging.info(f"current entries {len(current_entries)}")
    logging.info(f"changing entries {len(to_replace)}")
    logging.info(f"deleting {len(to_remove)}")
    if NOOP:
        import json

        with open("current_entries.json", "w") as f:
            json.dump(current_entries, f, indent=4)
        with open("current_entries_map.json", "w") as f:
            json.dump(pairs, f, indent=4)

        with open("to_replace.json", "w") as f:
            json.dump(to_replace, f, indent=4)

        with open("to_remove.json", "w") as f:
            json.dump(to_remove, f, indent=4)
    else:
        replace_changed_entries(to_replace, zone, host_ip)
        delete_leftover_hosts(to_remove, zone, host_ip)
