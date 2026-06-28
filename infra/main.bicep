targetScope = 'resourceGroup'

@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Prefix used for resource names.')
param namePrefix string = 'regbot'

@description('Name of the Linux App Service plan.')
param appServicePlanName string

@description('Name of the web app that hosts the FastAPI API.')
param apiWebAppName string

@description('Name of the web app that hosts the Streamlit frontend.')
param frontendWebAppName string

@description('Name of the Key Vault.')
param keyVaultName string

@description('Name of the Azure SQL Server.')
param sqlServerName string

@description('Name of the Azure SQL database.')
param sqlDatabaseName string = 'registrationdb'

@description('SQL admin login name.')
param sqlAdminLogin string = 'regbotadmin'

@secure()
@description('SQL admin password.')
param sqlAdminPassword string

@description('Name of the Azure AI Services account that provides the AiKey secret.')
param aiServicesName string

@description('Name of the Azure Speech resource.')
param speechName string

@description('Region string expected by the Speech SDK, for example swedencentral.')
param speechRegion string = location

@description('Azure AI Foundry project endpoint used by the app.')
param aiProjectEndpoint string

@description('Model deployment name used by the agent.')
param openAiDeploymentName string = 'gpt-4o'

var sqlServerDnsSuffix = environment().suffixes.sqlServerHostname
var sqlConnectionString = 'Server=tcp:${sqlServerName}.${sqlServerDnsSuffix},1433;Initial Catalog=${sqlDatabaseName};Persist Security Info=False;User ID=${sqlAdminLogin};Password=${sqlAdminPassword};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;'

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${namePrefix}-appi'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
  }
}

resource appServicePlan 'Microsoft.Web/serverfarms@2022-09-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: keyVaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enabledForDeployment: true
    enabledForTemplateDeployment: true
    enableRbacAuthorization: false
    publicNetworkAccess: 'Enabled'
    accessPolicies: []
  }
}

resource sqlServer 'Microsoft.Sql/servers@2021-11-01-preview' = {
  name: sqlServerName
  location: location
  properties: {
    administratorLogin: sqlAdminLogin
    administratorLoginPassword: sqlAdminPassword
    version: '12.0'
    publicNetworkAccess: 'Enabled'
  }
}

resource sqlFirewallAllowAzure 'Microsoft.Sql/servers/firewallRules@2021-11-01-preview' = {
  parent: sqlServer
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2021-11-01-preview' = {
  parent: sqlServer
  name: sqlDatabaseName
  location: location
  sku: {
    name: 'S0'
    tier: 'Standard'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 2147483648
    zoneRedundant: false
    readScale: 'Disabled'
  }
}

resource aiServices 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: aiServicesName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

resource speechService 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: speechName
  location: location
  kind: 'SpeechServices'
  sku: {
    name: 'S0'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

var aiServiceKeys = aiServices.listKeys()
var speechServiceKeys = speechService.listKeys()

resource sqlConnectionSecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'SqlConnectionString'
  properties: {
    value: sqlConnectionString
  }
}

resource aiKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'AiKey'
  properties: {
    value: aiServiceKeys.key1
  }
}

resource speechKeySecret 'Microsoft.KeyVault/vaults/secrets@2023-07-01' = {
  parent: keyVault
  name: 'SpeechKey'
  properties: {
    value: speechServiceKeys.key1
  }
}

resource apiWebApp 'Microsoft.Web/sites@2022-09-01' = {
  name: apiWebAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      alwaysOn: true
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'bash startup.sh'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8501'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'PYTHON_VERSION'
          value: '3.12'
        }
        {
          name: 'APP_MODE'
          value: 'api'
        }
        {
          name: 'AZURE_KEYVAULT_URL'
          value: keyVault.properties.vaultUri
        }
        {
          name: 'AZURE_AI_PROJECT_ENDPOINT'
          value: aiProjectEndpoint
        }
        {
          name: 'AZURE_OPENAI_DEPLOYMENT'
          value: openAiDeploymentName
        }
        {
          name: 'AZURE_SPEECH_REGION'
          value: speechRegion
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'AZURE_SQL_CONNECTIONSTRING'
          value: '@Microsoft.KeyVault(SecretUri=${sqlConnectionSecret.properties.secretUriWithVersion})'
        }
        {
          name: 'AZURE_AI_KEY'
          value: '@Microsoft.KeyVault(SecretUri=${aiKeySecret.properties.secretUriWithVersion})'
        }
      ]
    }
  }
}

resource frontendWebApp 'Microsoft.Web/sites@2022-09-01' = {
  name: frontendWebAppName
  location: location
  kind: 'app,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      alwaysOn: true
      linuxFxVersion: 'PYTHON|3.12'
      appCommandLine: 'bash startup.sh'
      ftpsState: 'Disabled'
      appSettings: [
        {
          name: 'WEBSITES_PORT'
          value: '8501'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '1'
        }
        {
          name: 'PYTHON_VERSION'
          value: '3.12'
        }
        {
          name: 'APP_MODE'
          value: 'frontend'
        }
        {
          name: 'API_URL'
          value: 'https://${apiWebApp.properties.defaultHostName}'
        }
        {
          name: 'AZURE_SPEECH_REGION'
          value: speechRegion
        }
        {
          name: 'AZURE_SPEECH_KEY'
          value: '@Microsoft.KeyVault(SecretUri=${speechKeySecret.properties.secretUriWithVersion})'
        }
      ]
    }
  }
}

resource keyVaultAccessPolicy 'Microsoft.KeyVault/vaults/accessPolicies@2023-07-01' = {
  name: 'add'
  parent: keyVault
  properties: {
    accessPolicies: [
      {
        tenantId: tenant().tenantId
        objectId: apiWebApp.identity.principalId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
        }
      }
      {
        tenantId: tenant().tenantId
        objectId: frontendWebApp.identity.principalId
        permissions: {
          secrets: [
            'get'
            'list'
          ]
        }
      }
    ]
  }
}

output apiWebAppDefaultHostName string = apiWebApp.properties.defaultHostName
output frontendWebAppDefaultHostName string = frontendWebApp.properties.defaultHostName
output keyVaultUri string = keyVault.properties.vaultUri
output sqlServerFqdn string = '${sqlServerName}.${sqlServerDnsSuffix}'
output speechResourceId string = speechService.id
output aiServicesId string = aiServices.id
output applicationInsightsConnectionString string = appInsights.properties.ConnectionString
