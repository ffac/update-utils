#! /usr/env/python3
# requires requests, dnspython
import os
from itertools import islice

import requests
from dns.tsigkeyring import from_text
from dns.update import Update
from dns.query import tcp


def batched(iterable, n):
    # if python >= 3.12:
    # from itertools import batched
    # https://docs.python.org/3/library/itertools.html#itertools.batched
    # batched('ABCDEFG', 3) → ABC DEF G
    if n < 1:
        raise ValueError("n must be at least one")
    it = iter(iterable)
    while batch := tuple(islice(it, n)):
        yield batch


dns_server = "8.8.8.8"
zone = "nodes.ffac.rocks"
key_name = "nodes.ffac.rocks."
key_secret = os.getenv("SECRET_KEY", "")
key_algorithm = "hmac-sha512"
keyring = from_text({key_name: key_secret})
url = "https://map.aachen.freifunk.net/data/nodes.json"

t = requests.get(url)
t.raise_for_status()
nodes = t.json()["nodes"]

# Parse the key data and create a TSIG keyring
pairs = []
for node in nodes:
    nodeinfo = node["nodeinfo"]
    addrs = nodeinfo["network"]["addresses"]
    addrs = list(filter(lambda x: not x.startswith("f"), addrs))
    host = nodeinfo["hostname"]
    replacements = ["`", "´", ".", " "]
    for rep in replacements:
        host = host.replace(rep, "-")
    host = host.encode("idna").decode()

    pairs.append((host, addrs))

# nsupdate can only handle 400 requests at once
n = 400
# pairs = sorted(filter(lambda x: "herrengarten" in x[0],pairs))
for batch in batched(sorted(pairs), n):
    update = Update(zone, keyring=keyring)
    for host, addrs in batch:
        dns_name = f"{host}.{zone}"
        update.replace(dns_name, 300, "AAAA", addrs[0])
    response = tcp(update, dns_server)
    print(response)



# for batch in batched(sorted(pairs), n):
#     update = Update(zone, keyring=keyring)
#     for host, addrs in batch:
#         dns_name = f"{host}.{zone}"

#         import dns
#         rdataset = dns.rdataset.Rdataset(dns.rdataclass.IN, dns.rdatatype.AAAA, ttl=300)
        
#         #for addr in addrs:
#         rdata = dns.rdata.from_text(dns.rdataclass.IN, dns.rdatatype.AAAA, addrs[0])
#         rdataset.add(rdata)
#         #if dns_name in list(map(lambda x: str(x.name), update.update)):
#             #update.replace(dns_name, 300, "AAAA", addr)
#         #else:
#         update.delete(dns_name, rdataset)

#         ### alternative 2
#         if dns_name in list(map(lambda x: str(x.name), update.update)):
#             pass
#             #update.replace(dns_name, 300, "AAAA", addr)
#         else:
#             update.replace(dns_name, 300, "AAAA", addrs[0])