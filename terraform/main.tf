data "harvester_image" "img" {
  display_name = var.img_display_name
  namespace    = "harvester-public"
}

data "harvester_ssh_key" "mysshkey" {
  name      = var.keyname
  namespace = var.namespace
}

data "harvester_ssh_key" "lecturersshkey" {
  name = var.lecturer-key
  namespace = var.namespace
}

resource "random_id" "secret" {
  byte_length = 5
}

resource "harvester_cloudinit_secret" "cloud-config" {
  name      = "cloud-config-${random_id.secret.hex}"
  namespace = var.namespace

  user_data = templatefile("cloud-init.tmpl.yml", {
      public_key_openssh = data.harvester_ssh_key.mysshkey.public_key
      lecturersshkey = data.harvester_ssh_key.lecturersshkey.public_key
    })
}

resource "harvester_virtualmachine" "spark_master" {
  
  count = 1

  name                 = "${var.username}-spark-master-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  namespace            = var.namespace
  restart_after_update = true

  description = "Spark Master/Driver Node"

  cpu    = 2 
  memory = "4Gi"

  efi         = true
  secure_boot = false

  run_strategy    = "RerunOnFailure"
  hostname        = "${var.username}-cw-head-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = "10Gi"
    bus        = "virtio"
    boot_order = 1

    image       = data.harvester_image.img.id
    auto_delete = true
  }

  tags = {
    condenser_ingress_isEnabled = true
    condenser_ingress_isAllowed = true
    condenser_ingress_prometheus_hostname = "${var.username}-cw-prometheus"
    condenser_ingress_prometheus_port = 9090
    condenser_ingress_prometheus_protocol = "https"
    condenser_ingress_grafana_hostname = "${var.username}-cw-grafana"
    condenser_ingress_grafana_port = 3000
    condenser_ingress_grafana_protocol = "https"
    condenser_ingress_node_port = 9100
    condenser_ingress_node_hostname = "node-${var.username}-head-${format("%02d", count.index + 1)}"
    condenser_ingress_sparkmaster_hostname = "${var.username}-spark-master-ui"
    condenser_ingress_sparkmaster_port = 8080
    condenser_ingress_sparkmaster_protocol = "http"
    condenser_ingress_sparkapp_hostname = "${var.username}-spark-app-ui"
    condenser_ingress_sparkapp_port = 4040
    condenser_ingress_sparkapp_protocol = "http"
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud-config.name
  }
}

resource "harvester_virtualmachine" "spark_worker" {
  
  count = var.vm_count

  name                 = "${var.username}-spark-worker-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  namespace            = var.namespace
  restart_after_update = true

  description = "Spark Worker Node"

  cpu    = 4
  memory = "32Gi"

  efi         = true
  secure_boot = false

  run_strategy    = "RerunOnFailure"
  hostname        = "${var.username}-cw-worker-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = "25Gi"
    bus        = "virtio"
    boot_order = 1

    image       = data.harvester_image.img.id
    auto_delete = true
  }

  disk {
    name       = "datadisk"
    type       = "disk"
    size       = "200Gi"
    bus        = "virtio"
    auto_delete = true
  }

  tags = {
    condenser_ingress_isEnabled = true
    condenser_ingress_isAllowed = true
    condenser_ingress_node_hostname = "node-${var.username}-worker-${format("%02d", count.index + 1)}"
    condenser_ingress_node_port = 9100
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud-config.name
  }
}

resource "harvester_virtualmachine" "minio_storage_node" {
  
  count = 1

  name                 = "${var.username}-minio-storage-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  namespace            = var.namespace
  restart_after_update = true

  description = "MinIO Storage Node"

  cpu    = 4
  memory = "32Gi"

  efi         = true
  secure_boot = false

  run_strategy    = "RerunOnFailure"
  hostname        = "${var.username}-minio-storage-${format("%02d", count.index + 1)}-${random_id.secret.hex}"
  reserved_memory = "100Mi"
  machine_type    = "q35"

  network_interface {
    name           = "nic-1"
    wait_for_lease = true
    type           = "bridge"
    network_name   = var.network_name
  }

  disk {
    name       = "rootdisk"
    type       = "disk"
    size       = "25Gi"
    bus        = "virtio"
    boot_order = 1

    image       = data.harvester_image.img.id
    auto_delete = true
  }

  disk {
    name       = "datadisk"
    type       = "disk"
    size       = "200Gi"
    bus        = "virtio"
    boot_order = 2
    auto_delete = true
  }

  tags = {
    condenser_ingress_isEnabled = true
    condenser_ingress_isAllowed = true
    condenser_ingress_node_hostname = "node-${var.username}-minio-storage-${format("%02d", count.index + 1)}"
    condenser_ingress_node_port = 9100
    condenser_ingress_os_hostname = "${var.username}-minio-s3"
    condenser_ingress_os_port = 9000
    condenser_ingress_os_protocol = "http"
    condenser_ingress_os_nginx_proxy-body-size = "0"
  }

  cloudinit {
    user_data_secret_name = harvester_cloudinit_secret.cloud-config.name
  }
}
