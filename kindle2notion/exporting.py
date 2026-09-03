import json
import re
import unicodedata
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from kindle2notion.notion_client import NotionClient

MAX_TEXT_LENGTH = 2000


def export_to_notion(
    all_books: Dict,
    notion: NotionClient,
    notion_database_id: str,
    title_alias_path: Optional[str] = None,
) -> None:
    print('Initiating transfer...\n')

    alias = _load_title_alias(title_alias_path)
    title_cache: Dict[str, str] = {}

    for clipped_title, each_book in all_books.items():
        title = alias.get(clipped_title, clipped_title)
        _sync_one_book(
            notion,
            notion_database_id,
            title,
            each_book['author'],
            each_book['highlights'],
            title_cache,
        )


def _sync_one_book(
    notion: NotionClient,
    notion_database_id: str,
    title: str,
    author: str,
    clippings: List,
    title_cache: Dict[str, str],
) -> str:
    title_and_author = f'{title} ({author})' if author else title
    print(title_and_author)
    print('-' * len(title_and_author))

    page, matched_title = _find_or_create_page(notion, notion_database_id, title, author, title_cache)
    if matched_title != title:
        print(f'ℹ Syncing into the existing page "{matched_title}".')

    existing_texts = _collect_existing_quote_texts(notion.list_page_blocks(page['id']))
    items = _pair_notes_with_highlights(clippings)

    new_items = []
    for item in items:
        normalized = _normalize_text(item['text'])
        if not normalized or normalized in existing_texts:
            continue
        existing_texts.add(normalized)
        new_items.append(item)

    if new_items:
        blocks: List[dict] = []
        for item in new_items:
            blocks.extend(_build_clipping_blocks(item))
        notion.append_blocks(page['id'], blocks)

    skipped_count = len(items) - len(new_items)
    if not new_items:
        message = 'None to add.'
    else:
        message = (
            f'✓ {len(new_items)} notes/highlights added successfully. '
            f'{skipped_count} skipped (already in Notion).'
        )
    print(message + '\n')
    return message


def _find_or_create_page(
    notion: NotionClient,
    notion_database_id: str,
    title: str,
    author: str,
    title_cache: Dict[str, str],
) -> Tuple[dict, str]:
    page = notion.query_page_by_title(notion_database_id, title)
    if page:
        return page, title

    if not title_cache:
        title_cache.update(notion.query_all_page_titles(notion_database_id))
    normalized = _normalize_text(title)
    matches = [
        page_id
        for page_id, page_title in title_cache.items()
        if _normalize_text(page_title) == normalized
    ]
    if len(matches) == 1:
        matched_title = title_cache[matches[0]]
        page = notion.query_page_by_title(notion_database_id, matched_title)
        if page:
            return page, matched_title
    if len(matches) > 1:
        print(
            f'× Multiple pages match "{title}" after normalizing the title. '
            'Creating a separate page to avoid merging different books.'
        )

    page = notion.create_page(notion_database_id, title, author)
    title_cache[page['id']] = title
    print('✓ Created a new page in Notion.')
    return page, title


def _pair_notes_with_highlights(clippings: List) -> List[dict]:
    items = []
    for text, page, location, date, is_note in clippings:
        if (
            is_note
            and items
            and not items[-1]['is_note']
            and _note_belongs_to_highlight(items[-1], page, location)
        ):
            items[-1]['note'] = text
            continue
        items.append(
            {
                'text': text,
                'page': page,
                'location': location,
                'date': date,
                'note': None,
                'is_note': is_note,
            }
        )
    return items


def _note_belongs_to_highlight(highlight: dict, page: str, location: str) -> bool:
    if location and highlight['location']:
        return _ranges_overlap(location, highlight['location'])
    if page and highlight['page']:
        return _ranges_overlap(page, highlight['page'])
    return False


def _ranges_overlap(a: str, b: str) -> bool:
    a_start, a_end = _parse_range(a)
    b_start, b_end = _parse_range(b)
    if a_start is None or b_start is None:
        return a == b
    return a_start <= b_end and b_start <= a_end


def _parse_range(value: str):
    match = re.match(r'\s*(\d+)(?:-(\d+))?', value)
    if not match:
        return None, None
    start = int(match.group(1))
    return start, int(match.group(2) or match.group(1))


def _build_clipping_blocks(item: dict) -> List[dict]:
    blocks = [
        {'object': 'block', 'type': 'divider', 'divider': {}},
        {
            'object': 'block',
            'type': 'quote',
            'quote': {'rich_text': _rich_text(item['text'])},
        },
    ]
    if item['note']:
        blocks.append(
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': _rich_text(f'📝 {item["note"]}')
                },
            }
        )
    added_date = _format_added_date(item['date'])
    if added_date:
        blocks.append(
            {
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {'content': f'Added on {added_date}'},
                            'annotations': {'italic': True, 'color': 'gray'},
                        }
                    ]
                },
            }
        )
    return blocks


def _rich_text(content: str) -> List[dict]:
    return [
        {'type': 'text', 'text': {'content': content[start : start + MAX_TEXT_LENGTH]}}
        for start in range(0, len(content), MAX_TEXT_LENGTH)
    ]


def _collect_existing_quote_texts(blocks: List[dict]) -> set:
    texts = set()
    for block in blocks:
        if block.get('type') != 'quote':
            continue
        rich_text = block.get('quote', {}).get('rich_text', [])
        plain_text = ''.join(rt.get('plain_text', '') for rt in rich_text)
        if plain_text:
            texts.add(_normalize_text(plain_text))
    return texts


def _normalize_text(text: str) -> str:
    return ' '.join(unicodedata.normalize('NFC', text).casefold().split())


def _format_added_date(date: str) -> Optional[str]:
    if not date:
        return None
    parsed = datetime.strptime(date, '%A, %d %B %Y %I:%M:%S %p')
    return parsed.strftime('%Y-%m-%d %H:%M')


def _load_title_alias(title_alias_path: Optional[str]) -> Dict[str, str]:
    if not title_alias_path:
        return {}
    try:
        with open(title_alias_path, 'r', encoding='utf-8') as alias_file:
            alias = json.load(alias_file)
    except (OSError, ValueError):
        print(f'× Could not read the title alias file: {title_alias_path}')
        return {}
    if not isinstance(alias, dict):
        print('× The title alias file must contain a JSON object.')
        return {}
    return alias
