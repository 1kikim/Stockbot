import datetime
import json
import os
import requests
import anthropic

# 네이버 증권 모바일 API (해외 서버 차단 없음)
headers = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
}

def get_naver_top10(market):
    url = f"https://m.stock.naver.com/api/stocks/marketValue/{market}?page=1&pageSize=10"
    try:
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        stocks = data.get("stocks", [])
        
        result = []
        for rank, stock in enumerate(stocks, 1):
            result.append({
                "순위": f"{rank}위",
                "종목명": stock.get("stockName"),
                "현재가": f"{stock.get('closePrice')}원",
                "시가총액": stock.get("marketValue")
            })
        return result
    except Exception as e:
        print(f"Error fetching {market} from Naver: {e}")
        return []

now_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")

kospi_today = get_naver_top10("KOSPI")
kosdaq_today = get_naver_top10("KOSDAQ")

# Claude API 호출
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

prompt = f"""
당신은 증시 전문 분석가입니다. 오늘({now_str}) 네이버 증권 기준 코스피 및 코스닥 시가총액 Top 10 정보입니다.

[코스피 Top10]
{json.dumps(kospi_today, ensure_ascii=False, indent=2)}

[코스닥 Top10]
{json.dumps(kosdaq_today, ensure_ascii=False, indent=2)}

[작성 가이드라인]
1. 오늘 기준 코스피 & 코스닥 시총 Top 10 순위, 종목명, 현재가, 시가총액을 깔끔하게 요약해 주세요.
2. 각 시장별 시가총액 상위 주요 특징을 간단히 짚어주세요.
3. 텔레그램 모바일 화면에서 보기 좋게 이모지(📊, 📈, 💡 등)를 적극 활용하여 전달력 높게 작성해 주세요.
"""

response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1500,
    messages=[{"role": "user", "content": prompt}]
)

# 텍스트 응답 안전하게 추출 (ThinkingBlock 에러 방지)
report_texts = []
for block in response.content:
    if getattr(block, 'type', '') == 'text':
        report_texts.append(block.text)

report = "\n".join(report_texts) if report_texts else "리포트 생성 실패"

# 텔레그램 전송
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if TELEGRAM_TOKEN and CHAT_ID:
    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    res = requests.post(send_url, data={"chat_id": CHAT_ID, "text": report})
    print(f"Telegram response status: {res.status_code}")
