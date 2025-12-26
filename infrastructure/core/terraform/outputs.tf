################################################################################
# Outputs - Important values after deployment
################################################################################

output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "function_app_name" {
  description = "Name of the Function App"
  value       = azurerm_linux_function_app.main.name
}

output "function_app_url" {
  description = "Default hostname of the Function App"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}"
}

output "webhook_url" {
  description = "Webhook URL for Azure DevOps pipeline (add function key manually)"
  value       = "https://${azurerm_linux_function_app.main.default_hostname}/api/HandleFailure"
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "key_vault_name" {
  description = "Name of the Key Vault"
  value       = azurerm_key_vault.main.name
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint"
  value       = azurerm_cognitive_account.openai.endpoint
}

output "openai_deployment_name" {
  description = "Name of the GPT-4o deployment"
  value       = azurerm_cognitive_deployment.gpt4o.name
}

output "application_insights_name" {
  description = "Name of Application Insights"
  value       = azurerm_application_insights.main.name
}

output "function_app_principal_id" {
  description = "Managed Identity Principal ID of Function App"
  value       = azurerm_linux_function_app.main.identity[0].principal_id
}

output "next_steps" {
  description = "What to do after deployment"
  value = <<-EOT
  
  Deployment Complete!
  
  📋 Next Steps:
  
  1. Set Azure DevOps PAT in Key Vault:
     az keyvault secret set --vault-name ${azurerm_key_vault.main.name} \
       --name ado-pat --value "YOUR_AZURE_DEVOPS_PAT"
  
  2. Deploy Function App code:
     cd ../../../src/agents/infra-healer
     func azure functionapp publish ${azurerm_linux_function_app.main.name}
  
  3. Get Function Key:
     func azure functionapp list-functions ${azurerm_linux_function_app.main.name} --show-keys
  
  4. Update Azure DevOps pipeline with webhook:
     ${self.value["webhook_url"]}?code=YOUR_FUNCTION_KEY
  
  5. View logs:
     func azure functionapp logstream ${azurerm_linux_function_app.main.name}
  
  📊 Resources Created:
  - Resource Group: ${azurerm_resource_group.main.name}
  - Function App: ${azurerm_linux_function_app.main.name}
  - Storage Account: ${azurerm_storage_account.main.name}
  - Key Vault: ${azurerm_key_vault.main.name}
  - OpenAI: ${azurerm_cognitive_account.openai.name}
  - App Insights: ${azurerm_application_insights.main.name}
  
  EOT
}