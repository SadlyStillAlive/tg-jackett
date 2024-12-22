#!/bin/bash

# Path to the ServerConfig.json file
CONFIG_FILE="/config/Jackett/ServerConfig.json"

echo "Waiting for Jackett config files to be available..."
while [ ! -f "$CONFIG_FILE" ]; do
  echo "Config file not found: $CONFIG_FILE. Retrying in 5 seconds..."
  sleep 1
done

echo "Config file found: $CONFIG_FILE. Proceeding with startup."

# Paths to save the extracted data
OUTPUT_JSON_FILE="/shared/envs/config.json"
OUTPUT_ENV_FILE="/shared/envs/.env"

# Ensure the /shared/envs directory exists
if [ ! -d "/shared/envs" ]; then
  echo "Creating directory /shared/envs..."
  mkdir -p /shared/envs
fi

# Check if the JSON file exists
if [ -f "$CONFIG_FILE" ]; then
  echo "Reading ServerConfig.json..."
  
  # Extract fields using jq
  PORT=$(jq -r '.Port' "$CONFIG_FILE")
  API_KEY=$(jq -r '.APIKey' "$CONFIG_FILE")
  INSTANCE_ID=$(jq -r '.InstanceId' "$CONFIG_FILE")
  LOCAL_BIND_ADDRESS=$(jq -r '.LocalBindAddress' "$CONFIG_FILE")

  echo "Extracted values:"
  echo "Port: $PORT"
  echo "APIKey: $API_KEY"
  echo "InstanceId: $INSTANCE_ID"
  echo "LocalBindAddress: $LOCAL_BIND_ADDRESS"

  # Write to JSON file
  echo "Saving to $OUTPUT_JSON_FILE..."
  cat <<EOF > "$OUTPUT_JSON_FILE"
{
  "JACKETT_PORT": "$PORT",
  "JACKETT_API_KEY": "$API_KEY",
  "JACKETT_INSTANCE_ID": "$INSTANCE_ID",
  "JACKETT_API_URL": "$LOCAL_BIND_ADDRESS"
}
EOF

  # Write to .env file
  echo "Saving to $OUTPUT_ENV_FILE..."
  cat <<EOF > "$OUTPUT_ENV_FILE"
JACKETT_PORT=$PORT
JACKETT_API_KEY=$API_KEY
JACKETT_INSTANCE_ID=$INSTANCE_ID
JACKETT_API_URL=$LOCAL_BIND_ADDRESS
EOF

  echo "Data saved successfully."
else
  echo "Error: $CONFIG_FILE does not exist."
  exit 1
fi

# Start the Telegram bot
echo "Starting Telegram bot..."
python /bot/bot.py

# Prevent script from exiting (optional, for debugging or container to remain active)
tail -f /dev/null
