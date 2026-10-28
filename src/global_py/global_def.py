import os
import json
import time
from src.download.trans import papago_translate

#귀찮아 안 만들어 나중에 함....

IS_GET = False
GLOBAL_TARGET = "ko"
GLOBAL_FILE = "./src/global_py/globals.json"
GLOBAL_FONT = "HY견고딕"

DATA = {}
TARGET_CACHE = {}


def load_translations():
    return # 안만들어... 귀찮아

    global DATA, TARGET_CACHE
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
    return text  # 안만들어... 귀찮아
    
    translated = TARGET_CACHE.get(text)
    if translated is not None:
        return translated

    if IS_GET:
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