from datetime import datetime
from pathlib import Path

from kindle2notion.parsing import (
    parse_raw_clippings_text,
    _parse_author_and_title,
    _parse_page_location_date_and_note,
    _add_parsed_items_to_all_books_dict,
)
from kindle2notion.reading import read_raw_clippings


def test_parse_raw_clippings_text_should_return_a_dict_with_all_the_parsed_information():
    # Given
    test_clippings_file_path = (
        Path(__file__).parent.absolute() / "test_data/Test Clippings.txt"
    )
    raw_clippings_text = read_raw_clippings(test_clippings_file_path)

    expected = {
        "Title 1: A Great Book": {
            "author": "Ben Horowitz",
            "highlights": [
                (
                    "This is test highlight 1.",
                    "11",
                    "111-114",
                    "Tuesday, 22 September 2020 09:23:48 AM",
                    False,
                ),
                (
                    "This is test highlight 2.",
                    "11",
                    "111-114",
                    "Tuesday, 22 September 2020 09:24:04 AM",
                    False,
                ),
            ],
        },
        "Title 2 Is Good Too": {
            "author": "Colin Bryar",
            "highlights": [
                (
                    "This is test highlight 3.",
                    "3",
                    "184-185",
                    "Friday, 30 April 2021 12:31:29 AM",
                    False,
                ),
                (
                    "This is test highlight 4.",
                    "34",
                    "682-684",
                    "Friday, 30 April 2021 03:14:33 PM",
                    False,
                ),
            ],
        },
        "Title 3 Is Clean (Robert C. Martin Series)": {
            "author": "Martin Robert C.",
            "highlights": [
                (
                    "This is test highlight 5.",
                    "22",
                    "559-560",
                    "Saturday, 15 May 2021 10:25:42 PM",
                    False,
                ),
                (
                    "This is test highlight 6.",
                    "22",
                    "564-565",
                    "Saturday, 15 May 2021 10:26:26 PM",
                    False,
                ),
            ],
        },
    }

    # When
    actual = parse_raw_clippings_text(raw_clippings_text)

    # Then
    assert expected == actual


