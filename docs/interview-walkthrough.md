# Interview walkthrough

## 60-second explanation

This project implements an event-driven self-healing workflow for an Azure Web App. Terraform provisions a Log Analytics workspace, Application Insights, diagnostic settings, an Azure Monitor metric alert, an action group, a Logic App and an Azure Automation account. When the HTTP 5xx threshold is breached, Azure Monitor sends the common alert schema to the Logic App. The Logic App invokes a PowerShell runbook webhook. The runbook authenticates with the Automation account's managed identity and calls Azure Resource Manager to restart the affected Web App. RBAC is scoped to the target Web App using the Website Contributor role.

The repository also demonstrates cloud-native delivery practices: Kubernetes probes and autoscaling, Flux GitOps reconciliation, Prometheus/Grafana monitoring, Jenkins and GitHub Actions validation, and an optional AI-assisted incident summary with a deterministic fallback.

## Design decisions

- **Managed identity instead of stored Azure credentials:** reduces secret-management risk.
- **Logic App as orchestration layer:** separates alert ingestion from remediation and allows notifications or approvals to be added.
- **Common alert schema:** provides a consistent alert payload.
- **Terraform:** makes the deployment repeatable and reviewable.
- **Scoped RBAC:** limits the Automation identity to the target Web App.
- **Safe AI usage:** AI summarizes evidence but does not execute remediation or invent a root cause.

## Failure modes to discuss

- Repeated restarts caused by a persistent dependency failure
- Expired or leaked Automation webhook
- Missing RBAC role assignment
- Alert noise from a threshold that is too sensitive
- Logic App or Automation regional outage
- Terraform state exposure
- Lack of deployment correlation or maintenance-window suppression

## Production controls

- Cooldown and maximum-attempt logic
- Approval gates for destructive actions
- Webhook rotation and Key Vault integration
- Private networking where supported
- SLO-based alerts and incident deduplication
- Correlation with deployments and change tickets
- Post-remediation health verification before closing the incident
