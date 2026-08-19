import html
import json
import asyncio
import datetime
import logging
import re
import random
import sys
import time
from pathlib import Path
from urlextract import URLExtract
from dotenv import load_dotenv
import os
import httpx
import feedparser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
log = logging.getLogger('movie_bot')

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('GROUP_CHAT_ID')
ALERT_CHAT_ID = os.getenv('ALERT_CHAT_ID') or CHAT_ID
REDDIT_URL = os.getenv('REDDIT_URL')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
SEEN_POSTS_FILE = Path('seen_posts.txt')
PENDING_FILE = Path('pending_posts.json')
OMDB_CACHE_FILE = Path('omdb_cache.json')
MAX_SEND_ATTEMPTS = 5

USER_AGENT = 'script:BarryNormalMovieBot:v2.0 (by /u/barrynormalmovies)'

POLL_INTERVAL = int(os.getenv('POLL_INTERVAL', '1800'))
HEARTBEAT_INTERVAL = int(os.getenv('HEARTBEAT_INTERVAL', '86400'))
CONSECUTIVE_FAILURE_ALERT = 3
OMDB_CONCURRENCY = 5

URL_EXTRACTOR = URLExtract()

TELEGRAM_API = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'


class TelegramSendError(Exception):
    def __init__(self, description, retry_after=None):
        super().__init__(description)
        self.retry_after = retry_after


def validate_env():
    required = {
        'BOT_TOKEN': 'Telegram bot token from @BotFather',
        'GROUP_CHAT_ID': 'Target Telegram group/channel ID',
        'REDDIT_URL': 'Reddit RSS feed URL',
        'OMDB_API_KEY': 'OMDB API key for ratings and genres',
    }
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        log.error("Missing required environment variables: %s", ', '.join(missing))
        log.error("Create a .env file — see README for the list of variables.")
        raise SystemExit(1)


async def telegram_send(client, chat_id, text, **kwargs):
    payload = {'chat_id': chat_id, 'text': text, **kwargs}
    try:
        response = await client.post(TELEGRAM_API, json=payload, timeout=30.0)
    except Exception as e:
        raise TelegramSendError(f'network error: {e}') from e
    try:
        data = response.json()
    except Exception:
        raise TelegramSendError(
            f'bad response ({response.status_code}): {response.text[:200]}'
        )
    if not data.get('ok'):
        params = data.get('parameters') or {}
        raise TelegramSendError(
            data.get('description') or f'HTTP {response.status_code}',
            retry_after=params.get('retry_after'),
        )
    return True


async def send_status_message(client, message):
    try:
        await telegram_send(client, ALERT_CHAT_ID, message)
        log.info("Status sent: %s", message.splitlines()[0])
        return True
    except Exception as e:
        log.error("Failed to send status message: %s", e)
        return False


def load_seen_data():
    try:
        if not SEEN_POSTS_FILE.exists():
            return set(), set()
        seen_posts = set()
        seen_imdb = set()
        for line in SEEN_POSTS_FILE.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(' | ')
            seen_posts.add(parts[0])
            if len(parts) >= 4:
                imdb_match = re.search(r'/title/(tt\d+)', parts[3])
                if imdb_match:
                    seen_imdb.add(imdb_match.group(1))
        return seen_posts, seen_imdb
    except Exception as e:
        log.warning("Failed to load seen data: %s", e)
        return set(), set()


def save_seen_post(post_id, date_str, title, url, rt_score=None, imdb_rating=None, genre=None):
    try:
        parts = [post_id, date_str, title, url]
        if rt_score:
            parts.append(rt_score)
        if imdb_rating:
            parts.append(imdb_rating)
        if genre:
            parts.append(genre)
        with SEEN_POSTS_FILE.open('a') as f:
            f.write(' | '.join(parts) + '\n')
        return True
    except Exception as e:
        log.error("Failed to save post: %s", e)
        return False


def load_pending():
    try:
        if not PENDING_FILE.exists():
            return []
        data = json.loads(PENDING_FILE.read_text())
        return data if isinstance(data, list) else []
    except Exception as e:
        log.warning("Failed to load pending queue: %s", e)
        return []