def test_parse_author_and_title_case_should_parse_the_author_and_title_when_the_author_name_is_formatted_with_a_comma():
    # Given
    raw_clipping_list = [
        "Relativity (Einstein, Albert)",
        "- Your Highlight on page 3 | Location 184-185 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("Albert Einstein", "Relativity")

    # When
    actual = _parse_author_and_title(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_author_and_title_case_should_parse_the_author_and_title_when_the_author_name_is_first_name_last_name():
    # Given
    raw_clipping_list = [
        "Relativity (Albert Einstein)",
        "- Your Highlight on page 3 | Location 184-185 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("Albert Einstein", "Relativity")

    # When
    actual = _parse_author_and_title(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_author_and_title_case_should_parse_the_author_and_title_when_there_are_parentheses_in_the_author_name():
    # Given
    raw_clipping_list = [
        "Candide (Voltaire (François-Marie Arouet))",
        "- Your Highlight on page 3 | Location 184-185 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("Voltaire (François-Marie Arouet)", "Candide")

    # When
    actual = _parse_author_and_title(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_author_and_title_case_should_parse_the_author_and_title_when_there_is_a_The_at_the_end_of_the_title():
    # Given
    raw_clipping_list = [
        "Age of Louis XIV, The (Voltaire (François-Marie Arouet))",
        "- Your Highlight on page 3 | Location 184-185 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("Voltaire (François-Marie Arouet)", "The Age of Louis XIV")

    # When
    actual = _parse_author_and_title(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_author_and_title_case_should_parse_the_author_and_title_when_there_are_parentheses_in_the_title():
    # Given
    raw_clipping_list = [
        "The Mysterious Disappearance of Leon (I Mean Noel) (Ellen Raskin)",
        "- Your Highlight on page 3 | Location 184-185 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("Ellen Raskin", "The Mysterious Disappearance of Leon (I Mean Noel)")

    # When
    actual = _parse_author_and_title(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_page_location_date_and_note_should_parse_the_page_location_and_date_when_there_are_all_three():
    # Given
    raw_clipping_list = [
        "Relativity (Albert Einstein)",
        "- Your Highlight on page 3 | Location 184-185 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("3", "184-185", "Friday, 30 April 2021 12:31:29 AM", False)

    # When
    actual = _parse_page_location_date_and_note(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_page_location_date_and_note_should_parse_the_page_and_location_when_there_is_no_date():
    # Given
    raw_clipping_list = [
        "Relativity (Albert Einstein)",
        "- Your Highlight on page 3 | Location 184-185",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("3", "184-185", "", False)

    # When
    actual = _parse_page_location_date_and_note(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_page_location_date_and_note_should_parse_the_location_and_date_when_there_is_no_page():
    # Given
    raw_clipping_list = [
        "Relativity (Albert Einstein)",
        "Location 184-185 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("", "184-185", "Friday, 30 April 2021 12:31:29 AM", False)

    # When
    actual = _parse_page_location_date_and_note(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_page_location_date_and_note_should_parse_the_page_and_date_when_there_is_no_location():
    # Given
    raw_clipping_list = [
        "Relativity (Albert Einstein)",
        "- Your Highlight on page 3 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
    ]
    expected = ("3", "", "Friday, 30 April 2021 12:31:29 AM", False)

    # When
    actual = _parse_page_location_date_and_note(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_raw_clippings_text_should_parse_koreader_my_clippings_format():
    # Given
    test_clippings_file_path = (
        Path(__file__).parent.absolute() / "test_data/KOReader Clippings.txt"
    )
    raw_clippings_text = read_raw_clippings(test_clippings_file_path)

    expected = {
        "三体": {
            "author": "刘慈欣",
            "highlights": [
                (
                    "给岁月以文明，给时光以生命。",
                    "123",
                    "",
                    "Wednesday, 02 September 2026 10:00:00 AM",
                    False,
                ),
                (
                    "这句真好",
                    "123",
                    "",
                    "Wednesday, 02 September 2026 10:00:00 AM",
                    True,
                ),
                (
                    "宇宙很大，生活更大。",
                    "456",
                    "",
                    "Thursday, 03 September 2026 11:30:15 PM",
                    False,
                ),
            ],
        },
        "The Book With No Author": {
            "author": "",
            "highlights": [
                (
                    "A lone highlight.",
                    "10",
                    "",
                    "Tuesday, 01 September 2026 09:15:00 AM",
                    False,
                )
            ],
        },
    }

    # When
    actual = parse_raw_clippings_text(raw_clippings_text)

    # Then
    assert expected == actual


def test_parse_raw_clippings_text_should_parse_the_chinese_kindle_format():
    # Given
    test_clippings_file_path = (
        Path(__file__).parent.absolute() / "test_data/Kindle Clippings (Chinese).txt"
    )
    raw_clippings_text = read_raw_clippings(test_clippings_file_path)

    expected = {
        "张春桥狱中家书（文字）": {
            "author": "张春桥",
            "highlights": [
                (
                    "而最明智的，反倒是些贫穷朴素的人。",
                    "",
                    "269-271",
                    "Friday, 06 March 2026 08:19:11 PM",
                    False,
                ),
                (
                    "纯粹的人性有用,战争怎么会发生？",
                    "",
                    "271",
                    "Friday, 06 March 2026 08:20:31 PM",
                    True,
                ),
                (
                    "纯粹的人道有用,战争怎么会发生？纯粹的精神无法改变物质。",
                    "",
                    "271",
                    "Friday, 06 March 2026 08:21:30 PM",
                    True,
                ),
            ],
        },
        "克林索尔的最后夏天（黑塞自传式作品）(果麦经典)": {
            "author": "赫尔曼·黑塞",
            "highlights": [
                (
                    "一个更热情更短暂的夏天开始了。",
                    "9",
                    "55-56",
                    "Thursday, 12 March 2026 08:25:37 PM",
                    False,
                )
            ],
        },
        "要为真理而斗争": {
            "author": "刘继明",
            "highlights": [
                (
                    "评价……” 刘继明： 迪芬巴赫博士来访",
                    "11-11",
                    "",
                    "Thursday, 05 March 2026 10:59:57 PM",
                    False,
                )
            ],
        },
        "哲学小辞典 (合集)": {
            "author": "",
            "highlights": [
                (
                    "人说这本书把马克思主义变得庸俗和僵化了。",
                    "4",
                    "6-7",
                    "Thursday, 16 April 2026 10:39:01 PM",
                    False,
                )
            ],
        },
    }

    # When
    actual = parse_raw_clippings_text(raw_clippings_text)

    # Then
    assert expected == actual


def test_parse_author_and_title_should_keep_an_author_name_inside_the_title():
    # Given
    raw_clipping_list = [
        "张春桥狱中家书（文字） (张春桥)",
        "- 您在位置 #24-26的标注 | 添加于 2026年3月1日星期日 下午5:20:08",
        "",
        "一些内容。",
        False,
    ]
    expected = ("张春桥", "张春桥狱中家书（文字）")

    # When
    actual = _parse_author_and_title(raw_clipping_list)

    # Then
    assert expected == actual


def test_parse_author_and_title_should_treat_koreader_unknown_author_as_missing():
    # Given
    raw_clipping_list = [
        "Some Book (Unknown)",
        "- Your Highlight on page 3 | Added on Friday, April 30, 2021 12:31:29 AM",
        "",
        "This is a test highlight.",
        False,
    ]
    expected = ("", "Some Book")

    # When
    actual = _parse_author_and_title(raw_clipping_list)

    # Then
    assert expected == actual


def test_add_parsed_items_to_books_dict_should_add_the_parsed_items_when_the_book_is_not_already_in_the_books_dict():
    # Given
    books = {}
    title = "Relativity"
    author = "Albert Einstein"
    highlight = "This is a first highlight."
    page = "1"
    location = "100"
    date = datetime(2021, 4, 30, 0, 31, 29)
    is_note = False

    expected = {
        "Relativity": {
            "author": "Albert Einstein",
            "highlights": [
                (
                    "This is a first highlight.",
                    "1",
                    "100",
                    datetime(2021, 4, 30, 0, 31, 29),
                    False,
                )
            ],
        }
    }

    # When
    actual = _add_parsed_items_to_all_books_dict(
        books, title, author, highlight, page, location, date, is_note
    )

    # Then
    assert expected == actual


def test_add_parsed_items_to_books_dict_should_add_the_parsed_items_when_the_book_is_already_in_the_books_dict():
    # Given
    books = {
        "Relativity": {
            "author": "Albert Einstein",
            "highlights": [
                (
                    "This is a first highlight.",
                    "1",
                    "100",
                    datetime(2021, 4, 30, 0, 31, 29),
                    False,
                )
            ],
        }
    }
    title = "Relativity"
    author = "Albert Einstein"
    highlight = "This is a second highlight."
    page = "2"
    location = "200"
    date = datetime(2021, 5, 1, 0, 31, 29)
    is_note = False

    expected = {
        "Relativity": {
            "author": "Albert Einstein",
            "highlights": [
                (
                    "This is a first highlight.",
                    "1",
                    "100",
                    datetime(2021, 4, 30, 0, 31, 29),
                    False,
                ),
                (
                    "This is a second highlight.",
                    "2",
                    "200",
                    datetime(2021, 5, 1, 0, 31, 29),
                    False,
                ),
            ],
        }
    }

    # When
    actual = _add_parsed_items_to_all_books_dict(
        books, title, author, highlight, page, location, date, is_note
    )

    # Then
    assert expected == actual
