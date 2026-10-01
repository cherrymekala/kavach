variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "asia-south1"
}
variable "billing_account" { type = string }
variable "budget_usd" {
  type    = number
  default = 50
}
