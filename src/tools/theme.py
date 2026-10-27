def get_theme(src: str) -> str:
    with open(src, "r", encoding="UTF-8") as f:
        qss = f.read()
    return qss