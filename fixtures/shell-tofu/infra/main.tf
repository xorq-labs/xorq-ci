variable "name" {
  type    = string
  default = "fixture"
}

output "name" {
  value = var.name
}
