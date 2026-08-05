output "resource_group_name" {
  description = "Resource group containing the monitoring and automation framework."
  value       = azurerm_resource_group.monitoring.name
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace resource ID."
  value       = azurerm_log_analytics_workspace.main.id
}

output "application_insights_connection_string" {
  description = "Connection string to configure in the monitored application."
  value       = azurerm_application_insights.main.connection_string
  sensitive   = true
}

output "logic_app_id" {
  description = "Logic App workflow resource ID."
  value       = azurerm_logic_app_workflow.self_healing.id
}

output "action_group_id" {
  description = "Azure Monitor action group resource ID."
  value       = azurerm_monitor_action_group.self_healing.id
}

output "metric_alert_id" {
  description = "HTTP 5xx metric alert resource ID."
  value       = azurerm_monitor_metric_alert.http_5xx.id
}
