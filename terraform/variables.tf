variable "project_id" {
  description = "GCP project ID used for all Terraform-managed resources."
  type        = string
}

variable "credentials_file" {
  description = "Absolute path to a GCP service account JSON key. Leave empty to use ADC."
  type        = string
  default     = ""
}

variable "region" {
  description = "Default region for regional resources."
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "Default zone for zonal resources."
  type        = string
  default     = "us-central1-c"
}

variable "network_name" {
  description = "VPC network name."
  type        = string
  default     = "finops-agent-vpc"
}

variable "subnet_name" {
  description = "Subnetwork name."
  type        = string
  default     = "finops-agent-subnet"
}

variable "subnet_cidr" {
  description = "CIDR block for the demo subnet."
  type        = string
  default     = "10.10.0.0/24"
}

variable "dataset_id" {
  description = "BigQuery dataset for telemetry history."
  type        = string
  default     = "finops_agent"
}

variable "instance_name" {
  description = "Demo VM instance name."
  type        = string
  default     = "finops-agent-demo-vm"
}

variable "machine_type" {
  description = "Machine type for the demo VM."
  type        = string
  default     = "e2-medium"
}

variable "boot_disk_name" {
  description = "Existing boot disk name for the imported VM."
  type        = string
  default     = ""
}

variable "existing_network_name" {
  description = "Existing VPC network name for the imported VM."
  type        = string
  default     = "default"
}

variable "existing_subnetwork_name" {
  description = "Existing subnetwork name for the imported VM."
  type        = string
  default     = "default"
}

variable "service_account_id" {
  description = "Service account account_id for the demo VM."
  type        = string
  default     = "finops-agent-demo-sa"
}

variable "owner_label" {
  description = "Owner label applied to demo resources."
  type        = string
  default     = "platform-owner"
}

variable "team_label" {
  description = "Team label applied to demo resources."
  type        = string
  default     = "platform-team"
}

variable "environment_label" {
  description = "Environment label applied to demo resources."
  type        = string
  default     = "dev"
}

variable "cost_center_label" {
  description = "Cost center label applied to demo resources."
  type        = string
  default     = "finops-lab"
}
