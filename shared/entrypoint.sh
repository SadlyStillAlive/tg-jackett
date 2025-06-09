#!/bin/bash

# Read required environment variables
# JACKETT_URL="${JACKETT_URL:-}"
JACKETT_API_URL="${JACKETT_API_URL:-}"
JACKETT_API_KEY="${JACKETT_API_KEY:-}"
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
ENV_FILE="/app/shared/.env"

# Check required env vars
if [ -z "$JACKETT_API_URL" ]; then
  echo "Error: JACKETT_API_URL environment variable not set. Exiting."
  exit 1
fi

if [ -z "$JACKETT_API_KEY" ]; then
  echo "Error: JACKETT_API_KEY environment variable not set. Exiting."
  exit 1
fi

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
  echo "Error: TELEGRAM_BOT_TOKEN environment variable not set. Exiting."
  exit 1
fi

echo "Waiting for Jackett to be available at $JACKETT_API_URL..."
until curl --silent --fail "$JACKETT_API_URL" > /dev/null; do
  echo "Jackett is not available yet. Retrying in 5 seconds..."
  sleep 5
done
echo "Jackett is up!"

# printing the env variables on screen
echo "Writing environment variables to $ENV_FILE..."
{
  echo "JACKETT_API_URL=$JACKETT_API_URL"
  echo "JACKETT_API_KEY=$JACKETT_API_KEY"
  echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
} > "$ENV_FILE"

echo "Environment setup complete:"
cat "$ENV_FILE"

# Save to env file
mkdir -p /shared/envs
cat <<EOF > /shared/envs/.env
JACKETT_API_KEY=$JACKETT_API_KEY
JACKETT_API_URL=$JACKETT_API_URL
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
WEBHOOK_URL=$WEBHOOK_URL
EOF

# Run the bot startup script
if [ -f "/app/shared/process_config.sh" ]; then
  chmod +x /app/shared/process_config.sh
  echo "Running process_config.sh..."
  exec /app/shared/process_config.sh
else
  echo "Error: process_config.sh not found. Exiting."
  exit 1
fi


# # #!/bin/bash
# #!/bin/bash

# JACKETT_URL="https://jackett-ewy7.onrender.com"  # Replace with your actual URL
# CONFIG_ENDPOINT="$JACKETT_URL/ServerConfig.json"
# ENV_FILE="/shared/.env"

# echo "Waiting for Jackett to be available at $JACKETT_URL..."
# until curl --silent --fail "$JACKETT_URL" > /dev/null; do
#   echo "Jackett is not available yet. Retrying in 5 seconds..."
#   sleep 5
# done

# echo "Jackett is up!"

# # Attempt to fetch Jackett API key (optional)
# echo "Attempting to fetch API key from $CONFIG_ENDPOINT..."
# JACKETT_API_KEY=$(curl -s "$CONFIG_ENDPOINT" | jq -r '.APIKey')

# if [ -z "$JACKETT_API_KEY" ] || [ "$JACKETT_API_KEY" == "null" ]; then
#   echo "Failed to fetch Jackett API key automatically."
#   # Optionally set it manually here:
#   # JACKETT_API_KEY="your-manual-api-key"
# else
#   echo "Jackett API key retrieved."
# fi

# echo "Writing environment variables to $ENV_FILE..."
# echo "JACKETT_API_URL=$JACKETT_URL" > "$ENV_FILE"
# echo "JACKETT_API_KEY=$JACKETT_API_KEY" >> "$ENV_FILE"

# # Handle Telegram bot token
# if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
#   echo "Error: TELEGRAM_BOT_TOKEN not set. Exiting."
#   exit 1
# else
#   echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" >> "$ENV_FILE"
# fi

# echo "Environment setup complete:"
# cat "$ENV_FILE"

# # Run the bot startup script
# if [ -f "/shared/process_config.sh" ]; then
#   chmod +x /shared/process_config.sh
#   echo "Running process_config.sh..."
#   exec /shared/process_config.sh
# else
#   echo "Error: process_config.sh not found. Exiting."
#   exit 1
# fi


# # # List contents of Jackett config directory
# # JACKETT_APP_DIR="/config/Jackett/"
# # echo "Listing contents of directory: $JACKETT_APP_DIR"
# # if [ -d "$JACKETT_APP_DIR" ]; then
# #   ls -l "$JACKETT_APP_DIR"
# # else
# #   echo "Directory $JACKETT_APP_DIR does not exist."
# # fi

# # # Configuration file path
# # CONFIG_FILE="/config/Jackett/ServerConfig.json"

# # # Wait for Jackett config file to be generated
# # echo "Waiting for Jackett config file: $CONFIG_FILE..."
# # while [ ! -f "$CONFIG_FILE" ]; do
# #   echo "Config file not found. Retrying in 5 seconds..."
# #   sleep 10
# # done
# # echo "Config file found: $CONFIG_FILE."

# # # Run the intermediate script
# # if [ -f "/shared/process_config.sh" ]; then
# #   chmod +x /shared/process_config.sh
# #   echo "Running process_config.sh..."
# #   /shared/process_config.sh
# # else
# #   echo "process_config.sh not found. Skipping."
# # fi

# # # # Display the .env file for verification
# # # echo "Final .env file contents:"
# # # cat /shared/.env

# # # # Fetch Jackett API details
# # # echo "Fetching Jackett API details..."
# # # JACKETT_API_URL="http://jackett:9117"
# # # JACKETT_API_KEY=$(curl -s "$JACKETT_API_URL/api/v2.0/indexers/all/results/torznab/api?apikey=${JACKETT_API_KEY_ENV}")

# # # if [ -z "$JACKETT_API_KEY" ]; then
# # #   echo "Failed to fetch Jackett API key. Exiting."
# # #   exit 1
# # # fi

# # echo "-----------------------------------------"
# # echo "Jackett API URL: $JACKETT_API_URL"
# # echo "Jackett API Key: $JACKETT_API_KEY"
# # echo "-----------------------------------------"

# # # Save Jackett details to .env file
# # echo "Saving Jackett details to .env..."
# # echo "JACKETT_API_URL=$JACKETT_API_URL" > /shared/.env
# # echo "JACKETT_API_KEY=$JACKETT_API_KEY" >> /shared/.env

# # # Fetch Telegram Bot Token
# # if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
# #   echo "Telegram Bot Token not found in environment variables. Exiting."
# #   exit 1
# # fi

# # echo "-----------------------------------------"
# # echo "Telegram Bot Token: $TELEGRAM_BOT_TOKEN"
# # echo "-----------------------------------------"

# # # Save Telegram Bot Token to .env file
# # echo "Saving Telegram Bot Token to .env..."
# # echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN" >> /shared/.env

# # # Start the Telegram bot
# # echo "Starting Telegram bot..."
# # python /bot/bot.py
