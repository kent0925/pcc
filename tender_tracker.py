import requests
from bs4 import BeautifulSoup
import json
import time

# ⚠️ 填入您剛才部署的 GAS Web App URL
GAS_URL = "https://script.google.com/macros/s/AKfycbwWNuc5yGNFJ5erxtpIY_MQHpYSUzUgPXpn7KJ-TCmRBy0pwOrdmOBSnFiIjPgEmhTT/exec"

def scrape_pcc_tender():
    # 這裡以搜尋結果頁面為例 (實務上需填入政府採購網的查詢結果 URL)
    target_url = "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/readNoticeAll?searchType=basic&..."
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # 1. 取得網頁內容
    response = requests.get(target_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # 2. 定位標案表格 (依據政府採購網當前結構，通常在名為 'table_T01' 的表格內)
    tenders = soup.select('tr.list_tpl') # 這是範例 Selector，需依實際頁面微調

    for tender in tenders:
        cols = tender.find_all('td')
        if len(cols) > 5:
            # 3. 封裝資料物件
            payload = {
                "id": cols[1].text.strip(),       # 案號
                "title": cols[2].text.strip(),    # 標案名稱
                "org": cols[3].text.strip(),      # 招標機關
                "city": cols[4].text.strip(),     # 縣市 (例如: [台北市])
                "budget": cols[5].text.strip(),   # 預算金額 (帶逗號的字串)
                "reason": "投標廠商不足三家"        # 或是從網頁解析
            }

            # 4. 推送到 GAS (這就是 CL3 邏輯的核心：Clean & Load)
            try:
                post_res = requests.post(GAS_URL, data=json.dumps(payload))
                print(f"案號 {payload['id']} 推送結果: {post_res.text}")
            except Exception as e:
                print(f"推送失敗: {e}")
            
            time.sleep(1) # 法律建議：務必加上延遲，避免干擾機關主機

if __name__ == "__main__":
    scrape_pcc_tender()
