"""
政府電子採購網北部地區流標監控爬蟲（修復版）
使用政府採購網官方 Open Data XML API
資料來源：https://web.pcc.gov.tw/tps/tp/OpenData/showList

功能：
1. 從官方 Open Data 下載最新決標公告 XML
2. 解析並篩選「無法決標」（流標/廢標）案件
3. 過濾北部地區案件
4. 推送資料到 Google Apps Script
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import xml.etree.ElementTree as ET
import os
import json
import time
import logging
from datetime import datetime, timedelta

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 從 GitHub Secrets 讀取環境變數
GAS_URL = os.getenv('GAS_URL')

# 北部地區定義
NORTHERN_REGIONS = ["台北市", "臺北市", "新北市", "基隆市", "桃園市", "宜蘭縣", "新竹市", "新竹縣"]

# Open Data 基礎 URL
OPENDATA_BASE_URL = "https://web.pcc.gov.tw/tps/tp/OpenData/downloadFile"


def get_session():
    """建立帶有重試機制的 requests session"""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/xml,text/xml,*/*;q=0.9',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    })
    return session


def get_current_period():
    """
    計算當前應該抓取的 Open Data 檔案名稱
    政府採購網每月分兩期更新：01（1-15日）和 02（16-月底）
    """
    today = datetime.now()
    year = today.year
    month = today.month
    
    # 判斷是上半月還是下半月
    if today.day <= 15:
        period = "01"
    else:
        period = "02"
    
    return f"{year}{month:02d}{period}"


def get_previous_periods(num_periods=2):
    """取得最近幾期的檔案名稱（用於回補資料）"""
    periods = []
    today = datetime.now()
    
    for i in range(num_periods):
        # 每期約 15 天
        target_date = today - timedelta(days=i * 15)
        year = target_date.year
        month = target_date.month
        
        if target_date.day <= 15:
            period = "01"
        else:
            period = "02"
        
        periods.append(f"{year}{month:02d}{period}")
    
    return list(set(periods))  # 去除重複


def download_and_parse_fail_notices(session, period):
    """
    下載並解析無法決標公告 XML
    檔案格式：award_YYYYMMPP.xml（決標公告包含無法決標資訊）
    """
    # 嘗試下載決標公告（包含流標資訊）
    filename = f"award_{period}.xml"
    url = f"{OPENDATA_BASE_URL}?fileName={filename}"
    
    logger.info(f"正在下載: {url}")
    
    try:
        response = session.get(url, timeout=60)
        response.raise_for_status()
        
        if len(response.content) < 100:
            logger.warning(f"檔案 {filename} 內容過小，可能尚未發布")
            return []
        
        # 解析 XML
        root = ET.fromstring(response.content)
        
        # 收集流標案件
        fail_notices = []
        
        # 遍歷所有案件紀錄（根據政府採購網 XML 結構）
        for record in root.findall('.//record'):
            try:
                # 取得案件基本資訊
                tender_case_no = get_xml_text(record, 'tender_case_no', '')
                tender_name = get_xml_text(record, 'tender_name', '')
                org_name = get_xml_text(record, 'org_name', '')
                org_address = get_xml_text(record, 'org_address', '')
                budget_amount = get_xml_text(record, 'budget_amount', '0')
                
                # 檢查是否為無法決標（流標/廢標）
                fail_reason = get_xml_text(record, 'fail_reason', '')
                is_failed = get_xml_text(record, 'is_failed', 'N')
                
                if fail_reason or is_failed == 'Y':
                    # 判斷地區
                    city = extract_city_from_address(org_address)
                    
                    if city:  # 只收集有辨識出地區的案件
                        fail_notices.append({
                            'id': tender_case_no,
                            'title': tender_name,
                            'org': org_name,
                            'city': city,
                            'budget': clean_budget(budget_amount),
                            'reason': fail_reason or '無法決標'
                        })
                        
            except Exception as e:
                logger.warning(f"解析單筆記錄時發生錯誤: {e}")
                continue
        
        logger.info(f"從 {filename} 解析出 {len(fail_notices)} 筆無法決標案件")
        return fail_notices
        
    except requests.exceptions.RequestException as e:
        logger.error(f"下載 {filename} 失敗: {e}")
        return []
    except ET.ParseError as e:
        logger.error(f"解析 {filename} XML 失敗: {e}")
        return []


def get_xml_text(element, tag, default=''):
    """安全取得 XML 標籤文字"""
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    return default


def extract_city_from_address(address):
    """從地址中提取縣市名稱"""
    if not address:
        return ''
    
    cities = [
        "台北市", "臺北市", "新北市", "基隆市", "桃園市", 
        "新竹市", "新竹縣", "宜蘭縣", "苗栗縣",
        "台中市", "臺中市", "彰化縣", "南投縣", "雲林縣",
        "嘉義市", "嘉義縣", "台南市", "臺南市",
        "高雄市", "屏東縣", "花蓮縣", "台東縣", "臺東縣",
        "澎湖縣", "金門縣", "連江縣"
    ]
    
    for city in cities:
        if city in address:
            return city
    
    return ''


def clean_budget(budget_str):
    """清理預算金額字串，轉為數字"""
    if not budget_str:
        return 0
    # 移除所有非數字字元（保留小數點）
    cleaned = ''.join(c for c in str(budget_str) if c.isdigit() or c == '.')
    try:
        return int(float(cleaned)) if cleaned else 0
    except ValueError:
        return 0


def is_northern_region(city):
    """判斷是否為北部地區"""
    return any(region in city for region in NORTHERN_REGIONS)


def push_to_gas(session, data):
    """推送資料到 Google Apps Script"""
    if not GAS_URL:
        logger.error("❌ 未設定 GAS_URL 環境變數")
        return False
    
    try:
        response = session.post(
            GAS_URL,
            data=json.dumps(data),
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            logger.info(f"✅ 標案 {data['id']} 推送成功")
            return True
        else:
            logger.error(f"❌ 標案 {data['id']} 推送失敗: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 推送時發生錯誤: {e}")
        return False


def run():
    """主執行函數"""
    logger.info("=" * 50)
    logger.info("🚀 啟動北部地區流標監控爬蟲（Open Data 版）")
    logger.info("=" * 50)
    
    if not GAS_URL:
        logger.error("❌ 未設定 GAS_URL 環境變數，無法執行資料推送。")
        logger.info("💡 請在 GitHub Secrets 中設定 GAS_URL")
        return
    
    session = get_session()
    
    # 取得最近的期別
    periods = get_previous_periods(num_periods=2)
    logger.info(f"📅 將抓取以下期別: {periods}")
    
    total_pushed = 0
    total_northern = 0
    
    for period in periods:
        logger.info(f"\n--- 處理期別: {period} ---")
        
        # 下載並解析資料
        fail_notices = download_and_parse_fail_notices(session, period)
        
        if not fail_notices:
            logger.info(f"💡 期別 {period} 無資料或尚未發布")
            continue
        
        # 篩選北部地區
        northern_notices = [n for n in fail_notices if is_northern_region(n['city'])]
        logger.info(f"🏙️ 北部地區案件: {len(northern_notices)} 筆（總共 {len(fail_notices)} 筆）")
        
        total_northern += len(northern_notices)
        
        # 推送到 GAS
        for notice in northern_notices:
            if push_to_gas(session, notice):
                total_pushed += 1
            time.sleep(0.5)  # 避免對 GAS 造成過大負擔
    
    logger.info("\n" + "=" * 50)
    logger.info(f"📊 執行完成")
    logger.info(f"   北部地區案件: {total_northern} 筆")
    logger.info(f"   成功推送: {total_pushed} 筆")
    logger.info("=" * 50)


if __name__ == "__main__":
    run()
