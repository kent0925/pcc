import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import os
import json
import time
import logging

# 設定日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 從 GitHub Secrets 讀取環境變數
GAS_URL = os.getenv('GAS_URL')

def get_session():
    """建立帶有重試機制的 requests session"""
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    })
    return session

def run():
    logger.info("--- [步驟 1] 啟動爬蟲任務 ---")
    
    if not GAS_URL:
        logger.error("❌ 未設定 GAS_URL 環境變數，無法執行資料推送。")
        return

    # 目標：政府電子採購網 - 每日招標公告
    # 修改策略：D0001 錯誤通常代表需要 Session 或 Referer
    home_url = "https://web.pcc.gov.tw/"
    target_url = "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/readNoticeAll"
    
    session = get_session()
    
    try:
        # [步驟 1.1] 先訪問首頁以取得 Cookies (建立 Session)
        logger.info(f"正在連線至首頁以建立 Session: {home_url}")
        session.get(home_url, timeout=30)
        
        # [步驟 1.2] 設定 Referer 並訪問目標頁面
        session.headers.update({'Referer': home_url})
        
        logger.info(f"正在連線至目標頁面: {target_url}")
        res = session.get(target_url, timeout=30)
        res.raise_for_status() # 檢查 HTTP 狀態碼
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 尋找表格列 (根據政府網站結構)
        tenders = soup.select('tr.list_tpl') 
        
        logger.info(f"網頁回應狀態: {res.status_code}, 內容長度: {len(res.text)}")
        
        if not tenders:
            logger.warning("💡 目前網頁上找不到 'tr.list_tpl' 元素。")
            # 記錄部分 HTML 以供除錯 (前 1000 字)
            logger.debug(f"網頁內容快照: {res.text[:1000]}...")
            
            # 嘗試檢查是否有其他提示訊息
            error_msg = soup.select_one('.error_msg')
            if error_msg:
                logger.info(f"網站訊息: {error_msg.get_text(strip=True)}")
            return

        logger.info(f"✅ 找到 {len(tenders)} 筆標案，開始處理...")

        count = 0
        for row in tenders:
            try:
                cols = row.find_all('td')
                # 防呆檢查：確保欄位數量足夠
                if len(cols) < 5: 
                    continue
                
                # 解析並清洗資料
                record_id = cols[1].get_text(strip=True)
                title = cols[2].get_text(strip=True)
                org = cols[3].get_text(strip=True)
                city = cols[4].get_text(strip=True)
                budget_str = cols[5].get_text(strip=True)
                
                # 簡單過濾或處理
                payload = {
                    "id": record_id,
                    "title": title,
                    "org": org,
                    "city": city,
                    "budget": budget_str, 
                    "reason": "流標/廢標" 
                }
                
                # 推送至 GAS
                post_res = session.post(GAS_URL, data=json.dumps(payload))
                if post_res.status_code == 200:
                    logger.info(f"✅ 標案 {record_id} 推送成功")
                    count += 1
                else:
                    logger.error(f"❌ 標案 {record_id} 推送失敗: {post_res.status_code} - {post_res.text}")
                
                # 避免對 GAS 或目標網站造成過大負擔
                time.sleep(0.5) 

            except Exception as row_error:
                logger.error(f"⚠️ 解析單筆資料時發生錯誤: {row_error}")
                continue
        
        logger.info(f"--- [結束] 共成功推送 {count} 筆資料 ---")

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ 網路請求錯誤: {e}")
    except Exception as e:
        logger.error(f"❌ 執行期間發生未預期錯誤: {e}")

if __name__ == "__main__":
    run()
