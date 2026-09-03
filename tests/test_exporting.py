import json

from kindle2notion.exporting import (
    _build_clipping_blocks,
    _collect_existing_quote_texts,
    _format_added_date,
    _normalize_text,
    _pair_notes_with_highlights,
    export_to_notion,
)


class FakeNotionClient:
    def __init__(self, pages=None, blocks=None):
        self.pages = pages or {}
        self.blocks = blocks or {}
        self.appended = {}

    def query_page_by_title(self, database_id, title):
        page = self.pages.get(title)
        return dict(page) if page else None

    def query_all_page_titles(self, database_id):
        return {page["id"]: title for title, page in self.pages.items()}

    def create_page(self, database_id, title, author=''):
        page = {"id": f"page-{title}"}
        self.pages[title] = page
        return page

    def list_page_blocks(self, page_id):
        return self.blocks.get(page_id, [])

    def append_blocks(self, page_id, blocks):
        self.appended.setdefault(page_id, []).extend(blocks)


def test_normalize_text_should_collapse_whitespace_and_ignore_case():
    assert _normalize_text('  The   Book ") Title ') == 'the book ") title'
    assert _normalize_text('abc') == _normalize_text('ABC')


def test_format_added_date_should_convert_the_parsed_clipping_date():
    assert _format_added_date('Tuesday, 22 September 2020 09:23:48 AM') == '2020-09-22 09:23'
    assert _format_added_date('') is None


def test_pair_notes_with_highlights_should_attach_a_note_to_its_highlight():
    # Given
    clippings = [
        ('A highlight.', '12', '', 'Tuesday, 22 September 2020 09:23:48 AM', False),
        ('A note.', '12', '', 'Tuesday, 22 September 2020 09:23:48 AM', True),
        ('Another highlight.', '13', '', 'Tuesday, 22 September 2020 10:00:00 AM', False),
    ]

    # When
    actual = _pair_notes_with_highlights(clippings)

    # Then
    assert len(actual) == 2
    assert actual[0]['text'] == 'A highlight.'
    assert actual[0]['note'] == 'A note.'
    assert actual[1]['note'] is None


def test_pair_notes_with_highlights_should_attach_a_native_kindle_note_by_location():
    # Given
    clippings = [
        ('A highlight.', '', '269-271', 'Friday, 06 March 2026 08:19:11 PM', False),
        ('A first note.', '', '271', 'Friday, 06 March 2026 08:20:31 PM', True),
        ('A second note.', '', '271', 'Friday, 06 March 2026 08:21:30 PM', True),
    ]

    # When
    actual = _pair_notes_with_highlights(clippings)

    # Then
    assert len(actual) == 1
    assert actual[0]['text'] == 'A highlight.'
    assert actual[0]['note'] == 'A second note.'


def test_pair_notes_with_highlights_should_keep_a_note_without_a_matching_highlight():
    # Given
    clippings = [
        ('Highlight A.', '', '100-105', 'Friday, 06 March 2026 08:19:11 PM', False),
        ('Highlight B.', '', '200-205', 'Friday, 06 March 2026 08:20:31 PM', False),
        ('A note for highlight A.', '', '100', 'Friday, 06 March 2026 08:21:30 PM', True),
    ]

    # When
    actual = _pair_notes_with_highlights(clippings)

    # Then
    assert len(actual) == 3
    assert actual[1]['note'] is None
    assert actual[2]['is_note'] is True
    assert actual[2]['note'] is None


def test_pair_notes_with_highlights_should_keep_a_note_without_a_matching_highlight_standalone():
    # Given
    clippings = [
        ('A lone note.', '12', '', 'Tuesday, 22 September 2020 09:23:48 AM', True),
    ]

    # When
    actual = _pair_notes_with_highlights(clippings)

    # Then
    assert len(actual) == 1
    assert actual[0]['text'] == 'A lone note.'
    assert actual[0]['note'] is None


def test_build_clipping_blocks_should_follow_the_readest_block_layout():
    # Given
    item = {
        'text': 'A highlight.',
        'page': '12',
        'location': '',
        'date': 'Tuesday, 22 September 2020 09:23:48 AM',
        'note': 'A note.',
        'is_note': False,
    }

    # When
    actual = _build_clipping_blocks(item)

    # Then
    expected = [
        {'object': 'block', 'type': 'divider', 'divider': {}},
        {
            'object': 'block',
            'type': 'quote',
            'quote': {
                'rich_text': [
                    {'type': 'text', 'text': {'content': 'A highlight.'}}
                ]
            },
        },
        {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [{'type': 'text', 'text': {'content': '📝 A note.'}}]
            },
        },
        {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [
                    {
                        'type': 'text',
                        'text': {'content': 'Added on 2020-09-22 09:23'},
                        'annotations': {'italic': True, 'color': 'gray'},
                    }
                ]
            },
        },
    ]
    assert expected == actual


