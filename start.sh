#!/bin/bash
echo "Starte API..."
az webapp start --resource-group rg-registration-bot --name registration-bot-app

echo "Starte Dashboard..."
az webapp start --resource-group rg-registration-bot --name registration-dashboard

echo "Fertig!"
echo "API:       https://registration-bot-app.azurewebsites.net"
echo "Dashboard: https://registration-dashboard.azurewebsites.net"
