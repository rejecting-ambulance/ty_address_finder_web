# app.py
from flask import Flask, request, jsonify, render_template
import logging
import os
import atexit
import time
import requests
import threading

from core import (
    setup_chrome_driver,
    search_address,
    simplify_address,
    format_simplified_address,
    remove_ling_with_condition,
    process_no_result_address,
)

app = Flask(__name__)

# 配置變數
CHROME_TIMEOUT = int(os.getenv('CHROME_TIMEOUT', '20'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))

    
# 初始化日誌，確保在 Cloud Run 中能看到輸出
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger('selenium').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# 在應用程式啟動時預先初始化 WebDriver (單例模式)
# Cloud Run 會在容器首次啟動時執行此段，並在容器重用時跳過
# 這樣可以減少每個請求的啟動延遲。
try:
    _driver_instance = None
    _wait_instance = None
    # 不在 import 時立即初始化 driver，改為 lazy 初始化
    #_driver_instance, _wait_instance = setup_chrome_driver()
except Exception as e:
    logging.error(f"Failed to setup Chrome driver on app startup: {e}")


@app.route('/')
def index():
    """
    渲染一個簡單的 HTML 頁面，用於用戶輸入地址和顯示結果。
    """
    return render_template('index.html')


@app.route('/search_address_api', methods=['GET'])
def api_search_address():
    """
    API 端點，接收地址查詢並返回格式化後的結果。
    """
    '''
    待處理錯誤地址
    1，too short>OK
    義民路10000號>OK
    中壢屈舊明里義民路10000號 not OK
    舊明里義民路120   not OK
    中壢義民路120號   not OK
    縣府路 not OK(太短無法查詢)
    '''

    global _driver_instance, _wait_instance

    address_query = request.args.get('address', '').strip()
    logging.info(f"Received API request for address: '{address_query}'")
    
    # 確保 driver 和 wait 已經初始化
    if not _driver_instance or not _driver_instance.session_id:
        logging.warning("WebDriver session invalid, recreating...")
        _driver_instance, _wait_instance = setup_chrome_driver()
            
    try:
        data_address, shorter_address, last_address = simplify_address(address_query)
        logging.info(f"Simplified for query: {shorter_address}")
        result_address = search_address(_driver_instance, _wait_instance, shorter_address)

        full_address_result = ""
        simplified_result = ""

        if result_address == "找不到結果":
            full_address_result = "查無結果"
            #simplified_result = process_no_result_address(data_address)
            simplified_result = "查無結果"

            response_data = {
                "simplified_address": simplified_result,
                "formatted_simplified_address": full_address_result, 
                "status": "no_result"
            }
            return jsonify(response_data), 200
        
        elif result_address == "網站錯誤":
            return jsonify({"error": "網站暫時無法使用，請稍後再試"}), 503

        elif result_address == "未提供地址":
            return jsonify({"error": "請提供 'address' 參數"}), 400
        
        elif result_address == "請提供完整地址":
            return jsonify({"error": "地址長度過短，請提供更完整的地址"}), 400
            
        else:
            full_address_result = f'桃園市{result_address}{last_address}'
            full_address_result = format_simplified_address(full_address_result)
            simplified_result = remove_ling_with_condition(full_address_result)

            response_data = {
                "simplified_address": simplified_result,
                "formatted_simplified_address": full_address_result, 
                "status": "success" if full_address_result.startswith("桃園市") else "no_result"
            }

            logging.info(f"Successfully processed address '{address_query}'. Result: {response_data}")
            return jsonify(response_data), 200

    except Exception as e:
        logging.error(f"Error processing address '{address_query}': {e}", exc_info=True)
        return jsonify({"error": f"處理地址時發生錯誤: {e}"}), 500


@app.route('/_health')
def health_check():
    if _driver_instance and _wait_instance:
        try:
            # 簡單測試 WebDriver 是否正常
            _driver_instance.current_url
            return jsonify({"status": "healthy"}), 200
        except:
            return jsonify({"status": "unhealthy"}), 500
    return jsonify({"status": "initializing"}), 503


# 新增：在每個 worker 第一次請求前初始化一次（更安全於 Gunicorn）
@app.before_request
def initialize_driver():
    global _driver_instance, _wait_instance
    if _driver_instance and getattr(_driver_instance, "session_id", None):
        return
    try:
        _driver_instance, _wait_instance = setup_chrome_driver()
        logging.info("WebDriver initialized in worker.")
    except Exception as e:
        logging.error(f"Failed to initialize WebDriver in worker: {e}")


@app.route('/ping')
def ping():
    return "pong"

def keep_alive():
    """定期 ping 自己以防止冷啟動"""
    session = requests.Session()
    port = os.getenv("PORT", "8080")
    url = os.getenv("SELF_URL", f"http://localhost:{port}/ping")
    interval = int(os.getenv("KEEPALIVE_INTERVAL", "30"))

    while True:
        try:
            r = session.get(url, timeout=5)
            logging.info(f"[KeepAlive] Pinged {url} ({r.status_code})")
        except Exception as e:
            logging.warning(f"[KeepAlive] Error: {e}")
        time.sleep(interval)



# import atexit
def cleanup():
    global _driver_instance
    if _driver_instance:
        try:
            _driver_instance.quit()
        except:
            pass

atexit.register(cleanup)


# Cloud Run 會使用 PORT 環境變數來決定服務監聽的端口
if __name__ == '__main__':

    # 啟動防冷啟動的背景執行緒
    threading.Thread(target=keep_alive, daemon=True).start()

    # 在本地開發環境運行時使用，Cloud Run 會透過 Gunicorn 啟動
    app.run(host='0.0.0.0', port=8080)

