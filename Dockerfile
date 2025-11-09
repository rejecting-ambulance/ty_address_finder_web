FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 工作目錄
WORKDIR /app

# 安裝系統套件，包含 unzip 與中文字型
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget unzip fonts-noto-cjk python3 \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libgbm1 libgtk-3-0 \
    libx11-6 libxcomposite1 libxdamage1 libxrandr2 libasound2 libxtst6 libxss1 \
    libpangocairo-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# 下載並安裝 Chrome-for-Testing 與相對應的 chromedriver
RUN set -eux; \
    wget -qO /tmp/versions.json https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json; \
    python3 - <<'PY'
import json, os, sys
with open('/tmp/versions.json') as f:
    j = json.load(f)
# 計算適用 linux64 的 Stable 頻道下載資料
stable = j.get('channels', {}).get('Stable', {}).get('downloads', {})
def pick_url(obj_name):
    # downloads contains lists of dicts like {'platform':'linux64','url':...}
    items = stable.get(obj_name, [])
    for it in items:
        if isinstance(it, dict):
            # prefer linux64 platform
            if it.get('platform') == 'linux64' and it.get('url'):
                return it['url']
    # fallback: return first url found
    for it in items:
        if isinstance(it, dict) and it.get('url'):
            return it.get('url')
    return ''
chrome_url = pick_url('chrome')
driver_url = pick_url('chromedriver')
if not chrome_url:
    print('ERROR: could not find chrome url', file=sys.stderr)
    sys.exit(2)
print('chrome:', chrome_url)
print('driver:', driver_url)
os.system(f'wget -qO /tmp/chrome.zip "{chrome_url}"')
os.system('unzip -q /tmp/chrome.zip -d /opt/')
# move extracted folder to /opt/chrome (pattern chrome-*) using Python to avoid shell quoting issues
import glob, shutil
dirs = glob.glob('/opt/chrome-*')
if dirs:
    src = dirs[0]
    try:
        if os.path.exists('/opt/chrome'):
            shutil.rmtree('/opt/chrome')
        os.rename(src, '/opt/chrome')
    except Exception:
        pass
os.symlink('/opt/chrome/chrome', '/usr/bin/google-chrome-stable')
if driver_url:
    os.system(f'wget -qO /tmp/chromedriver.zip "{driver_url}"')
    os.system('unzip -q /tmp/chromedriver.zip -d /opt/chromedriver')
    # find chromedriver binary recursively and move to /usr/local/bin
    for root, _, files in os.walk('/opt/chromedriver'):
        for name in files:
            if name == 'chromedriver':
                src = os.path.join(root, name)
                try:
                    shutil.copy(src, '/usr/local/bin/chromedriver')
                    os.chmod('/usr/local/bin/chromedriver', 0o755)
                except Exception:
                    pass
PY

# 複製 requirements 並安裝 Python 套件
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# 複製應用程式原始碼
COPY . /app

# 環境變數，點出 Chrome binary 位置
ENV CHROME_BIN=/opt/chrome/chrome
ENV CHROME_LOG_FILE=/dev/null
ENV PORT=8080

# 非 root 使用者
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# 使用 gunicorn 作為生產環境的 server，綁定 app:app
ENTRYPOINT ["gunicorn"]
CMD ["--workers=1", "--threads=8", "--timeout=0", "--bind=0.0.0.0:8080", "app:app"]
