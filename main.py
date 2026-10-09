import datetime
import json
import os
import requests
import anthropic
from pykrx import stock

now = datetime.datetime.now()
today_str = now.strftime("%Y%m%d")
past_str = (now - datetime.timedelta(days=7)).strftime("%Y%m%d")

def get_top10(date_str, market):
    try:
        df = stock.get_market_cap_by_ticker(date_str, market=market)
        df = df.sort_values(by="시가총액", ascending=False).head(10)
        result = []
        for rank, (ticker, row) in enumerate(df.iterrows(), 1):
            name = stock.get_market_ticker_name(ticker)
            result.append({
                "rank": rank,
                "name": name,
                "market_cap_okrw": round(int(row["시가총액"]) / 100000000, 1),
                "price": int(row["종가"])
            })
        return result
    except Exception as e:
        print(f"Error fetching {market} for {date_str}: {e}")
        return []

kospi_today = get_top10(today_str, "KOSPI")
kosdaq_today = get_top10(today_str, "KOSDAQ")
kospi_past = get_top10(past_str, "KOSPI")
kosdaq_past = get_top10(past_str, "KOSDAQ")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

prompt = f"""
당신은 증시 전문 분석가입니다. 오늘({today_str}) 코스피/코스닥 시가총액 Top 10 정보와 일주일 전({past_str}) 대비 변화를 분석해 텔레그램 메시지용 리포트를 작성해 주세요.

[오늘 코스피 Top10]
{json.dumps(kospi_today, ensure_ascii=False)}

[7일 전 코스피 Top10]
{json.dumps(kospi_past, ensure_ascii=False)}

[오늘 코스닥 Top10]
{json.dumps(kosdaq_today, ensure_ascii=False)}

[7일 전 코스닥 Top10]
{json.dumps(kosdaq_past, ensure_ascii=False)}

[작성 가이드라인]
1. 오늘 기준 코스피 & 코스닥 시총 Top 10 순위와 시가총액(억 원)을 깔끔하게 요약할 것.
2. 지난주(7일 전) 대비 순위 상승/하락, 신규 Top 10 진입 종목 등 주간 변동 사항을 한눈에 알기 쉽게 이모지와 함께 강조할 것.
3. 모바일(텔레그램) 화면에서 읽기 좋은 가독성으로 작성할 것.
"""

# 최신 지원 모델인 claude-sonnet-5-5 로 적용
response = client.messages.create(
    model="claude-sonnet-5-5",
    max_tokens=1500,
    messages=[{"role": "user", "content": prompt}]
)

report = response.content[0].text

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
requests.post(send_url, data={"chat_id": CHAT_ID, "text": report})
