import os
import json
import time

IS_GET = True

if IS_GET:
    try:
        from src.download.trans import papago_translate
    except:
        pass

GLOBAL_TARGET = "ko"
GLOBAL_FILE = "./src/global_py/globals.json"

GLOBAL_TEXTS = {
    "ko": "Malgun Gothic",
    "ja": "Meiryo",
    "en": "Arial",
    "cn": "Microsoft YaHei",
}
GLOBAL_FONT = ""

DATA = {}
TARGET_CACHE = {}


def load_translations():
    global DATA, TARGET_CACHE, GLOBAL_FONT, GLOBAL_TARGET
    
    GLOBAL_FONT = GLOBAL_TEXTS[GLOBAL_TARGET]
    if os.path.exists(GLOBAL_FILE):
        try:
            with open(GLOBAL_FILE, "r", encoding="UTF-8") as f:
                DATA = json.load(f)
        except json.JSONDecodeError:
            DATA = {}
    
    TARGET_CACHE = {
        k: v.get(GLOBAL_TARGET, k) 
        for k, v in DATA.items() 
        if isinstance(v, dict)
    }

load_translations()


def global_text(text: str) -> str:
    translated = TARGET_CACHE.get(text)
    if translated is not None:
        return translated

    if IS_GET:
        if GLOBAL_TARGET == "ko":
            translations = {
                "ko": text,
                "ja": papago_translate(text, "ko", "ja"),
                "en": papago_translate(text, "ko", "en"),
                "cn": papago_translate(text, "ko", "zh-CN"),
            }
            
            DATA[text] = translations
            TARGET_CACHE[text] = translations.get(GLOBAL_TARGET, text)

            with open(GLOBAL_FILE, "w", encoding="UTF-8") as f:
                json.dump(DATA, f, ensure_ascii=False, indent=4)
                
            time.sleep(0.15)
            return TARGET_CACHE[text]

    return text

def set_target(target: str):
    global GLOBAL_TARGET
    GLOBAL_TARGET = target
    
def get_target():
    global GLOBAL_TARGET
    return GLOBAL_TARGET

def get_font():
    global GLOBAL_FONT
    return GLOBAL_FONT

def Change_Data(data: dict):
    DATA.update(data)
    with open(GLOBAL_FILE, "w", encoding="UTF-8") as f:
        json.dump(DATA, f, ensure_ascii=False, indent=4)


# 데이터 정리 용
if __name__ == "__main__":
    corrections = {
    }
    Change_Data(corrections)