def save_pending(items):
    try:
        PENDING_FILE.write_text(json.dumps(items, indent=2))
    except Exception as e:
        log.warning("Failed to save pending queue: %s", e)


def load_omdb_cache():
    try:
        if OMDB_CACHE_FILE.exists():
            data = json.loads(OMDB_CACHE_FILE.read_text())
            return data if isinstance(data, dict) else {}
    except Exception as e:
        log.warning("Failed to load OMDB cache: %s", e)
    return {}


def save_omdb_cache(cache):
    try:
        OMDB_CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception as e:
        log.warning("Failed to save OMDB cache: %s", e)


def clean_title(title):
    return re.sub(r'\s*\(admin\)\s*', '', title, flags=re.IGNORECASE).strip()


def is_valid_movie_url(text):
    for url in URL_EXTRACTOR.find_urls(text):
        if 'imdb.com' in url:
            return url
    return None


def extract_imdb_id(url):
    match = re.search(r'/title/(tt\d+)', url)
    return match.group(1) if match else None


async def fetch_movie_info(client, imdb_id, omdb_cache, omdb_semaphore):
    if not OMDB_API_KEY or not imdb_id:
        return None, None, None
    if imdb_id in omdb_cache:
        cached = omdb_cache[imdb_id]
        return cached.get('rt_score'), cached.get('imdb_rating'), cached.get('genre')
    async with omdb_semaphore:
        try:
            url = f'https://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}'
            response = await client.get(url, timeout=15.0)
            response.raise_for_status()
            data = response.json()
            if data.get('Response') != 'True':
                return None, None, None
            genre = data.get('Genre')
            rt_score = None
            for rating in data.get('Ratings', []):
                if rating.get('Source') == 'Rotten Tomatoes' and rating.get('Value'):
                    rt_score = rating['Value']
                    break
            imdb_val = data.get('imdbRating')
            imdb_rating = imdb_val + '/10' if imdb_val and imdb_val != 'N/A' else None
            omdb_cache[imdb_id] = {
                'rt_score': rt_score,
                'imdb_rating': imdb_rating,
                'genre': genre,
            }
            save_omdb_cache(omdb_cache)
            return rt_score, imdb_rating, genre
        except Exception as e:
            log.warning("Failed to fetch movie info for %s: %s", imdb_id, e)
    return None, None, None


def build_message(title, date_str, url, rt_score, imdb_rating, genre):
    lines = [f"🎬 {html.escape(title)}", f"📅 {html.escape(date_str)}"]
    if genre:
        lines.append(f"🏷 {html.escape(str(genre))}")
    if rt_score:
        lines.append(f"🍅 {html.escape(str(rt_score))}")
    if imdb_rating:
        lines.append(f"⭐ {html.escape(str(imdb_rating))}")
    lines.append(f"🔗 {html.escape(url)}")
    return "\n".join(lines)


async def send_telegram_message(client, title, date, url, rt_score=None, imdb_rating=None, genre=None):
    date_str = date.strftime('%d %b %Y') if isinstance(date, datetime.datetime) else str(date)
    message = build_message(title, date_str, url, rt_score, imdb_rating, genre)
    try:
        await telegram_send(
            client,
            CHAT_ID,
            message,
            parse_mode='HTML',
            disable_web_page_preview=False,
        )
        log.info("Sent: %s", title)
        return True
    except TelegramSendError as e:
        log.error("Failed to send %s: %s", title, e)
        wait = None
        if e.retry_after:
            wait = int(e.retry_after) + 2
        else:
            match = re.search(r'Retry in (\d+) seconds', str(e))
            if match:
                wait = int(match.group(1)) + 2
        if wait:
            log.info("Waiting %ds for flood control...", wait)
            await asyncio.sleep(wait)
        return False
    except Exception as e:
        log.error("Failed to send %s: %s", title, e)
        return False


