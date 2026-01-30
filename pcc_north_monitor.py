import requests
from bs4 import BeautifulSoup
import os
import json
import time

# 從 GitHub Secrets 讀取環境變數
GAS_URL = os.getenv('GAS_URL')

def run():
    print("--- [步驟 1] 啟動爬蟲任務 ---")
    if not GAS_URL:
        print("❌ 錯誤：找不到 GAS_URL 環境變數，請檢查 GitHub Secrets 設定。")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    # 測試用目標網址 (這是政府採購網的公告頁面)
    target_url = "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/readNoticeAll"
    
    print(f"--- [步驟 2] 正在連線至目標網站... ---")
    try:
        # 增加 timeout 避免 GitHub Actions 卡死
        res = requests.get(target_url, headers=headers, timeout=30)
        print(f"✅ 網頁回應代碼: {res.status_code}")
        
        # 建立一筆測試資料，確認 API 是通的
        test_payload = {
            "id": "DEBUG-113",
            "title": "GitHub 自動化測試標案",
            "org": "測試開發部",
            "city": "台北市",
            "budget": "888,888",
            "reason": "系統自動測試執行"
        }
        
        print("--- [步驟 3] 正在嘗試推送資料至 GAS... ---")
        post_res = requests.post(GAS_URL, data=json.dumps(test_payload))
        
        # 這裡的輸出非常重要，會告訴我們 GAS 端有沒有問題
        print(f"✅ GAS 回應內容: {post_res.text}")
        
    except Exception as e:
        print(f"❌ 執行過程中發生錯誤: {e}")

if __name__ == "__main__":
    run()
