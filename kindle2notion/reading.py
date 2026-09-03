from pathlib import Path
from typing import Union


def read_raw_clippings(clippings_file_path: Union[str, Path]) -> str:
    with open(clippings_file_path, "r", encoding="utf-8-sig") as raw_clippings_file:
        raw_clippings_text = raw_clippings_file.read()
    return raw_clippings_text.replace(u"\ufeff", "")