def test_build_clipping_blocks_should_omit_the_note_and_date_blocks_when_missing():
    # Given
    item = {
        'text': 'A highlight.',
        'page': '12',
        'location': '',
        'date': '',
        'note': None,
        'is_note': False,
    }

    # When
    actual = _build_clipping_blocks(item)

    # Then
    assert len(actual) == 2
    assert actual[0]['type'] == 'divider'
    assert actual[1]['type'] == 'quote'


def test_collect_existing_quote_texts_should_collect_and_normalize_quote_blocks():
    # Given
    blocks = [
        {'type': 'divider', 'divider': {}},
        {
            'type': 'quote',
            'quote': {
                'rich_text': [
                    {'plain_text': 'A highlight.'},
                    {'plain_text': ' Rest of it.'},
                ]
            },
        },
        {
            'type': 'paragraph',
            'paragraph': {'rich_text': [{'plain_text': 'Added on 2020-09-22'}]},
        },
    ]

    # When
    actual = _collect_existing_quote_texts(blocks)

    # Then
    assert actual == {_normalize_text('A highlight. Rest of it.')}


def test_export_to_notion_should_create_a_new_page_and_append_readest_style_blocks():
    # Given
    notion = FakeNotionClient()
    all_books = {
        '三体': {
            'author': '刘慈欣',
            'highlights': [
                (
                    '给岁月以文明，给时光以生命。',
                    '123',
                    '',
                    'Wednesday, 02 September 2026 10:00:00 AM',
                    False,
                ),
                (
                    '这句真好',
                    '123',
                    '',
                    'Wednesday, 02 September 2026 10:00:00 AM',
                    True,
                ),
            ],
        }
    }

    # When
    export_to_notion(all_books, notion, 'database-id')

    # Then
    assert list(notion.pages) == ['三体']
    appended = notion.appended['page-三体']
    quote_texts = [
        rt['text']['content']
        for block in appended
        if block['type'] == 'quote'
        for rt in block['quote']['rich_text']
    ]
    assert quote_texts == ['给岁月以文明，给时光以生命。']
    note_blocks = [
        block
        for block in appended
        if block['type'] == 'paragraph'
        and block['paragraph']['rich_text'][0]['text']['content'].startswith('📝')
    ]
    assert len(note_blocks) == 1
    assert note_blocks[0]['paragraph']['rich_text'][0]['text']['content'] == '📝 这句真好'


def test_export_to_notion_should_skip_highlights_already_present_in_notion():
    # Given
    notion = FakeNotionClient(
        pages={'三体': {'id': 'page-1'}},
        blocks={
            'page-1': [
                {
                    'type': 'quote',
                    'quote': {'rich_text': [{'plain_text': '宇宙很大，生活更大。'}]},
                }
            ]
        },
    )
    all_books = {
        '三体': {
            'author': '刘慈欣',
            'highlights': [
                (
                    '宇宙很大，生活更大。',
                    '456',
                    '',
                    'Thursday, 03 September 2026 11:30:15 PM',
                    False,
                ),
                (
                    '给岁月以文明，给时光以生命。',
                    '123',
                    '',
                    'Wednesday, 02 September 2026 10:00:00 AM',
                    False,
                ),
            ],
        }
    }

    # When
    export_to_notion(all_books, notion, 'database-id')

    # Then
    assert list(notion.pages) == ['三体']
    appended = notion.appended['page-1']
    quote_texts = [
        rt['text']['content']
        for block in appended
        if block['type'] == 'quote'
        for rt in block['quote']['rich_text']
    ]
    assert quote_texts == ['给岁月以文明，给时光以生命。']


def test_export_to_notion_should_reuse_a_page_with_an_equivalent_title():
    # Given
    notion = FakeNotionClient(pages={'The Book Title': {'id': 'page-1'}})
    all_books = {
        'the  book   title': {
            'author': 'An Author',
            'highlights': [
                ('A highlight.', '1', '', 'Tuesday, 22 September 2020 09:23:48 AM', False)
            ],
        }
    }

    # When
    export_to_notion(all_books, notion, 'database-id')

    # Then
    assert list(notion.pages) == ['The Book Title']
    assert notion.appended['page-1']


def test_export_to_notion_should_apply_the_title_alias_file(tmp_path):
    # Given
    alias_file = tmp_path / 'alias.json'
    alias_file.write_text(json.dumps({'三体（Kindle）': '三体'}), encoding='utf-8')
    notion = FakeNotionClient(pages={'三体': {'id': 'page-1'}})
    all_books = {
        '三体（Kindle）': {
            'author': '刘慈欣',
            'highlights': [
                ('A highlight.', '1', '', 'Tuesday, 22 September 2020 09:23:48 AM', False)
            ],
        }
    }

    # When
    export_to_notion(
        all_books,
        notion,
        'database-id',
        title_alias_path=str(alias_file),
    )

    # Then
    assert list(notion.pages) == ['三体']
    assert notion.appended['page-1']
