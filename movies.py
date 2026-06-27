import json
import asyncio
import datetime
import re
import unicodedata
import random
from pathlib import Path
from urlextract import URLExtract
from dotenv import load_dotenv
from telegram import Bot
import os
import httpx
import feedparser

load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('GROUP_CHAT_ID')
REDDIT_URL = os.getenv('REDDIT_URL')
OMDB_API_KEY = os.getenv('OMDB_API_KEY')
SEEN_POSTS_FILE = Path('seen_posts.txt')

USER_AGENT = 'script:BarryNormalMovieBot:v2.0 (by /u/barrynormalmovies)'

bot = Bot(token=BOT_TOKEN)


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
        print(f"[WARN] Failed to load seen data: {e}")
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
    except Exception as e:
        print(f"[WARN] Failed to save post: {e}")

def is_valid_movie_url(text):
    urls = URLExtract().find_urls(text)
    for url in urls:
        if "imdb.com" in url:
            return url
    return None

def extract_imdb_id(url):
    match = re.search(r'/title/(tt\d+)', url)
    return match.group(1) if match else None

def make_rt_slug(title):
    if not title:
        return None
    slug = re.sub(r'\s*[\[\(]\d{4}[\]\)]\s*', '', title)
    slug = slug.strip()
    slug = unicodedata.normalize('NFKD', slug)
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    slug = slug.replace("'", "").replace(":", "").replace(".", "").replace("-", " ")
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug.lower()

async def scrape_rt_tomatometer(client, title):
    if not title:
        return None
    slug = make_rt_slug(title)
    if not slug:
        return None
    try:
        url = f"https://www.rottentomatoes.com/m/{slug}"
        headers = {'User-Agent': USER_AGENT}
        response = await client.get(url, headers=headers, follow_redirects=True, timeout=10.0)
        response.raise_for_status()
        for match in re.finditer(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', response.text, re.DOTALL):
            data = json.loads(match.group(1))
            ar = data.get('aggregateRating', {})
            if isinstance(ar, dict) and ar.get('name') == 'Tomatometer':
                val = ar.get('ratingValue')
                if val:
                    return val + '%'
        match = re.search(r'(\d+)%","title":"Tomatometer"', response.text)
        if match:
            return match.group(1) + '%'
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            print(f"[WARN] RT scrape error for '{title}' (slug: {slug}): {e}")
    except Exception as e:
        print(f"[WARN] Failed to scrape RT for '{title}' (slug: {slug}): {e}")
    return None

async def fetch_movie_info(client, imdb_id):
    if not OMDB_API_KEY or not imdb_id:
        return None, None, None
    try:
        url = f"https://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_API_KEY}"
        response = await client.get(url)
        response.raise_for_status()
        data = response.json()
        if data.get('Response') != 'True':
            return None, None, None
        genre = data.get('Genre')
        title = data.get('Title', '')
        rt_score = await scrape_rt_tomatometer(client, title)
        imdb_val = data.get('imdbRating')
        imdb_rating = imdb_val + '/10' if imdb_val and imdb_val != 'N/A' else None
        return rt_score, imdb_rating, genre
    except Exception as e:
        print(f"[WARN] Failed to fetch movie info for {imdb_id}: {e}")
    return None, None, None

async def send_telegram_message(title, date, url, rt_score=None, imdb_rating=None, genre=None):
    date_str = date.strftime('%d %b %Y') if isinstance(date, datetime.datetime) else str(date)
    message = f"🎬 {title}\n📅 {date_str}"
    if genre:
        message += f"\n🏷 {genre}"
    if rt_score:
        message += f"\n🍅 {rt_score}"
    if imdb_rating:
        message += f"\n⭐ {imdb_rating}"
    message += f"\n🔗 {url}"
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"[INFO] Sent: {title}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send {title}: {e}")
        err_str = str(e)
        if 'Flood control exceeded' in err_str:
            match = re.search(r'Retry in (\d+) seconds', err_str)
            wait = int(match.group(1)) + 2 if match else 30
            print(f"[INFO] Waiting {wait}s for flood control...")
            await asyncio.sleep(wait)
        return False

async def process_entry(client, entry, seen_posts, seen_imdb):
    post_id = entry.get('id', '').split('_')[-1]
    if not post_id or post_id in seen_posts:
        return False

    content = entry.get('content', [{}])[0].get('value', '') + ' ' + entry.get('summary', '')

    if url := is_valid_movie_url(content):
        imdb_id = extract_imdb_id(url)
        if imdb_id and imdb_id in seen_imdb:
            seen_posts.add(post_id)
            return False

        updated_parsed = entry.get('updated_parsed')
        date_obj = datetime.datetime(*updated_parsed[:6]) if updated_parsed else datetime.datetime.now()
        rt_score, imdb_rating, genre = await fetch_movie_info(client, imdb_id)
        title = entry.get('title', 'No Title')
        date_str = date_obj.strftime('%Y-%m-%d')
        success = await send_telegram_message(
            title,
            date_obj,
            url,
            rt_score,
            imdb_rating,
            genre
        )
        if success:
            save_seen_post(post_id, date_str, title, url, rt_score, imdb_rating, genre)
            seen_posts.add(post_id)
            if imdb_id:
                seen_imdb.add(imdb_id)
            return True
        return False
    return False

async def fetch_reddit_rss(client):
    for attempt in range(5):
        try:
            response = await client.get(
                REDDIT_URL,
                headers={'User-Agent': USER_AGENT},
                timeout=15.0
            )
            response.raise_for_status()
            feed = feedparser.parse(response.text)
            return feed.entries
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = 2 ** (attempt + 4) + random.randint(0, 60)
                print(f"[WARN] Reddit rate limited (429). Attempt {attempt+1}/5. Waiting {wait}s...")
                await asyncio.sleep(wait)
            else:
                print(f"[ERROR] Failed to fetch RSS: {e}")
                return []
        except Exception as e:
            print(f"[ERROR] Failed to fetch RSS: {e}")
            return []
    print(f"[ERROR] Reddit RSS still rate limited after 5 attempts.")
    return []

async def main():
    print("[INFO] Starting Movie News Bot (v2 - full overhaul)...")
    seen_posts, seen_imdb = load_seen_data()
    print(f"[INFO] Loaded {len(seen_posts)} seen posts, {len(seen_imdb)} unique movies")

    async with httpx.AsyncClient() as client:
        while True:
            try:
                entries = await fetch_reddit_rss(client)
                new_count = 0
                for entry in entries:
                    if await process_entry(client, entry, seen_posts, seen_imdb):
                        new_count += 1

                if new_count == 0:
                    print(f"[INFO] No new posts found ({len(entries)} in feed). Checking again in 30 minutes...")
                else:
                    print(f"[INFO] Posted {new_count} new movie(s). Checking again in 30 minutes...")

                await asyncio.sleep(1800)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                print(f"[ERROR] Main loop error: {e}")
                await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(main())
