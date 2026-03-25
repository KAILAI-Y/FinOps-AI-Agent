output "demo_vm_name" {
  description = "Demo VM instance name."
  value       = google_compute_instance.demo_vm.name
}

output "demo_vm_external_ip" {
  description = "External IP assigned to the demo VM."
  value       = google_compute_instance.demo_vm.network_interface[0].access_config[0].nat_ip
}
