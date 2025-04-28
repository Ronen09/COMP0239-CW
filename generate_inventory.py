#!/usr/bin/env python3

import json
import subprocess
import argparse

def run(command, cwd=None):
    # Ensure stderr is captured too, in case of terraform errors
    result = subprocess.run(command, capture_output=True, encoding='UTF-8', cwd=cwd)
    if result.returncode != 0:
        print(f"Error running command '{' '.join(command)}': {result.stderr}")
        # Decide how to handle errors, e.g., raise exception or return empty data
        # For now, print error and return potentially partial/empty data
    return result

def expand_full_path(path):
    return subprocess.os.path.expanduser(path)

def generate_inventory():
    host_vars = {}
    terraform_dir = expand_full_path("/home/Ronen/Documents/COMP0239/terraform")

    # --- Define SSH Connection Parameters ---
    # *** Replace with the username on your Spark/MinIO VMs ***
    target_vm_user = "almalinux" # Or centos, ubuntu, your-user, etc.
    ssh_common_args = "-J condenser-proxy"
    # Get Spark Master IP
    command = "terraform output --json spark_master_ips".split()
    tf_result = run(command, cwd=terraform_dir)
    if not tf_result.stdout.strip(): return json.dumps({}) # Handle empty output
    ip_data = json.loads(tf_result.stdout)
    master_node = ip_data.pop()
    host_vars[master_node] = {
        "ip": [master_node],
        "compute_node": "0",
        "ansible_user": target_vm_user
    }

    # Get MinIO Node IP
    command = "terraform output --json minio_storage_node_ips".split()
    tf_result = run(command, cwd=terraform_dir)
    if not tf_result.stdout.strip(): return json.dumps({}) # Handle empty output
    ip_data = json.loads(tf_result.stdout)
    minio_node = ip_data.pop()
    host_vars[minio_node] = {
        "ip": [minio_node],
        "ansible_user": target_vm_user
    }

    # Get Spark Worker IPs
    workers = []
    command = "terraform output --json spark_worker_ips".split()
    tf_result = run(command, cwd=terraform_dir)
    if not tf_result.stdout.strip(): return json.dumps({}) # Handle empty output
    ip_data = json.loads(tf_result.stdout)
    for (idx, worker_ip) in enumerate(ip_data):
        host_vars[worker_ip] = {
            "ip": [worker_ip],
            "compute_node": str(idx+1),
            "ansible_user": target_vm_user
        }
        workers.append(worker_ip)

    # --- Construct Final Inventory (with Group Vars) ---
    _meta = {"hostvars": host_vars}
    _all = {"children": ["spark_master", "spark_workers", "minio_nodes"]}
    # Define group vars here as suggested by professor
    group_vars = {"ansible_ssh_common_args": ssh_common_args}
    _spark_master = {"hosts": [master_node], "vars": group_vars}
    _minio_nodes = {"hosts": [minio_node], "vars": group_vars}
    _spark_workers = {"hosts": workers, "vars": group_vars}

    _jd = {
        "_meta": _meta,
        "all": _all,
        "spark_master": _spark_master,
        "minio_nodes": _minio_nodes,
        "spark_workers": _spark_workers
    }
    # --- End Construct Final Inventory ---

    jd = json.dumps(_jd, indent=4)
    return jd

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description = "Generate a cluster inventory from Terraform.",
        prog = __file__
    )
    mo = ap.add_mutually_exclusive_group()
    mo.add_argument("--list", action="store", nargs="*", default="dummy", help="Show JSON of all managed hosts")
    mo.add_argument("--host", action="store", help="Display vars related to the host")
    args = ap.parse_args()

    if args.host:
        # Ansible --host expects an empty JSON object if no specific vars are needed
        print(json.dumps({}))
    elif len(args.list) >= 0:
        jd = generate_inventory()
        print(jd)
    else:
        raise ValueError("Expecting either --host $HOSTNAME or --list")
