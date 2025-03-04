import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

# run git restore-mtime before
# sudo apt install git-restore-mtime
# https://github.com/MestreLion/git-tools/
PEERS_REPO = "../peers-wg"


def read_and_delete_repo_keys(directory: str | Path):
    """
    reads all keys in the peers-wg repo and removes duplicate keys.
    Uses the mtime of the file to determine the older file and 
    """
    repokeys = {}
    for file in Path(directory).rglob('*'):
        if file.is_file() and '.git' not in file.parts:
            try:
                key = file.read_text().strip().split("\n")[0]
                if not re.match(r"^[0-9a-zA-Z+/]{42}[AEIMQUYcgkosw480]=$", key):
                    print(f"Key of {file.name} is invalid! Removing.")
                    file.unlink()
                    continue

                if key in repokeys.keys():
                    other_file = repokeys[key]
                    other_creation_date = datetime.fromtimestamp(
                        other_file.stat().st_mtime
                    )
                    creation_date = datetime.fromtimestamp(file.stat().st_mtime)
                    print(f"key {key} exists in {file} and {other_file}")
                    conflicted_file = file
                    if creation_date <= other_creation_date:
                        
                        file.unlink()
                        print(f"removed {file}")
                    else:
                        other_file.unlink()
                        repokeys[key] = file
                        print(f"removed {other_file}")
                else:
                    repokeys[key] = file
            except IOError as e:
                print(f"Error reading {file.name}: {e}")
    return repokeys

if __name__ == "__main__":
    keys = read_and_delete_repo_keys(PEERS_REPO)
