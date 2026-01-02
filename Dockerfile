# ==========================================
# Giai đoạn 1: Build usque (Giữ nguyên)
# ==========================================
FROM golang:1.24.1 AS builder-usque
RUN apt-get update && apt-get install -y git
WORKDIR /app
RUN git clone https://github.com/tungns1207/usque.git .
RUN go mod download
RUN go build -o usque -ldflags="-s -w" .

# ==========================================
# Giai đoạn 2: Build masque-plus (Giữ nguyên)
# ==========================================
FROM golang:1.24.1 AS builder-masque
RUN apt-get update && apt-get install -y git
WORKDIR /app
RUN git clone https://github.com/ircfspace/masque-plus.git .
RUN go mod download
RUN go build -o masque-plus .

# ==========================================
# Giai đoạn 3: Final Image (ĐÃ CẬP NHẬT GECKODRIVER 0.36.0)
# ==========================================
FROM accetto/ubuntu-vnc-xfce-firefox-g3:latest

# Chuyển sang root để cài đặt phần mềm
USER root

# 1. Cài đặt Python, PIP và các công cụ hỗ trợ
RUN apt-get update && apt-get install -y \
    ca-certificates \
    tcpdump \
    curl \
    iproute2 \
    net-tools \
    vim \
    sudo \
    python3-pip \
    wget \
    unzip \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 2. Cài đặt Selenium
RUN pip3 install selenium --break-system-packages --ignore-installed

# 3. Cài đặt undetected-geckodriver để bypass bot detection
COPY --chown=1001:0 undetected_geckodriver ./undetected_geckodriver
RUN pip3 install -e ./undetected_geckodriver --break-system-packages
# Đã sửa từ v0.34.0 -> v0.36.0 để tương thích Firefox mới nhất
RUN wget https://github.com/mozilla/geckodriver/releases/download/v0.36.0/geckodriver-v0.36.0-linux64.tar.gz \
    && tar -xvzf geckodriver-v0.36.0-linux64.tar.gz \
    && chmod +x geckodriver \
    && mv geckodriver /usr/local/bin/ \
    && rm geckodriver-v0.36.0-linux64.tar.gz

# 4. Cấu hình quyền Sudo
RUN echo "headless ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup thư mục làm việc
WORKDIR /home/headless/tools

# 5. Copy file binary
COPY --from=builder-usque --chown=1001:0  /app/usque ./usque
COPY --from=builder-masque --chown=1001:0 /app/masque-plus ./masque-plus

# 6. Copy Script Python
COPY --chown=1001:0 youtube_loop_firefox.py ./youtube_loop_firefox.py

# Cấp quyền thực thi
RUN chmod +x ./usque ./masque-plus

# Tạo shortcut Desktop
RUN mkdir -p /home/headless/Desktop && \
    echo "[Desktop Entry]\nVersion=1.0\nType=Application\nName=Traffic Tools\nExec=xfce4-terminal --working-directory=/home/headless/tools\nIcon=utilities-terminal\nTerminal=false\nStartupNotify=false" > /home/headless/Desktop/tools.desktop \
    && chmod +x /home/headless/Desktop/tools.desktop

# Fix quyền sở hữu
RUN chown -R 1001:0 /home/headless /dockerstartup

# Quay về user mặc định
USER 1001