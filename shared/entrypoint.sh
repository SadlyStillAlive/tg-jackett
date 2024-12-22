#!/bin/bash

# List contents of Jackett config directory
JACKETT_APP_DIR="/config/Jackett/"
echo "Listing contents of directory: $JACKETT_APP_DIR"
if [ -d "$JACKETT_APP_DIR" ]; then
  ls -l "$JACKETT_APP_DIR"
else
  echo "Directory $JACKETT_APP_DIR does not exist."
fi

# Configuration file path
CONFIG_FILE="/config/Jackett/ServerConfig.json"

# Wait for Jackett config file to be generated
echo "Waiting for Jackett config file: $CONFIG_FILE..."
while [ ! -f "$CONFIG_FILE" ]; do
  echo "Config file not found. Retrying in 5 seconds..."
  sleep 10
done
echo "Config file found: $CONFIG_FILE."

# Run the intermediate script
if [ -f "/shared/process_config.sh" ]; then
  chmod +x /shared/process_config.sh
  echo "Running process_config.sh..."
  /shared/process_config.sh
else
  echo "process_config.sh not found. Skipping."
fi

# # Display the .env file for verification
# echo "Final .env file contents:"
# cat /shared/.env

# # Fetch Jackett API details
# echo "Fetching Jackett API details..."
# JACKETT_API_URL="http://jackett:9117"
# JACKETT_API_KEY=$(curl -s "$JACKETT_API_URL/api/v2.0/indexers/all/results/torznab/api?apikey=${JACKETT_API_KEY_ENV}")

# if [ -z "$JACKETT_API_KEY" ]; then
#   echo "Failed to fetch Jackett API key. Exiting."
#   exit 1
# fi

echo "-----------------------------------------"
echo "Jackett API URL: $JACKETT_API_URL"
echo "Jackett API Key: $JACKETT_API_KEY"
echo "-----------------------------------------"

# Save Jackett details to .env file
echo "Saving Jackett details to .env..."
echo "JACKETT_API_URL=$JACKETT_API_URL" > /shared/.env
echo "JACKETT_API_KEY=$JACKETT_API_KEY" >> /shared/.env

# Fetch Telegram Bot Token
if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Telegram Bot Token not found in environment variables. Exiting."
  exit 1
fi

echo "-----------------------------------------"
echo "Telegram Bot Token: $TELEGRAM_BOT_TOKEN"
echo "-----------------------------------------"

# Save Telegram Bot Token to .env file
echo "Saving Telegram Bot Token to .env..."
echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" >> /shared/.env

# Start the Telegram bot
echo "Starting Telegram bot..."
python /bot/bot.py
