variable "name_prefix" {
  description = "Short lowercase prefix used for created resources."
  type        = string
  default     = "selfheal"

  validation {
    condition     = can(regex("^[a-z0-9-]{3,16}$", var.name_prefix))
    error_message = "name_prefix must contain 3-16 lowercase letters, numbers or hyphens."
  }
}

variable "location" {
  description = "Azure region for the monitoring and automation resources."
  type        = string
  default     = "West Europe"
}

variable "target_web_app_resource_id" {
  description = "Full Azure resource ID of the existing Web App to monitor and restart."
  type        = string

  validation {
    condition     = startswith(lower(var.target_web_app_resource_id), "/subscriptions/") && strcontains(lower(var.target_web_app_resource_id), "/providers/microsoft.web/sites/")
    error_message = "Provide a full Microsoft.Web/sites Azure resource ID."
  }
}

variable "target_resource_group_name" {
  description = "Resource group containing the target Web App."
  type        = string
}

variable "target_web_app_name" {
  description = "Name of the target Azure Web App."
  type        = string
}

variable "http_5xx_threshold" {
  description = "Number of HTTP 5xx responses in the alert window that triggers remediation."
  type        = number
  default     = 5

  validation {
    condition     = var.http_5xx_threshold >= 1
    error_message = "http_5xx_threshold must be at least 1."
  }
}

variable "webhook_expiry_time" {
  description = "ISO 8601 expiration time for the Azure Automation webhook. Rotate before expiry."
  type        = string
  default     = "2030-01-01T00:00:00Z"
}

variable "notification_webhook_uri" {
  description = "Optional Teams/Slack-compatible incoming webhook URI for remediation notifications."
  type        = string
  default     = null
  sensitive   = true
}

variable "tags" {
  description = "Tags applied to created Azure resources."
  type        = map(string)
  default = {
    project     = "azure-self-healing-sre-platform"
    environment = "portfolio"
    managed-by  = "terraform"
  }
}
