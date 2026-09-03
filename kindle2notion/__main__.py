import json
import sys
import time
from pathlib import Path

import click

from kindle2notion.exporting import export_to_notion
from kindle2notion.notion_client import NotionClient
from kindle2notion.parsing import parse_raw_clippings_text
from kindle2notion.reading import read_raw_clippings

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_PATH = PROJECT_ROOT / 'config.json'
SYNC_STATE_PATH = PROJECT_ROOT / 'sync_state.json'

DEFAULT_CONFIG = {
    'notion_token': '',
    'database_id': '',
    'clippings_file': '',
    'title_alias': None,
    'watch_interval': 300,
}


@click.group(invoke_without_command=True)
@click.option('--config', 'config_path', default=None, type=click.Path(), help='配置文件路径，默认 ~/.kindle2notion/config.json')
@click.option('--watch', is_flag=True, default=False, help='监听文件变化，自动同步')
@click.pass_context
def main(ctx, config_path, watch):
    if ctx.invoked_subcommand is not None:
        return

    if sys.stdout:
        sys.stdout.reconfigure(errors='replace')

    config = _load_config(config_path)
    if config is None:
        return

    notion = NotionClient(config['notion_token'])
    database_id = _resolve_database_id(notion, config['database_id'])
    if database_id is None:
        print('× Notion 数据库未找到，请检查 config.json 中的 database_id')
        return

    if watch:
        _watch_loop(notion, database_id, config)
    else:
        _run_sync(notion, database_id, config)
        print('同步完成')


@main.command('init')
def init_config():
    if CONFIG_PATH.exists():
        if not click.confirm(f'配置文件已存在 ({CONFIG_PATH})，是否覆盖？'):
            return

    click.echo('kindle2notion 配置向导')
    click.echo('-' * 40)
    token = click.prompt('Notion Integration Token', hide_input=True)
    db_id = click.prompt('Notion 数据库 ID')
    clippings = click.prompt(
        'My Clippings.txt 路径',
        default=str(Path.home() / 'Documents' / 'My Clippings.txt'),
    )
    interval = click.prompt('监听间隔（秒）', default=300, type=int)

    config = {
        'notion_token': token,
        'database_id': db_id,
        'clippings_file': clippings,
        'title_alias': None,
        'watch_interval': interval,
    }

    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    click.echo(f'配置已保存到 {CONFIG_PATH}')
    click.echo('运行 kindle2notion --watch 开始同步')


def _load_config(config_path=None):
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        print(f'× 配置文件不存在: {path}')
        print('  运行 kindle2notion init 创建配置文件')
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (OSError, ValueError) as e:
        print(f'× 配置文件读取失败: {e}')
        return None

    merged = {**DEFAULT_CONFIG, **config}
    missing = [k for k in ('notion_token', 'database_id', 'clippings_file') if not merged.get(k)]
    if missing:
        print(f'× 配置缺少必填项: {", ".join(missing)}')
        return None
    return merged


def _run_sync(notion, database_id, config):
    clippings_file = config['clippings_file']
    if not Path(clippings_file).exists():
        print(f'× 文件不存在: {clippings_file}')
        return False
    print('解析中...')
    raw_clippings = read_raw_clippings(clippings_file)
    all_books = parse_raw_clippings_text(raw_clippings)
    export_to_notion(
        all_books, notion, database_id,
        config.get('title_alias'),
    )
    return True


def _watch_loop(notion, database_id, config):
    state = _load_state()
    interval = config['watch_interval']
    clippings_file = config['clippings_file']
    print(f'监听 {clippings_file}，每 {interval} 秒检查一次，Ctrl+C 退出')
    while True:
        try:
            signature = _file_signature(clippings_file)
            if signature is not None and signature != state.get(clippings_file):
                if _run_sync(notion, database_id, config):
                    state[clippings_file] = signature
                    _save_state(state)
            time.sleep(interval)
        except KeyboardInterrupt:
            print('退出监听')
            break
        except Exception as e:
            print(f'× 同步失败: {e}')
            time.sleep(interval)


def _resolve_database_id(notion, database_id):
    database_id = database_id.strip()
    if notion.retrieve_database(database_id):
        return database_id
    child_database_id = notion.resolve_database_id(database_id)
    if child_database_id:
        print(f'已解析到子数据库: {child_database_id}')
        return child_database_id
    return None


def _file_signature(clippings_file):
    path = Path(clippings_file)
    if not path.exists():
        return None
    stat = path.stat()
    return (stat.st_mtime_ns, stat.st_size)


def _load_state():
    try:
        with open(SYNC_STATE_PATH, 'r', encoding='utf-8') as f:
            state = json.load(f)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_state(state):
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    with open(SYNC_STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=4)


if __name__ == '__main__':
    main()