async def process_entry(client, entry, seen_posts, seen_imdb, pending, omdb_cache, omdb_semaphore):
    post_id = entry.get('id', '').split('_')[-1]
    if not post_id or post_id in seen_posts:
        return 'skip'
    if any(item['post_id'] == post_id for item in pending):
        return 'skip'

    content = entry.get('content', [{}])[0].get('value', '') + ' ' + entry.get('summary', '')

    if url := is_valid_movie_url(content):
        imdb_id = extract_imdb_id(url)
        if imdb_id and imdb_id in seen_imdb:
            seen_posts.add(post_id)
            return 'skip'

        rt_score, imdb_rating, genre = await fetch_movie_info(
            client, imdb_id, omdb_cache, omdb_semaphore
        )

        if post_id in seen_posts:
            return 'skip'

        updated_parsed = entry.get('updated_parsed')
        date_obj = datetime.datetime(*updated_parsed[:6]) if updated_parsed else datetime.datetime.now()
        title = clean_title(entry.get('title', 'No Title'))
        date_str = date_obj.strftime('%Y-%m-%d')

        if not save_seen_post(post_id, date_str, title, url, rt_score, imdb_rating, genre):
            log.error("Not sending '%s': could not persist to seen file.", title)
            return 'skip'
        seen_posts.add(post_id)
        if imdb_id:
            seen_imdb.add(imdb_id)

        success = await send_telegram_message(
            client,
            title,
            date_obj,
            url,
            rt_score,
            imdb_rating,
            genre,
        )
        if success:
            return 'sent'
        pending.append({
            'post_id': post_id,
            'date_str': date_str,
            'title': title,
            'url': url,
            'rt_score': rt_score,
            'imdb_rating': imdb_rating,
            'genre': genre,
            'attempts': 1,
        })
        save_pending(pending)
        return 'queued'
    return 'skip'


async def retry_pending(client, seen_posts, seen_imdb, pending):
    if not pending:
        return 0
    log.info("Retrying %d pending post(s)...", len(pending))
    still_pending = []
    sent_count = 0
    for item in pending:
        date_obj = datetime.datetime.strptime(item['date_str'], '%Y-%m-%d')
        success = await send_telegram_message(
            client,
            item['title'],
            date_obj,
            item['url'],
            item.get('rt_score'),
            item.get('imdb_rating'),
            item.get('genre'),
        )
        if success:
            seen_posts.add(item['post_id'])
            imdb_id = extract_imdb_id(item['url'])
            if imdb_id:
                seen_imdb.add(imdb_id)
            sent_count += 1
        else:
            item['attempts'] = item.get('attempts', 1) + 1
            if item['attempts'] <= MAX_SEND_ATTEMPTS:
                still_pending.append(item)
            else:
                log.error(
                    "Giving up on '%s' after %d send attempts.",
                    item['title'],
                    MAX_SEND_ATTEMPTS,
                )
                seen_posts.add(item['post_id'])
                imdb_id = extract_imdb_id(item['url'])
                if imdb_id:
                    seen_imdb.add(imdb_id)
                save_seen_post(
                    item['post_id'],
                    item['date_str'],
                    item['title'],
                    item['url'],
                    item.get('rt_score'),
                    item.get('imdb_rating'),
                    item.get('genre'),
                )
    pending[:] = still_pending
    save_pending(pending)
    return sent_count


REDDIT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'application/rss+xml, application/xml;q=0.9, */*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}

FALLBACK_REDDIT_URLS = [
    'https://www.reddit.com/r/movieleaks.rss',
    'https://www.reddit.com/r/movieleaks/.rss',
]


def _is_login_redirect(response):
    location = response.headers.get('location', '')
    return response.status_code in (301, 302, 303, 307, 308) and '/login/' in location


