import requests
from bs4 import BeautifulSoup

def debug_run():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    target_url = "https://web.pcc.gov.tw/prkms/tender/common/noticeAll/readNoticeAll"
    
    print(f"Fetching {target_url}...")
    try:
        res = requests.get(target_url, headers=headers, timeout=30)
        print(f"Status Code: {res.status_code}")
        
        with open("debug_pcc.html", "w", encoding="utf-8") as f:
            f.write(res.text)
        print("Saved response to debug_pcc.html")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        tenders = soup.select('tr.list_tpl')
        print(f"Found {len(tenders)} tenders with selector 'tr.list_tpl'")
        
        # Try to find ANY table rows to see if selector is just wrong
        all_trs = soup.find_all('tr')
        print(f"Total 'tr' tags found: {len(all_trs)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_run()
