data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "monitoring" {
  name     = "rg-${var.name_prefix}-monitoring"
  location = var.location
  tags     = var.tags
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${var.name_prefix}"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${var.name_prefix}"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = var.tags
}

resource "azurerm_monitor_diagnostic_setting" "target_web_app" {
  name                       = "send-to-${azurerm_log_analytics_workspace.main.name}"
  target_resource_id         = var.target_web_app_resource_id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id

  enabled_log {
    category_group = "allLogs"
  }

  enabled_metric {
    category = "AllMetrics"
  }
}

resource "azurerm_automation_account" "main" {
  name                         = "aa-${var.name_prefix}"
  location                     = azurerm_resource_group.monitoring.location
  resource_group_name          = azurerm_resource_group.monitoring.name
  sku_name                     = "Basic"
  local_authentication_enabled = false

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_automation_runbook" "restart_web_app" {
  name                    = "Restart-UnhealthyWebApp"
  location                = azurerm_resource_group.monitoring.location
  resource_group_name     = azurerm_resource_group.monitoring.name
  automation_account_name = azurerm_automation_account.main.name
  log_verbose             = true
  log_progress            = true
  description             = "Restarts an unhealthy Azure Web App after a validated Azure Monitor alert."
  runbook_type            = "PowerShell72"
  content                 = file("${path.module}/../automation/restart-webapp.ps1")
  tags                    = var.tags
}

resource "azurerm_automation_webhook" "restart_web_app" {
  name                    = "restart-web-app-webhook"
  resource_group_name     = azurerm_resource_group.monitoring.name
  automation_account_name = azurerm_automation_account.main.name
  expiry_time             = var.webhook_expiry_time
  enabled                 = true
  runbook_name            = azurerm_automation_runbook.restart_web_app.name
}

resource "azurerm_role_assignment" "automation_web_app" {
  scope                = var.target_web_app_resource_id
  role_definition_name = "Website Contributor"
  principal_id         = azurerm_automation_account.main.identity[0].principal_id
}

resource "azurerm_logic_app_workflow" "self_healing" {
  name                = "logic-${var.name_prefix}-self-healing"
  location            = azurerm_resource_group.monitoring.location
  resource_group_name = azurerm_resource_group.monitoring.name
  tags                = var.tags
}

resource "azurerm_logic_app_trigger_http_request" "azure_monitor_alert" {
  name         = "When_Azure_Monitor_Alert_Fires"
  logic_app_id = azurerm_logic_app_workflow.self_healing.id

  schema = jsonencode({
    type = "object"
    properties = {
      schemaId = { type = "string" }
      data     = { type = "object" }
    }
  })
}

resource "azurerm_logic_app_action_custom" "invoke_automation" {
  name         = "Invoke_Automation_Webhook"
  logic_app_id = azurerm_logic_app_workflow.self_healing.id

  body = jsonencode({
    type = "Http"
    inputs = {
      method = "POST"
      uri    = azurerm_automation_webhook.restart_web_app.uri
      headers = {
        "Content-Type" = "application/json"
      }
      body = {
        subscriptionId    = data.azurerm_client_config.current.subscription_id
        resourceGroupName = var.target_resource_group_name
        webAppName         = var.target_web_app_name
        alertRule          = "@{triggerBody()?['data']?['essentials']?['alertRule']}"
        severity           = "@{triggerBody()?['data']?['essentials']?['severity']}"
        firedDateTime      = "@{triggerBody()?['data']?['essentials']?['firedDateTime']}"
      }
    }
    runAfter = {}
  })
}

resource "azurerm_logic_app_action_custom" "notify_operations" {
  count        = var.notification_webhook_uri == null ? 0 : 1
  name         = "Notify_Operations"
  logic_app_id = azurerm_logic_app_workflow.self_healing.id

  body = jsonencode({
    type = "Http"
    inputs = {
      method = "POST"
      uri    = var.notification_webhook_uri
      headers = {
        "Content-Type" = "application/json"
      }
      body = {
        text = "@{concat('Self-healing remediation invoked for ', triggerBody()?['data']?['essentials']?['alertRule'], '. Severity: ', triggerBody()?['data']?['essentials']?['severity'])}"
      }
    }
    runAfter = {
      Invoke_Automation_Webhook = ["Succeeded"]
    }
  })
}

resource "azurerm_monitor_action_group" "self_healing" {
  name                = "ag-${var.name_prefix}-self-healing"
  resource_group_name = azurerm_resource_group.monitoring.name
  short_name          = substr(replace(var.name_prefix, "-", ""), 0, 12)
  tags                = var.tags

  logic_app_receiver {
    name                    = "self-healing-logic-app"
    resource_id             = azurerm_logic_app_workflow.self_healing.id
    callback_url            = azurerm_logic_app_trigger_http_request.azure_monitor_alert.callback_url
    use_common_alert_schema = true
  }
}

resource "azurerm_monitor_metric_alert" "http_5xx" {
  name                = "alert-${var.name_prefix}-http5xx"
  resource_group_name = azurerm_resource_group.monitoring.name
  scopes              = [var.target_web_app_resource_id]
  description         = "Triggers self-healing when HTTP 5xx responses exceed the configured threshold."
  severity            = 2
  enabled             = true
  auto_mitigate       = true
  frequency           = "PT1M"
  window_size         = "PT5M"
  tags                = var.tags

  criteria {
    metric_namespace = "Microsoft.Web/sites"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = var.http_5xx_threshold
  }

  action {
    action_group_id = azurerm_monitor_action_group.self_healing.id
  }
}
