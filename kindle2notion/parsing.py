from datetime import datetime
from re import compile, findall, search, sub
from typing import Dict, List, Tuple

from dateparser import parse

BOOKS_WO_AUTHORS = []

WEEKDAY_PATTERN = compile(r'星期[一二三四五六日天]|周[一二三四五六日天]')
CN_PAGE_PATTERN = compile(r'第\s*([\d-]+)\s*页')
CN_LOCATION_PATTERN = compile(r'位置\s*#?([\d-]+)')
CN_DATE_PATTERN = compile(
    r'(?P<year>\d{4})年(?P<month>\d{1,2})月(?P<day>\d{1,2})日'
    r'(?:\D*(?P<meridiem>上午|下午)\s*(?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
    r'(?::(?P<second>\d{1,2}))?)?'
)

ACADEMIC_TITLES = [
    "A.A.",
    "A.S.",
    "A.A.A.",
    "A.A.S.",
    "A.B.",
    "A.D.N.",
    "A.M.",
    "A.M.T.",
    "C.E.",
    "Ch.E.",
    "D.A.",
    "D.A.S.",
    "D.B.A.",
    "D.C.",
    "D.D.",
    "D.Ed.",
    "D.L.S.",
    "D.M.D.",
    "D.M.S.",
    "D.P.A.",
    "D.P.H.",
    "D.R.E.",
    "D.S.W.",
    "D.Sc.",
    "D.V.M.",
    "Ed.D.",
    "Ed.S.",
    "E.E.",
    "E.M.",
    "E.Met.",
    "I.E.",
    "J.D.",
    "J.S.D.",
    "L.H.D.",
    "Litt.B.",
    "Litt.M.",
    "LL.B.",
    "LL.D.",
    "LL.M.",
    "M.A.",
    "M.Aero.E.",
    "M.B.A.",
    "M.C.S.",
    "M.D.",
    "M.Div.",
    "M.E.",
    "M.Ed.",
    "M.Eng.",
    "M.F.A.",
    "M.H.A.",
    "M.L.S.",
    "M.Mus.",
    "M.N.",
    "M.P.A.",
    "M.S.",
    "M.S.Ed.",
    "M.S.W.",
    "M.Th.",
    "Nuc.E.",
    "O.D.",
    "Pharm.D.",
    "Ph.B.",
    "Ph.D.",
    "S.B.",
    "Sc.D.",
    "S.J.D.",
    "S.Sc.D.",
    "Th.B.",
    "Th.D.",
    "Th.M.",
]

DELIMITERS = ["; ", " & ", " and "]


def parse_raw_clippings_text(raw_clippings_text: str) -> Dict:
    raw_clippings_list = raw_clippings_text.split("==========")
    print(f"Found {len(raw_clippings_list)} notes and highlights.\n")

    all_books = {}
    passed_clippings_count = 0

    for each_raw_clipping in raw_clippings_list:
        raw_clipping_list = each_raw_clipping.strip().split("\n")

        if _is_valid_clipping(raw_clipping_list):
            author, title = _parse_author_and_title(raw_clipping_list)
            page, location, date, is_note = _parse_page_location_date_and_note(
                raw_clipping_list
            )
            highlight = raw_clipping_list[3]

            all_books = _add_parsed_items_to_all_books_dict(
                all_books, title, author, highlight, page, location, date, is_note
            )
        else:
            passed_clippings_count += 1

    print(f"× Passed {passed_clippings_count} bookmarks or unsupported clippings.\n")
    return all_books


def _is_valid_clipping(raw_clipping_list: List) -> bool:
    return len(raw_clipping_list) >= 3


def _parse_author_and_title(raw_clipping_list: List) -> Tuple[str, str]:
    author, title = _parse_raw_author_and_title(raw_clipping_list)
    author, title = _deal_with_exceptions_in_author_name(author, title)
    title = _deal_with_exceptions_in_title(title)
    return author, title


