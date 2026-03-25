provider "google" {
  project     = var.project_id
  region      = var.region
  zone        = var.zone
  credentials = var.credentials_file != "" ? file(var.credentials_file) : null
}

locals {
  common_labels = {
    managed_by  = "terraform"
    env         = var.environment_label
    owner       = var.owner_label
    team        = var.team_label
    cost-center = var.cost_center_label
  }
}

resource "google_compute_instance" "demo_vm" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone
  labels       = local.common_labels

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-12"
      size  = 20
      type  = "pd-balanced"
    }
  }

  network_interface {
    network    = var.existing_network_name
    subnetwork = var.existing_subnetwork_name

    access_config {}
  }

  lifecycle {
    ignore_changes = [
      attached_disk,
      confidential_instance_config,
      description,
      guest_accelerator,
      metadata,
      metadata_startup_script,
      network_interface,
      reservation_affinity,
      scheduling,
      service_account,
      shielded_instance_config,
      tags,
    ]
  }
}
