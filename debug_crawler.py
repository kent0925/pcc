"""
政府採購網 Open Data 測試腳本
用於驗證 Open Data XML API 是否可正常存取
"""

import requests
from datetime import datetime

def test_opendata():
    """測試 Open Data API"""
    
    print("=" * 50)
    print("🧪 政府採購網 Open Data 測試")
    print("=" * 50)
    
    # 計算當前期別
    today = datetime.now()
    year = today.year
    month = today.month
    period = "01" if today.day <= 15 else "02"
    
    # 上一期
    if period == "01":
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_period = f"{prev_year}{prev_month:02d}02"
    else:
        prev_period = f"{year}{month:02d}01"
    
    current_period = f"{year}{month:02d}{period}"
    
    print(f"📅 當前期別: {current_period}")
    print(f"📅 上一期別: {prev_period}")
    print()
    
    # 測試 URL
    base_url = "https://web.pcc.gov.tw/tps/tp/OpenData/downloadFile"
    
    test_files = [
        f"award_{prev_period}.xml",  # 決標公告（含流標資訊）
        f"tender_{prev_period}.xml",  # 招標公告
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for filename in test_files:
        url = f"{base_url}?fileName={filename}"
        print(f"🔍 測試: {filename}")
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            print(f"   狀態碼: {response.status_code}")
            print(f"   內容大小: {len(response.content)} bytes")
            
            if response.status_code == 200 and len(response.content) > 500:
                print(f"   ✅ 成功取得資料")
                # 顯示前 500 字元
                print(f"   前 500 字元預覽:")
                print(f"   {response.text[:500]}...")
            else:
                print(f"   ⚠️ 資料可能尚未發布或檔案過小")
                
        except Exception as e:
            print(f"   ❌ 錯誤: {e}")
        
        print()
    
    # 測試 GAS API
    print("=" * 50)
    print("🔍 測試 GAS API（唯讀）")
    gas_url = "https://script.google.com/macros/s/AKfycbwWNuc5yGNFJ5erxtpIY_MQHpYSUzUgPXpn7KJ-TCmRBy0pwOrdmOBSnFiIjPgEmhTT/exec"
    
    try:
        response = requests.get(gas_url, timeout=30)
        print(f"   狀態碼: {response.status_code}")
        print(f"   回應: {response.text[:200]}...")
        print(f"   ✅ GAS API 正常運作")
    except Exception as e:
        print(f"   ❌ 錯誤: {e}")


if __name__ == "__main__":
    test_opendata()
