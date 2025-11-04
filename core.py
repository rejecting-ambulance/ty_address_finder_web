# core.py
import re
import os
import logging

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException


def setup_chrome_driver():
    options = Options()

    # --- Headless 模式設定 ---
    options.add_argument('--headless=new')  # 啟用新版無頭模式，模擬真實瀏覽器但不開視窗
    options.add_argument('--disable-gpu')   # 關閉 GPU 加速，避免在部分環境下造成錯誤
    options.add_argument('--no-sandbox')    # 解除沙盒限制（Linux/Docker 無權限環境必加）
    options.add_argument('--disable-dev-shm-usage')  # 避免 /dev/shm 空間不足導致崩潰（Docker 常見）
    options.add_argument("--disable-software-rasterizer")  # 關閉軟體光柵化，提升效能
    options.add_argument('--window-size=1920,1080')  # 指定視窗大小，確保頁面元素完整載入可見

    # --- 日誌與自動化提示設定 ---
    # 排除特定開關，以隱藏「Chrome 正在受自動化控制」提示及多餘的 console log
    options.add_experimental_option(
        'excludeSwitches', 
        ['enable-logging', 'enable-automation']
    )

    # 關閉 Chrome 自動化擴展功能（減少被網站偵測的機率）
    options.add_experimental_option('useAutomationExtension', False)

    # --- 系統級日誌抑制設定 ---
    # 將 Chrome 的內部 log 輸出導向無效位置（在 container 使用 /dev/null）
    if os.name == 'nt':
        os.environ['CHROME_LOG_FILE'] = 'NUL'
    else:
        os.environ['CHROME_LOG_FILE'] = '/dev/null'

    # 降低 Selenium 與 urllib3 的日誌輸出層級，只顯示警告以上訊息
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

    # 建立 WebDriver 物件
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 20)  # 設置等待時間為20秒
    return driver, wait



def wait_mask_cycle(driver, mask_class='ext-el-mask', timeout=20):
    """
    等待遮罩出現再消失，用於等待查詢完成
    """
    try:    # Step 1. 等待遮罩出現
        WebDriverWait(driver, timeout/2).until(
            EC.presence_of_element_located((By.CLASS_NAME, mask_class))
        )
        #print("[INFO] 遮罩已出現，開始等待消失...")

    except TimeoutException:
        logging.warning("Query mask did not appear.")
        #print("[WARN] 查詢遮罩未出現（可能瞬間出現又消失）")

    # Step 2. 等待遮罩消失
    WebDriverWait(driver, timeout).until_not(
        EC.presence_of_element_located((By.CLASS_NAME, mask_class))
    )
    logging.info("Query mask has disappeared.")
    #print("[INFO] 遮罩已消失，查詢完成。")

    
def search_address(driver, wait, address):
    """
    使用 Selenium 訪問地址查詢網站，輸入地址並獲取結果。
    """
    logging.info("Switch to Core.")
    
    if not address:     #例外處理
        logging.warning("No address provided in the request.")
        return "未提供地址"
    elif len(address) < 3 or re.fullmatch(r'\d+', address):
        logging.warning("Provided address is too short.")
        return "請提供完整地址"


    try:    # 可查詢地址，執行地址查詢
        logging.info(f"Start searching: {address}")
        driver.get('https://addressrs.moi.gov.tw/address/index.cfm?city_id=68000')
        address_box = wait.until(EC.presence_of_element_located((By.ID, 'FreeText_ADDR')))
        submit_button = driver.find_element(By.ID, 'ext-gen51')

        address_box.clear()
        address_box.send_keys(address)
        submit_button.click()
        
        wait_mask_cycle(driver)
        
        try:
            result = driver.find_element(By.XPATH, '//*[@id="ext-gen111"]/div/table/tbody/tr/td[2]/div')
            logging.info(f"Search result found: {result.text.strip()}")
            return result.text.strip()
        
        except NoSuchElementException as e:
            logging.warning(f"Result element not found for address '{address}': {e}")
            return "找不到結果"
        
    except Exception as e:
        logging.error(f"Error during search_address for '{address}': {e}")
        #raise RuntimeError(f"Error searching address: {e}")
        return "網站錯誤"

def simplify_address(address):
    """
    將地址簡化為：去除里、鄰與號後的文字，並將 '-' 替換為 '之'。
    回傳：(原地址, 簡化地址, 後綴)
    """
    original_address = address  # 保留原始輸入

    # 移除「區」之後的 XX里（保留前後），避免誤刪區名
    address = re.sub(r'([\u4e00-\u9fff]{1,5}區)[\u4e00-\u9fff]{1,2}里', r'\1', address)
    # 移除 XXX鄰（1~3位數）但保留後面的地址（若有），可加入 lookahead 或結合 word boundary
    address = re.sub(r'(\d{1,3})鄰', '', address)

    # 將簡化地址中的 '-' 取代為 '之'
    address = address.replace('-', '之')

    # 處理號後的尾端文字
    split_chars = ['號', '及', '、', '.']
    split_indices = [(address.find(c), c) for c in split_chars if address.find(c) != -1]

    if split_indices:
        split_indices.sort()
        index, char = split_indices[0]

        if char == '號':
            simplified = address[:index + 1]
            suffix = address[index + 1:]
        else:
            simplified = address[:index]
            suffix = address[index:]
    else:
        simplified = address
        suffix = ''
    
    #print(f"原地址: {original_address}, 簡化地址: {simplified}, 後綴: {suffix}")
    return original_address.strip(), simplified.strip(), suffix.strip()


def fullwidth_to_halfwidth(text):
    """
    將全形字元轉換為半形字元。
    """
    half_text = ''
    for char in text:
        code = ord(char)
        if code == 0x3000: # 全形空格
            code = 0x0020 # 半形空格
        elif 0xFF01 <= code <= 0xFF5E: # 全形字元範圍
            code -= 0xFEE0 # 轉換為半形
        half_text += chr(code)
    return half_text


def format_simplified_address(addr):
    '''
    結果格式化：
    1. 數字轉半形
    2. 去除空格
    3. 將「-」轉回「之」
    4. 去除「0」開頭的鄰編號，如 003鄰 ➜ 3鄰
    5. 阿拉伯數字轉中文段號（1~9段）
    '''    
    
    # 數字轉半形
    addr = fullwidth_to_halfwidth(addr)
    addr = addr.replace(' ', '')  # 去除空格
    addr = addr.replace('-', '之')  # 將「-」轉回「之」
    addr = addr.replace(',', '，')  # 半形「,」轉回「，」

    # 去除「0」開頭的鄰編號，如 003鄰 ➜ 3鄰
    addr = re.sub(r'(\D)0*(\d+)鄰', r'\1\2鄰', addr)

    # 阿拉伯數字轉中文段號（1~9段）
    num_to_chinese = {'1': '一', '2': '二', '3': '三', '4': '四', '5': '五',
                      '6': '六', '7': '七', '8': '八', '9': '九'}

    def replace_road_section(match):
        num = match.group(1)
        return num_to_chinese.get(num, num) + '段'

    addr = re.sub(r'(\d)段', replace_road_section, addr)

    return addr.strip()


def remove_ling_with_condition(full_address):
    """
    刪除「里」與「鄰」間文字（含鄰），除非有特殊條件。
    """
    return re.sub(r'(里).*?鄰', r'\1', full_address)


def process_no_result_address(original_address):
    """
    處理查無結果的地址：如果原地址有「里」，則將原地址作為結果返回，否則返回「查詢失敗」。
    """
    if "里" in original_address:
        return original_address
    else:
        return "查詢失敗"