def _parse_page_location_date_and_note(
    raw_clipping_list: List,
) -> Tuple[str, str, str, bool]:
    second_line = raw_clipping_list[1]
    second_line_as_list = second_line.strip().split(" | ")
    page = location = date = ""
    is_note = False

    for element in second_line_as_list:
        element = element.lower()
        if "note" in element or "笔记" in element:
            is_note = True
        if "page" in element:
            page = element[element.find("page") :].replace("page", "").strip()
        elif "页" in element:
            match = search(CN_PAGE_PATTERN, element)
            if match:
                page = match.group(1)
        if "location" in element:
            location = (
                element[element.find("location") :].replace("location", "").strip()
            )
        elif "位置" in element:
            match = search(CN_LOCATION_PATTERN, element)
            if match:
                location = match.group(1)
        if "added on" in element:
            date = _parse_date(
                element[element.find("added on") :].replace("added on", "").strip()
            )
        elif "添加于" in element:
            date = _parse_date(element.split("添加于", 1)[1].strip())

    return page, location, date, is_note


def _parse_date(date_string: str) -> str:
    if not date_string:
        return ""
    cleaned = sub(WEEKDAY_PATTERN, " ", date_string)
    match = search(CN_DATE_PATTERN, cleaned)
    if match:
        parsed_date = datetime(
            int(match["year"]), int(match["month"]), int(match["day"])
        )
        if match["meridiem"]:
            hour = int(match["hour"])
            if match["meridiem"] == "下午" and hour < 12:
                hour += 12
            elif match["meridiem"] == "上午" and hour == 12:
                hour = 0
            parsed_date = parsed_date.replace(
                hour=hour, minute=int(match["minute"]), second=int(match["second"] or 0)
            )
        return parsed_date.strftime("%A, %d %B %Y %I:%M:%S %p")
    parsed_date = parse(cleaned)
    if parsed_date:
        return parsed_date.strftime("%A, %d %B %Y %I:%M:%S %p")
    return ""


def _add_parsed_items_to_all_books_dict(
    all_books: Dict,
    title: str,
    author: str,
    highlight: str,
    page: str,
    location: str,
    date: str,
    is_note: bool,
) -> Dict:
    if title not in all_books:
        all_books[title] = {"author": author, "highlights": []}
    all_books[title]["highlights"].append((highlight, page, location, date, is_note))
    return all_books


def _parse_raw_author_and_title(raw_clipping_list: List) -> Tuple[str, str]:
    author = ""
    raw_title = raw_clipping_list[0].strip()
    title = raw_title

    matches = findall(r"\(.*?\)", raw_title)
    if matches:
        author = matches[-1].removeprefix("(").removesuffix(")")
        if raw_title.endswith(matches[-1]):
            title = raw_title[: -len(matches[-1])]
        else:
            title = raw_title.replace(author, "")
    else:
        if title not in BOOKS_WO_AUTHORS:
            BOOKS_WO_AUTHORS.append(title)
            print(
                f"{title} - No author found. You can manually add the author in the Notion database."
            )

    title = title.strip().replace(" ()", "").strip()

    if author.lower() in ("unknown", "未知"):
        author = ""
        if title not in BOOKS_WO_AUTHORS:
            BOOKS_WO_AUTHORS.append(title)
            print(
                f"{title} - No author found. You can manually add the author in the Notion database."
            )

    return author, title


def _deal_with_exceptions_in_author_name(author: str, title: str) -> Tuple[str, str]:
    if "(" in author:
        author = author + ")"
        title = title.removesuffix(")")

    if ", " in author and all(x not in author for x in DELIMITERS):
        if (author.split(", "))[1] not in ACADEMIC_TITLES:
            author = " ".join(reversed(author.split(", ")))

    if "; " in author:
        authorList = author.split("; ")
        author = ""
        for ele in authorList:
            author += " ".join(reversed(ele.split(", "))) + ", "
        author = author.removesuffix(", ")
    return author, title


def _deal_with_exceptions_in_title(title: str) -> str:
    if ", The" in title:
        title = "The " + title.replace(", The", "")
    return title
