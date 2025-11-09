# 基礎 Python 映像
FROM python:3.11-slim

# 避免互動式安裝
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 設定工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget unzip fonts-noto-cjk \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 libgtk-3-0 \
    libx11-6 libxcomposite1 libxdamage1 libxrandr2 libasound2 libxtst6 libxss1 \
    libpangocairo-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Chrome-for-Testing 與 Chromedriver
RUN wget -qO /tmp/cft.json https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json && \
    CHROME_URL=$(python3 -c "import json; j=json.load(open('/tmp/cft.json')); print(j['channels']['Stable']['downloads']['chrome'][0]['url'])") && \
    DRIVER_URL=$(python3 -c "import json; j=json.load(open('/tmp/cft.json')); print(j['channels']['Stable']['downloads']['chromedriver'][0]['url'])") && \
    echo "Downloading Chrome from $CHROME_URL" && \
    wget -qO /tmp/chrome.zip "$CHROME_URL" && unzip -q /tmp/chrome.zip -d /opt/ && \
    mv /opt/chrome-* /opt/chrome && \
    ln -sf /opt/chrome/chrome /usr/bin/google-chrome-stable && \
    echo "Downloading Chromedriver from $DRIVER_URL" && \
    wget -qO /tmp/chromedriver.zip "$DRIVER_URL" && unzip -q /tmp/chromedriver.zip -d /opt/chromedriver && \
    find /opt/chromedriver -type f -name 'chromedriver' -exec mv {} /usr/local/bin/chromedriver \; && \
    chmod +x /usr/local/bin/chromedriver && \
    rm -rf /tmp/*

# 安裝 Python 套件
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 複製專案程式碼
COPY . /app

# 環境變數
ENV CHROME_BIN=/opt/chrome/chrome
ENV CHROME_LOG_FILE=/dev/null
ENV PORT=8080

# 非 root 使用者
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 啟動 Gunicorn server
ENTRYPOINT ["gunicorn"]
CMD ["--workers=1", "--threads=8", "--timeout=0", "--bind=0.0.0.0:8080", "app:app"]
