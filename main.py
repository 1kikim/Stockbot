import os
import datetime
import json
import requests

# pykrx 호출 전 KRX 환경변수 체크
krx_id = os.environ.get("KRX_ID")
krx_pw = os.environ.get("KRX_PW")

if not krx_id or not krx_pw:
    print("⚠️ 경고: KRX_ID 또는 KRX_PW가 Secrets에 설정되지 않았습니다.")

from pykrx import stock
import anthropic

now = datetime.datetime.now()
today_str = now.strftime("%Y%m%d")
past_str = (now - datetime.timedelta(days=7)).strftime("%Y%m%d")

print(f"Data processing started for today: {today_str}, past: {past_str}")

def get_top10(date_str, market):
    try:
        target_date = stock.get_nearest_business_day_in_a_week(date_str)
        df = stock.get_market_cap_by_ticker(target_date, market=market)
        if df is None or df.empty:
            print(f"Empty data returned for {market} on {target_date}")
            return []
        
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

# 시총 데이터 수집
kospi_today = get_top10(today_str, "KOSPI")
kosdaq_today = get_top10(today_str, "KOSDAQ")
kospi_past = get_top10(past_str, "KOSPI")
kosdaq_past = get_top10(past_str, "KOSDAQ")

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

print("Requesting Claude API...")
# 최신 Claude 모델 적용
response = client.messages.create(
    model="claude-3-5-sonnet-latest",
    max_tokens=1500,
    messages=[{"role": "user", "content": prompt}]
)

report = response.content[0].text

print("Sending Telegram message...")
send_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
res = requests.post(send_url, data={"chat_id": telegram_chat_id, "text": report})
print(f"Telegram response status: {res.status_code}")
