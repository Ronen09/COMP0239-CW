output spark_worker_ips {
  value = harvester_virtualmachine.spark_worker[*].network_interface[0].ip_address
}

output spark_worker_ids {
  value = harvester_virtualmachine.spark_worker.*.id
}

output spark_master_ips {
  value = harvester_virtualmachine.spark_master[*].network_interface[0].ip_address
}

output spark_master_ids {
  value = harvester_virtualmachine.spark_master.*.id
}

output "minio_storage_node_ips" {
  description = "IP addresses of the MinIO storage node"
  value       = harvester_virtualmachine.minio_storage_node[*].network_interface[0].ip_address
}

output "minio_storage_node_ids" {
  description = "IDs of the MinIO storage node"
  value       = harvester_virtualmachine.minio_storage_node[*].id
}