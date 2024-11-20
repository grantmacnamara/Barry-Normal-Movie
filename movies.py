import json
import asyncio
import datetime
import urllib.request
from pathlib import Path
from urlextract import URLExtract
from dotenv import load_dotenv
from telegram import Bot
import os

# Configuration
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('GROUP_CHAT_ID')
REDDIT_URL = os.getenv('REDDIT_URL')
HEADERS = {'User-Agent': 'Mozilla/5.0 (Chrome/91.0.4472.124)'}
SEEN_POSTS_FILE = Path('seen_posts.txt')

# Initialize bot
bot = Bot(token=BOT_TOKEN)

def load_seen_posts():
    """Load seen post IDs from file."""
    try:
        return set(SEEN_POSTS_FILE.read_text().splitlines()) if SEEN_POSTS_FILE.exists() else set()
    except Exception as e:
        print(f"[WARN] Failed to load seen posts: {e}")
        return set()

def save_seen_post(post_id):
    """Append new post ID to file."""
    try:
        with SEEN_POSTS_FILE.open('a') as f:
            f.write(f"{post_id}\n")
    except Exception as e:
        print(f"[WARN] Failed to save post ID: {e}")

def is_valid_movie_url(text):
    """Check if text contains valid IMDB URL."""
    urls = URLExtract().find_urls(text)
    return urls[0] if urls and "imdb.com" in urls[0] else None

async def send_telegram_message(title, date, url):
    """Send formatted message to Telegram."""
    message = f" {title}\n {date}\n {url}"
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message)
        print(f"[INFO] Sent: {title}")
    except Exception as e:
        print(f"[ERROR] Failed to send {title}: {e}")

async def process_post(post, seen_posts):
    """Process single Reddit post."""
    post_id = post['data']['id']
    if post_id in seen_posts:
        return False

    if url := is_valid_movie_url(post['data']['selftext']):
        await send_telegram_message(
            post['data']['title'],
            datetime.datetime.fromtimestamp(post['data']['created']),
            url
        )
        save_seen_post(post_id)
        seen_posts.add(post_id)
        return True
    return False

async def fetch_reddit_posts():
    """Fetch new posts from Reddit."""
    try:
        request = urllib.request.Request(REDDIT_URL, headers=HEADERS)
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())['data']['children']
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch posts: {e}")
        return []

async def main():
    """Monitor Reddit for new movie posts."""
    print("[INFO] Starting Movie News Bot...")
    seen_posts = load_seen_posts()
    print(f"[INFO] Loaded {len(seen_posts)} seen posts")
    
    while True:
        try:
            if posts := await fetch_reddit_posts():
                for post in posts:
                    await process_post(post, seen_posts)
                    print(f"[INFO] POST: {(post)}")
            print("[INFO] Checking again in 30 minutes...")
            await asyncio.sleep(1800)
            
        except Exception as e:
            print(f"[ERROR] Main loop error: {e}")
            await asyncio.sleep(60)

if __name__ == '__main__':
    asyncio.run(main())
