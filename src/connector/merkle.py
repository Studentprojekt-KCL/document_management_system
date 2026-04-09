import os
import hashlib
import json
import logging
from typing import Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import datetime
CACHE_FILE = "merkle_cache.json"
MAX_WORKERS = 8  # testa 4–16 beroende på maskin
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# ---------------------------
# 🔹 Hash utilities
# ---------------------------

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------
# 🔹 Cache handling
# ---------------------------

def load_cache() -> Dict:
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_cache(cache: Dict):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)


#------------------------------
# helpers
def should_rehash(old_meta, new_meta):
    return (
        old_meta["size"] == new_meta["size"] and
        old_meta["mtime"] == new_meta["mtime"]
    )

def get_subtree(cache, root_path):
    root_path = root_path.rstrip("/") + "/"
    return {
        path: data
        for path, data in cache.items()
        if path == root_path[:-1] or path.startswith(root_path)
    }



# ---------------------------
# 🔹 Core Merkle logic
# ---------------------------

def fmt_time(ts):
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def scan(path: str, old_cache: Dict) -> Tuple[str, Dict]:
    new_cache = {}

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        return "", {}

    h = hashlib.sha256()

    futures = []
    results = {}

    for name in entries:
        full_path = os.path.join(path, name)

        try:
            stat = os.stat(full_path)
        except FileNotFoundError:
            continue

        meta = {
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
            "ctime": int(stat.st_ctime),
            "atime": int(stat.st_atime)
        }
        logging.info("Scanning: %s (mtime: %s, size: %s)", full_path, time.ctime(meta["mtime"]), meta["size"])

        # -------------------
        # FILE (parallel)
        # -------------------
        if os.path.isfile(full_path):
            old = old_cache.get(full_path)
            if old:
                logging.debug("should rehash: %s", should_rehash(old["meta"], meta))
            if old and should_rehash(old["meta"], meta):
                logging.debug("Reusing cached hash for %s", full_path)
                # reuse cache
                results[full_path] = (name, old["hash"], meta, "file")
            else:
                # kör hashing i thread
                future = executor.submit(hash_file, full_path)
                futures.append((future, full_path, name, meta))

        # -------------------
        # DIRECTORY (sync)
        # -------------------
        elif os.path.isdir(full_path):
            old = old_cache.get(full_path)

            if old and should_rehash(old["meta"], meta):
                subtree = get_subtree(old_cache, full_path)
                new_cache.update(subtree)

                results[full_path] = (name, old["hash"], meta, "dir")
                continue

            else:
                dir_hash, child_cache = scan(full_path, old_cache)
                new_cache.update(child_cache)

                results[full_path] = (name, dir_hash, meta, "dir")

        else:
            continue

    # samla threaded resultat
    for future, full_path, name, meta in futures:
        file_hash = future.result()
        results[full_path] = (name, file_hash, meta, "file")

    # bygg hash + cache
    for full_path, (name, file_hash, meta, typ) in sorted(
        results.items(), key=lambda x: x[1][0]
    ):
        h.update(name.encode())
        h.update(file_hash.encode())

        new_cache[full_path] = {
            "hash": file_hash,
            "meta": meta,
            "type": typ
        }

    # spara directory själv
    stat = os.stat(path)
    new_cache[path] = {
        "hash": h.hexdigest(),
        "meta": {
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
            "ctime": int(stat.st_ctime),
            "atime": int(stat.st_atime)
        },
        "type": "dir"
    }

    return h.hexdigest(), new_cache

# ---------------------------
# 🔹 Diff detection
# ---------------------------

def diff(old_cache: Dict, new_cache: Dict):
    added = []
    removed = []
    modified = []

    old_paths = set(old_cache.keys())
    new_paths = set(new_cache.keys())

    for path in new_paths - old_paths:
        added.append(path)

    for path in old_paths - new_paths:
        removed.append(path)

    for path in old_paths & new_paths:
        if old_cache[path]["hash"] != new_cache[path]["hash"]:
            modified.append(path)

    return added, removed, modified


#----------------------------
# Make Tree
#----------------------------

def build_tree(path, cache):
    node = {
        "name": os.path.basename(path),
        "path": path,
        "children": [],
        "hash": None,
        "type": "dir" if os.path.isdir(path) else "file"
    }

    if os.path.isfile(path):
        node["hash"] = cache[path]["hash"]
        return node

    for name in sorted(os.listdir(path)):
        full = os.path.join(path, name)
        if full in cache:
            node["children"].append(build_tree(full, cache))

    node["hash"] = cache[path]["hash"]
    return node


#----------------------------
#  Terminal Visualisering
#----------------------------
def print_tree(node, changed=set(), prefix=""):
    marker = ""

    if node["path"] in changed:
        marker = " 🔴"

    logging.info("%s%s [%s]%s", prefix, node["name"], node["hash"][:6], marker)

    for i, child in enumerate(node.get("children", [])):
        last = i == len(node["children"]) - 1
        new_prefix = prefix + ("   " if last else "│  ")
        print_tree(child, changed, new_prefix)






# ---------------------------
# 🔹 MAIN
# ---------------------------

def build_merkle(root_path: str):
    logging.info("Scanning root: %s", root_path)
    start = time.time()

    old_cache = load_cache()

    root_hash, new_cache = scan(root_path, old_cache)

    added, removed, modified = diff(old_cache, new_cache)

    save_cache(new_cache)

    end = time.time()
    logging.info("Merkle root: %s", root_hash)
    logging.info("Changes: added=%s removed=%s modified=%s", len(added), len(removed), len(modified))
    logging.info("Time taken: %.2f seconds", end - start)

    tree = build_tree(ROOT, new_cache)

    changed = set(modified + added + removed)

    logging.info("Tree:")
    print_tree(tree, changed)



    return {
        "root_hash": root_hash,
        "added": added,
        "removed": removed,
        "modified": modified
    }


if __name__ == "__main__":
    ROOT = "/mnt/Kernel/projB"   # 👈 ändra till din SMB mount
    build_merkle(ROOT)
