import requests

session = requests.Session() if requests else None
if session:
    session.headers.update({
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://papago.naver.com/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    })


def papago_translate(text: str, source: str = "ja", target: str = "ko") -> str:
    if not session or not text.strip():
        return text

    url = "https://papago.naver.com/api/text/translation"
    payload = {
        "source": source,
        "target": target,
        "text": text,
        "dict": "true",
        "useGlossary": "false",
        "honorific": "false",
        "dictDisplay": "30",
    }

    try:
        response = session.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            translated_text = data.get("translatedText")
            if not translated_text and "message" in data:
                translated_text = data.get("message", {}).get("result", {}).get("translatedText")

            if translated_text:
                return translated_text
        return text
    except Exception as e:
        print(f"파파고 번역 에러: {e}")
        return text