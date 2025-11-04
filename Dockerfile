# ===== 基礎映像 =====
FROM python:3.11-slim

# ===== 工作目錄 =====
WORKDIR /app

# ===== 安裝系統相依套件 =====
# 包含 Chrome-for-Testing 所需依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    wget \
    unzip \
    fonts-noto-cjk \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libasound2 \
    libxtst6 \
    libxss1 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ===== 安裝最新 Chrome-for-Testing =====
RUN set -eux; \
    wget -qO /tmp/versions.json https://googlechromelabs.github.io/chrome-for-testing/latest-versions-per-platform.json; \
    CFT_URL=$(python3 -c "import json;print(json.load(open('/tmp/versions.json'))['channels']['Stable']['platforms']['linux64']['download_url'])"); \
    wget -qO /tmp/chrome-for-testing.zip "$CFT_URL"; \
    unzip -q /tmp/chrome-for-testing.zip -d /opt/; \
    mv /opt/chrome-linux64 /opt/chrome || mv /opt/chrome-* /opt/chrome; \
    ln -s /opt/chrome/chrome /usr/bin/google-chrome-stable; \
    rm -rf /tmp/*

# ===== 複製並安裝 Python 依賴 =====
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ===== 複製程式碼 =====
COPY . .

# ===== 設定環境變數 =====
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/opt/chrome/chrome
ENV CHROME_LOG_FILE=/dev/null

# ===== 建立非 root 使用者 =====
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# ===== Gunicorn 啟動命令 =====
ENTRYPOINT ["gunicorn"]
CMD ["--workers=1", "--threads=8", "--timeout=0", "--bind=0.0.0.0:8080", "app:app"]
