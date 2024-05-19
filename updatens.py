#! /usr/env/python3
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

zone = "nodes.ffac.rocks."
# url from which the current state is crawled
url = "https://map.aachen.freifunk.net/data/nodes.json"

DEBUG = False

key_secret = os.getenv("ZONE_SECRET_KEY", "")
assert len(key_secret) > 10
key_algorithm = "hmac-sha512"
# Parse the key data and create a TSIG keyring
KEYRING = dns.tsig.Key(zone, key_secret, key_algorithm)

# nsupdate can only handle 300-400 requests at once
# so we are running in batches of 300
BATCH_SIZE = 400


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

    pairs = []
    for node in nodes:
        nodeinfo = node["nodeinfo"]
        addrs = nodeinfo["network"]["addresses"]
        addrs = list(filter(lambda x: not x.startswith("f"), addrs))
        host = nodeinfo["hostname"]
        replacements = ["`", "´", ".", " ", "#", "_", "'", "+", "&"]
        for rep in replacements:
            host = host.replace(rep, "-")
        host = host.strip("-")
        host = host.encode("idna").decode().lower()

        pairs.append((host, addrs))

    return list(sorted(pairs))


def crawl_stat_from_xfr(host_ip: str, zone: str) -> list[dict[str, list[str]]]:
    zone_entries = list(dns.query.xfr(host_ip, zone))
    current_entries = {}
    for dns_message in zone_entries:
        # dns_message has 4 sections
        # second section contains dns names, others are irrelevant
        filt = filter(lambda e: e.rdtype == dns.rdatatype.AAAA, dns_message.sections[1])
        for entry in filt:
            current_entries[str(entry.name)] = list(
                map(lambda x: str(x), entry.items.keys())
            )
    return current_entries


def replace_changed_entries(
    changed_pairs: list[dict[str, list[str]]],
    zone: str,
    host_ip: str,
):
    try:
        for batch in batched(changed_pairs, BATCH_SIZE):
            update = dns.update.Update(zone, keyring=KEYRING)
            for host, addrs in batch:
                dns_name = f"{host}.{zone}"
                # to add multiple for a single host, we need this Rdataset type
                # otherwise this would also work:
                # update.replace(dns_name, 300, "AAAA", addr[0])
                if addrs:
                    rdataset = dns.rdataset.Rdataset(
                        dns.rdataclass.IN, dns.rdatatype.AAAA, ttl=300
                    )
                    for addr in addrs:
                        rdata = dns.rdata.from_text(
                            dns.rdataclass.IN, dns.rdatatype.AAAA, addr
                        )
                        rdataset.add(rdata)
                    update.add(dns_name, rdataset)
            response = dns.query.tcp(update, host_ip)
            if response.rcode() > 0:
                print("error in ", update, response)
    except dns.exception.TooBig:
        print(f"dns message is too big with {len(update.index)}")


def delete_leftover_hosts(to_remove: list, zone: str, dns_server: str):
    try:
        for batch in batched(to_remove, BATCH_SIZE):
            update = dns.update.Update(zone, keyring=KEYRING)
            for host, _ in batch:
                dns_name = f"{host}.{zone}"
                update.delete(dns_name, dns.rdatatype.AAAA)
            response = dns.query.tcp(update, dns_server)
            print(response)
    except dns.exception.TooBig:
        print(f"dns message is too big with {len(update.index)}")


if __name__ == "__main__":
    # resolve the IP of the AXFR target dynamically by reading the SOA record
    resolver = dns.resolver.Resolver()
    try:
        soa_answer = resolver.resolve(zone, dns.rdatatype.SOA)
        host_ip = str(socket.gethostbyname(str(soa_answer[0].mname)))
    except Exception as e:
        print(f"error: {e}")
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
            current_addrs = entries.pop(host)
        except KeyError:
            current_addrs = [None]

        # if the addresses are not as expected - we need to replace them
        if sorted(addrs) != sorted(current_addrs):
            to_replace.append((host, addrs))

    to_remove = []
    # we can now add the leftovers to our remove list
    for host, addrs in entries.items():
        to_remove.append((host, addrs))
    # to_remove now only contains entries which are not valid anymore

    if DEBUG:
        import json

        print("anzahl einträge", len(current_entries))

        with open("current_entries.json", "w") as f:
            json.dump(current_entries, f, indent=4)

        with open("to_replace.json", "w") as f:
            json.dump(to_replace, f, indent=4)

        with open("to_remove.json", "w") as f:
            json.dump(to_remove, f, indent=4)
    else:
        replace_changed_entries(to_replace, zone, host_ip)
        delete_leftover_hosts(to_remove, zone, host_ip)
