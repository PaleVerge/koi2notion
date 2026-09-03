from time import sleep
from typing import Dict, List, Optional

import requests
from requests.exceptions import ConnectionError, SSLError

NOTION_API_BASE_URL = 'https://api.notion.com/v1'
NOTION_API_VERSION = '2022-06-28'
MAX_BLOCKS_PER_REQUEST = 100


class NotionError(Exception):
    pass


class NotionClient:
    def __init__(self, auth_token: str) -> None:
        self.auth_token = auth_token

    def retrieve_database(self, database_id: str) -> Optional[dict]:
        res = self._request('GET', f'/databases/{database_id}')
        if res.status_code != 200:
            return None
        return res.json()

    def resolve_database_id(self, page_id: str) -> Optional[str]:
        res = self._request('GET', f'/blocks/{page_id}/children')
        if res.status_code != 200:
            return None
        for block in res.json().get('results', []):
            if block.get('type') == 'child_database':
                return block.get('id')
        return None

    def query_page_by_title(self, database_id: str, title: str) -> Optional[dict]:
        res = self._request(
            'POST',
            f'/databases/{database_id}/query',
            body={
                'filter': {'property': 'title', 'title': {'equals': title}},
                'page_size': 5,
            },
        )
        results = self._results(res, f'database query failed for book "{title}"')
        return results[0] if results else None

    def query_all_page_titles(self, database_id: str) -> Dict[str, str]:
        titles = {}
        cursor = None
        while True:
            body = {'page_size': 100}
            if cursor:
                body['start_cursor'] = cursor
            res = self._request('POST', f'/databases/{database_id}/query', body=body)
            results = self._results(res, 'database query failed while listing pages')
            for page in results:
                title = extract_page_title(page)
                if title is not None:
                    titles[page['id']] = title
            data = res.json()
            if not data.get('has_more'):
                break
            cursor = data.get('next_cursor')
        return titles

    def create_page(self, database_id: str, title: str, author: str = '') -> dict:
        properties: dict = {'title': {'title': [{'text': {'content': title}}]}}
        if author:
            properties['作者'] = {'rich_text': [{'text': {'content': author}}]}
        res = self._request(
            'POST',
            '/pages',
            body={
                'parent': {'database_id': database_id},
                'properties': properties,
            },
        )
        return self._payload(res, f'failed to create a page for book "{title}"')

    def list_page_blocks(self, page_id: str) -> List[dict]:
        blocks = []
        cursor = None
        while True:
            params = {'page_size': 100}
            if cursor:
                params['start_cursor'] = cursor
            res = self._request('GET', f'/blocks/{page_id}/children', params=params)
            data = self._payload(res, f'failed to read blocks of page "{page_id}"')
            blocks.extend(data.get('results', []))
            if not data.get('has_more'):
                break
            cursor = data.get('next_cursor')
        return blocks

    def append_blocks(self, page_id: str, blocks: List[dict]) -> None:
        for start in range(0, len(blocks), MAX_BLOCKS_PER_REQUEST):
            chunk = blocks[start : start + MAX_BLOCKS_PER_REQUEST]
            res = self._request(
                'PATCH', f'/blocks/{page_id}/children', body={'children': chunk}
            )
            self._payload(res, f'failed to append blocks to page "{page_id}"')

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None,
        body: Optional[dict] = None,
    ) -> requests.Response:
        headers = {
            'Authorization': f'Bearer {self.auth_token}',
            'Notion-Version': NOTION_API_VERSION,
        }
        url = f'{NOTION_API_BASE_URL}{path}'
        res = None
        for attempt in range(4):
            try:
                res = requests.request(
                    method, url, headers=headers, params=params, json=body
                )
                if res.status_code == 429 or res.status_code >= 500:
                    retry_after = res.headers.get('Retry-After')
                    sleep(float(retry_after) if retry_after else min(2**attempt, 30))
                    continue
                return res
            except (SSLError, ConnectionError):
                if attempt < 3:
                    sleep(min(2**attempt, 30))
                    continue
                raise
        return res

    def _results(self, res: requests.Response, context: str) -> List[dict]:
        data = self._payload(res, context)
        return data.get('results', [])

    def _payload(self, res: requests.Response, context: str) -> dict:
        if res.status_code != 200:
            raise NotionError(f'{context}: {self._error_message(res)}')
        return res.json()

    @staticmethod
    def _error_message(res: requests.Response) -> str:
        try:
            return res.json().get('message', f'HTTP {res.status_code}')
        except ValueError:
            return f'HTTP {res.status_code}'


def extract_page_title(page: dict) -> Optional[str]:
    for prop in page.get('properties', {}).values():
        if prop.get('type') == 'title':
            return ''.join(
                t.get('plain_text', '') for t in prop.get('title', [])
            ).strip()
    return None