async def fetch_reddit_rss(client):
    for attempt in range(5):
        try:
            response = await client.get(
                REDDIT_URL,
                headers=REDDIT_HEADERS,
                follow_redirects=False,
                timeout=15.0,
            )
            if _is_login_redirect(response) or response.status_code == 403:
                log.warning(
                    "%s returned %s, trying fallback URLs...",
                    REDDIT_URL,
                    response.status_code,
                )
                for url in FALLBACK_REDDIT_URLS:
                    if url == REDDIT_URL:
                        continue
                    fallback = await client.get(
                        url,
                        headers=REDDIT_HEADERS,
                        follow_redirects=True,
                        timeout=15.0,
                    )
                    if not _is_login_redirect(fallback) and fallback.status_code == 200:
                        log.info("Using fallback feed: %s", url)
                        feed = feedparser.parse(fallback.text)
                        return feed.entries
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            return feed.entries
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = 2 ** (attempt + 4) + random.randint(0, 60)
                log.warning(
                    "Reddit rate limited (429). Attempt %d/5. Waiting %ds...",
                    attempt + 1,
                    wait,
                )
                await asyncio.sleep(wait)
            else:
                log.error("Failed to fetch RSS: %s", e)
                return None
        except Exception as e:
            log.error("Failed to fetch RSS: %s", e)
            return None
    log.error("Reddit RSS still rate limited after 5 attempts.")
    return None


async def main():
    validate_env()
    log.info("Starting Movie News Bot (v4 - async, cached, alerting)...")
    seen_posts, seen_imdb = load_seen_data()
    log.info("Loaded %d seen posts, %d unique movies", len(seen_posts), len(seen_imdb))

    consecutive_failures = 0
    last_heartbeat = time.monotonic()
    posts_since_heartbeat = 0
    alerts_sent = 0
    pending = load_pending()
    omdb_cache = load_omdb_cache()
    omdb_semaphore = asyncio.Semaphore(OMDB_CONCURRENCY)
    if pending:
        log.info("Loaded %d pending post(s) from queue.", len(pending))
    if omdb_cache:
        log.info("Loaded %d cached movie info entries.", len(omdb_cache))

    async with httpx.AsyncClient() as client:
        while True:
            try:
                sent_from_queue = await retry_pending(client, seen_posts, seen_imdb, pending)
                if sent_from_queue:
                    posts_since_heartbeat += sent_from_queue

                entries = await fetch_reddit_rss(client)

                if entries is None:
                    consecutive_failures += 1
                    log.warning("Feed fetch failed (%d consecutive).", consecutive_failures)
                    if consecutive_failures == CONSECUTIVE_FAILURE_ALERT:
                        await send_status_message(
                            client,
                            f"⚠️ Movie bot alert: Reddit feed failed {consecutive_failures} "
                            f"times in a row. The bot may be down or Reddit is blocking it.",
                        )
                        alerts_sent += 1
                else:
                    consecutive_failures = 0
                    tasks = [
                        process_entry(
                            client, entry, seen_posts, seen_imdb, pending,
                            omdb_cache, omdb_semaphore,
                        )
                        for entry in entries
                    ]
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    new_count = 0
                    for result in results:
                        if isinstance(result, Exception):
                            log.error("Error processing entry: %s", result)
                        elif result == 'sent':
                            new_count += 1
                            posts_since_heartbeat += 1

                    if new_count == 0:
                        log.info(
                            "No new posts found (%d in feed). Checking again in %ds...",
                            len(entries),
                            POLL_INTERVAL,
                        )
                    else:
                        log.info(
                            "Posted %d new movie(s). Checking again in %ds...",
                            new_count,
                            POLL_INTERVAL,
                        )

                if time.monotonic() - last_heartbeat >= HEARTBEAT_INTERVAL:
                    hours = HEARTBEAT_INTERVAL // 3600
                    status = "✅" if consecutive_failures == 0 else "⚠️"
                    await send_status_message(
                        client,
                        f"{status} Movie bot alive.\n"
                        f"📨 {posts_since_heartbeat} movie(s) posted in the last {hours}h.\n"
                        f"🚨 {alerts_sent} alert(s) triggered.\n"
                        f"🗂 {len(seen_posts)} posts tracked total.",
                    )
                    last_heartbeat = time.monotonic()
                    posts_since_heartbeat = 0
                    alerts_sent = 0

                await asyncio.sleep(POLL_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                log.error("Main loop error: %s", e)
                consecutive_failures += 1
                if consecutive_failures == CONSECUTIVE_FAILURE_ALERT:
                    await send_status_message(
                        client,
                        f"⚠️ Movie bot alert: main loop errored {consecutive_failures} times in a row.",
                    )
                await asyncio.sleep(60)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down.")
