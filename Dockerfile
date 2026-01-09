# ==========================================
# Stage 1: Build usque 
# ==========================================
FROM golang:1.24.1 AS builder-usque
RUN apt-get update && apt-get install -y git
WORKDIR /app
RUN git clone https://github.com/tungns1207/usque.git .
RUN go mod download
RUN go build -o usque -ldflags="-s -w" .

# ==========================================
# Stage 2: Build masque-plus 
# ==========================================
FROM golang:1.24.1 AS builder-masque
RUN apt-get update && apt-get install -y git
WORKDIR /app
RUN git clone https://github.com/ircfspace/masque-plus.git .
RUN go mod download
RUN go build -o masque-plus .


# ==========================================
# Stage 3: Final Image (UPDATED GECKODRIVER 0.36.0)
# ==========================================
FROM accetto/ubuntu-vnc-xfce-firefox-g3:latest

# Switch to root to install software
USER root

# 1. Install Python, PIP, and utility tools
RUN apt-get update && apt-get install -y \
    ca-certificates \
    tcpdump \
    curl \
    iproute2 \
    iptables \
    net-tools \
    vim \
    sudo \
    python3-pip \
    wget \
    unzip \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Install Selenium
RUN pip3 install selenium --break-system-packages --ignore-installed

# 3. Install undetected-geckodriver to bypass bot detection
COPY --chown=1001:0 undetected_geckodriver ./undetected_geckodriver
RUN pip3 install -e ./undetected_geckodriver --break-system-packages
# Updated from v0.34.0 -> v0.36.0 for compatibility with the latest Firefox
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz \
    && tar -xvzf geckodriver-v0.36.0-linux64.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.36.0-linux64.tar.gz

# 4. Configure Sudo permissions
RUN echo "headless ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup working directory
WORKDIR /home/headless/tools

# 5. Copy binary files
COPY --from=builder-usque --chown=1001:0  /app/usque ./usque
COPY --from=builder-masque --chown=1001:0 /app/masque-plus ./masque-plus

COPY curl-linux-x86_64-musl-8.18.0/curl /usr/local/bin/curl

# 6. Copy Python Scripts
COPY --chown=1001:0 youtube_loop_firefox_with_proxy.py ./youtube_loop_firefox_with_proxy.py
COPY --chown=1001:0 youtube_loop_firefox_without_proxy.py ./youtube_loop_firefox_without_proxy.py
COPY --chown=1001:0 file_transfer_with_proxy.py ./file_transfer_with_proxy.py
COPY --chown=1001:0 file_transfer_without_proxy.py ./file_transfer_without_proxy.py

# Grant execution permissions
RUN chmod +x ./usque ./masque-plus

# Create Desktop shortcut
RUN mkdir -p /home/headless/Desktop && \
    echo "[Desktop Entry]\nVersion=1.0\nType=Application\nName=Traffic Tools\nExec=xfce4-terminal --working-directory=/home/headless/tools\nIcon=utilities-terminal\nTerminal=false\nStartupNotify=false" > /home/headless/Desktop/tools.desktop \
    && chmod +x /home/headless/Desktop/tools.desktop

# Fix ownership permissions
RUN chown -R 1001:0 /home/headless /dockerstartup

# Switch back to default user
USER 1001