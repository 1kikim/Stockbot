import os
import datetime
import json
import requests
from bs4 import BeautifulSoup
import anthropic

def get_naver_market_cap_top10(sosok=0):
    """
    네이버 증권에서 시가총액 Top 10 수집 (sosok=0: 코스피, sosok=1: 코스닥)
    KRX 아이디/비밀번호 없이 100% 안정적으로 동작합니다.
    """
    url = f"https://finance.naver.com/sise/sise_market_sum.naver?sosok={sosok}&page=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        
        table = soup.find("table", {"class": "type_2"})
        if not table:
            return []
            
        tbody = table.find("tbody")
        if not tbody:
            return []
            
        rows = tbody.find_all("tr")
        results = []
        
        for row in rows:
            cols = row.find_all("td")
            if len(cols) <= 1:
                continue
                
            rank = cols[0].text.strip()
            name = cols[1].text.strip()
            price = cols[2].text.strip().replace(",", "")
            market_cap = cols[6].text.strip().replace(",", "")
            
            if rank and name and market_cap:
                results.append({
                    "rank": int(rank),
                    "name": name,
                    "price_krw": int(price) if price.isdigit() else price,
                    "market_cap_100m_krw": int(market_cap) if market_cap.isdigit() else market_cap
                })
                
            if len(results) >= 10:
                break
                
        return results
    except Exception as e:
        print(f"Error fetching Naver Finance data (sosok={sosok}): {e}")
        return []

print("Data processing started using Naver Finance...")

# 코스피(0) / 코스닥(1) 시총 Top 10 수집
kospi_top10 = get_naver_market_cap_top10(sosok=0)
kosdaq_top10 = get_naver_market_cap_top10(sosok=1)

today_str = datetime.datetime.now().strftime("%Y-%m-%d")

# 환경 변수 검증
api_key = os.environ.get("ANTHROPIC_API_KEY")
telegram_token = os.environ.get("TELEGRAM_TOKEN")
telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID")

if not api_key:
    raise ValueError("❌ Error: ANTHROPIC_API_KEY가 Secrets에 설정되지 않았습니다.")
if not telegram_token or not telegram_chat_id:
    raise ValueError("❌ Error: TELEGRAM_TOKEN 또는 TELEGRAM_CHAT_ID가 Secrets에 설정되지 않았습니다.")

client = anthropic.Anthropic(api_key=api_key)

prompt = f"""
당신은 증시 전문 분석가입니다. 오늘({today_str}) 기준 코스피 및 코스닥 시가총액 Top 10 종목 정보를 바탕으로 텔레그램 리포트를 작성해 주세요.

[오늘 코스피 시총 Top 10]
{json.dumps(kospi_top10, ensure_ascii=False, indent=2)}

[오늘 코스닥 시총 Top 10]
{json.dumps(kosdaq_top10, ensure_ascii=False, indent=2)}

[작성 가이드라인]
1. 코스피와 코스닥 Top 10 순위, 종목명, 현재가(원), 시가총액(억 원)을 한눈에 알기 쉽게 요약해 주세요.
2. 주요 관심 종목 및 시가총액 규모를 직관적인 이모지와 함께 강조해 주세요.
3. 텔레그램 모바일 화면에서 읽기 좋은 가독성으로 깔끔하게 작성해 주세요.
"""

print("Requesting Claude API...")
# 공식 고정 모델명 사용
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1500,
    messages=[{"role": "user", "content": prompt}]
)

report = response.content[0].text

print("Sending Telegram message...")
send_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
res = requests.post(send_url, data={"chat_id": telegram_chat_id, "text": report})
print(f"Telegram response status: {res.status_code}")
print("Successfully finished!")
