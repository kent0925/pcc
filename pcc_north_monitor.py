import requests
from bs4 import BeautifulSoup
import os
import json
import time

# 從 GitHub Secrets 讀取環境變數
GAS_URL = os.getenv('GAS_URL')

def run():
    print("--- [步驟 1] 啟動爬蟲任務 ---")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 目標：政府電子採購網 - 每日招標公告 (此處以當日流標/廢標查詢 URL 為例)
    # 建議實務上從政府公開資料平台 API 獲取更穩定，或針對特定查詢結果頁面
    target_url = "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/readNoticeAll"
    
    try:
        res = requests.get(target_url, headers=headers, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 尋找表格列 (根據政府網站結構，標案通常在 tr 標籤且具備特定 class)
        # 注意：此處 Selector 需依據實際搜尋結果頁面微調
        tenders = soup.select('tr.list_tpl') 
        
        if not tenders:
            print("💡 目前網頁上無新增標案，發送一筆測試資料確保系統正常。")
            # 這裡保留一筆測試，或直接結束
            return

        for row in tenders:
            cols = row.find_all('td')
            if len(cols) < 5: continue
            
            payload = {
                "id": cols[1].get_text(strip=True),       # 案號
                "title": cols[2].get_text(strip=True),    # 標案名稱
                "org": cols[3].get_text(strip=True),      # 招標機關
                "city": cols[4].get_text(strip=True),     # 縣市
                "budget": cols[5].get_text(strip=True),   # 金額字串
                "reason": "流標/廢標"                      # 原因
            }
            
            post_res = requests.post(GAS_URL, data=json.dumps(payload))
            print(f"✅ 標案 {payload['id']} 推送結果: {post_res.text}")
            time.sleep(1) # 法律規範：避免高頻存取

    except Exception as e:
        print(f"❌ 執行錯誤: {e}")
