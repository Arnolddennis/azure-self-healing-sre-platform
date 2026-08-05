param(
    [Parameter(Mandatory = $false)]
    [object] $WebhookData
)

$ErrorActionPreference = "Stop"

if (-not $WebhookData) {
    throw "WebhookData was not supplied. Run this runbook from its webhook or provide test webhook data."
}

if (-not $WebhookData.RequestBody) {
    throw "The webhook request did not include a RequestBody."
}

$payload = $WebhookData.RequestBody | ConvertFrom-Json
$requiredFields = @("subscriptionId", "resourceGroupName", "webAppName")

foreach ($field in $requiredFields) {
    if (-not $payload.$field) {
        throw "Required field '$field' is missing from the webhook payload."
    }
}

Write-Output "Starting self-healing action."
Write-Output "Alert rule: $($payload.alertRule)"
Write-Output "Severity: $($payload.severity)"
Write-Output "Target Web App: $($payload.resourceGroupName)/$($payload.webAppName)"

Disable-AzContextAutosave -Scope Process | Out-Null
$context = (Connect-AzAccount -Identity).Context
Set-AzContext -SubscriptionId $payload.subscriptionId -DefaultProfile $context | Out-Null

$path = "/subscriptions/$($payload.subscriptionId)/resourceGroups/$($payload.resourceGroupName)/providers/Microsoft.Web/sites/$($payload.webAppName)/restart?api-version=2023-12-01"
$response = Invoke-AzRestMethod -Method POST -Path $path

if ($response.StatusCode -notin @(200, 202, 204)) {
    throw "Restart request failed with status code $($response.StatusCode). Response: $($response.Content)"
}

Write-Output "Restart request accepted with status code $($response.StatusCode)."
Write-Output "Self-healing action completed."
