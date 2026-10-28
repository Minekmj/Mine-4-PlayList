import re
from youtube_transcript_api import YouTubeTranscriptApi

from src.download.trans import papago_translate

def batch_translate_subtitles(texts: list[str], source_lang: str) -> list[str]:
    translated_results = []
    chunk_size = 15

    for i in range(0, len(texts), chunk_size):
        chunk = texts[i:i + chunk_size]
        combined_text = "\n".join(chunk)

        res = papago_translate(combined_text, source=source_lang, target="ko")
        split_res = [line.strip() for line in res.split("\n")]

        if len(split_res) == len(chunk):
            translated_results.extend(split_res)
        else:
            for line in chunk:
                translated_results.append(papago_translate(line, source=source_lang, target="ko"))

    return translated_results

def srt_time(sec: float) -> str:
    h, rem = divmod(int(sec), 3600)
    m, s = divmod(rem, 60)
    ms = int((sec % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def clean_text(text: str) -> str:
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_and_translate_srt(video_id: str, srt_path: str):
    try:
        try:
            t_list = YouTubeTranscriptApi().list(video_id)
        except AttributeError:
            t_list = YouTubeTranscriptApi.list_transcripts(video_id)

        manual_transcripts = [t for t in t_list if not t.is_generated]
        if not manual_transcripts:
            return

        transcript = None
        source_lang = "ja"

        for pref in ["ko", "ja", "en"]:
            for t in manual_transcripts:
                if t.language_code.lower().startswith(pref):
                    transcript = t
                    source_lang = pref
                    break
            if transcript:
                break

        if not transcript:
            transcript = manual_transcripts[0]
            source_lang = transcript.language_code[:2].lower()

        raw_data = transcript.fetch()
        subtitles = []
        for d in raw_data:
            txt = getattr(d, "text", None) if not isinstance(d, dict) else d.get("text", "")
            start = getattr(d, "start", 0) if not isinstance(d, dict) else d.get("start", 0)
            duration = getattr(d, "duration", 0) if not isinstance(d, dict) else d.get("duration", 0)

            txt = clean_text(txt or "")
            if txt:
                subtitles.append({
                    "start": start,
                    "end": start + duration,
                    "text": txt
                })

        if not subtitles:
            return

        if not source_lang.startswith("ko"):
            raw_lines = [item["text"] for item in subtitles]
            translated_lines = batch_translate_subtitles(raw_lines, source_lang=source_lang)
            for item, trans in zip(subtitles, translated_lines):
                item["text"] = trans

        with open(srt_path, "w", encoding="utf-8") as f:
            for idx, it in enumerate(subtitles, 1):
                f.write(f"{idx}\n{srt_time(it['start'])} --> {srt_time(it['end'])}\n{it['text']}\n\n")

    except Exception as e:
        print(f"자막 처리 실패: {e}")