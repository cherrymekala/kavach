variable "project_id" { type = string }
variable "region" {
  type    = string
  default = "asia-south1"
}
variable "billing_account" { type = string }
variable "budget_amount" {
  type    = number
  default = 4500
}
variable "budget_currency" {
  description = "Must match the billing account's currency."
  type        = string
  default     = "INR"
}
