import os
import re
from collections import defaultdict
from pathlib import Path

import requests
import unicodedata

# https://gist.github.com/berlotto/6295018
_slugify_strip_re = re.compile(r'[^\w\s-]')
_slugify_hyphenate_re = re.compile(r'[-\s]+')
def slugify(value):
    """
    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = _slugify_strip_re.sub('', value).strip().lower()
    return _slugify_hyphenate_re.sub('-', value)

PEERS_REPO = "../peers-wg"
directory = PEERS_REPO

def read_repo_keys(directory):
    repokeys = []
    for file in Path(directory).rglob('*'):
        if file.is_file() and '.git' not in file.parts:
            key = file.read_text().strip().split("\n")[0]
            
            if not re.match("^[0-9a-zA-Z+/]{42}[AEIMQUYcgkosw480]=$", key):
                print(f"Warning: Skipping {file.name}. Key is invalid!")
                continue
            router_name = file.relative_to(Path(directory))
            repokeys.append(router_name)
    return repokeys


name_list = read_repo_keys(PEERS_REPO)

url = "https://map.aachen.freifunk.net/data/nodes.json"
t = requests.get(url)
t.raise_for_status()
nodes = t.json()["nodes"]
# Parse the key data and create a TSIG keyring

router_codes = []
for node in nodes:
    router_codes.append(slugify(node["nodeinfo"]["hostname"]))

len(router_codes)
len(name_list)

for router_name in name_list:
    splitting = "_".join(router_name.name.split("_")[:-1])
    # some contain - which are not in the filename and create false positives
    # handle with care
    
    if splitting not in router_codes:
        print(router_name)
        (Path(directory)/router_name).unlink()
