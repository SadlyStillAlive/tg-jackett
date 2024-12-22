# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Install necessary dependencies for Jackett and jq
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Install Jackett
RUN echo "**** install jackett ****" && \
    mkdir -p /app/Jackett && \
    JACKETT_RELEASE=$(curl -sX GET "https://api.github.com/repos/Jackett/Jackett/releases/latest" | jq -r .tag_name) && \
    curl -o /tmp/jackett.tar.gz -L "https://github.com/Jackett/Jackett/releases/download/${JACKETT_RELEASE}/Jackett.Binaries.LinuxAMDx64.tar.gz" && \
    tar xf /tmp/jackett.tar.gz -C /app/Jackett --strip-components=1 && \
    rm /tmp/jackett.tar.gz

# Set the working directory for the bot
WORKDIR /app

# Copy bot code and requirements file into the container
COPY bot/ /app/bot
# COPY requirements.txt /app/requirements.txt
# COPY bot/bot.py /app/bot.py
# COPY bot/temp.py /app/bot.py

# Copy requirements file to the working directory
COPY requirements.txt /shared/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /shared/requirements.txt

# Ensure the entrypoint script is executable
COPY shared/entrypoint.sh /shared/entrypoint.sh
COPY shared/process_config.sh /shared/process_config.sh
RUN chmod +x /shared/entrypoint.sh
RUN chmod +x /shared/process_config.sh
    

# Expose the ports used by the bot and Jackett
EXPOSE 9117
EXPOSE 5000

# Set entrypoint script
ENTRYPOINT ["sh", "/shared/entrypoint.sh"]
