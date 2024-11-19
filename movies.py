import os
import sys
import json
import time
import requests
import asyncio
import datetime
import urllib.request
from bs4 import BeautifulSoup
from telegram import Bot

from urlextract import URLExtract
import movieposters as mp
from dotenv import load_dotenv

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Load environment variables
load_dotenv()

# Configuration
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SEEN_POSTS_FILE = 'seen_posts.txt'

# API Settings
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID')
REDDIT_URL = os.getenv('REDDIT_URL')

# Initialize bot
bot = Bot(token=BOT_TOKEN)

# File Management Functions
def load_seen_posts():
    """Load seen posts from file."""
    print("\n[DEBUG] Loading seen posts from file...")
    if os.path.exists(SEEN_POSTS_FILE):
        with open(SEEN_POSTS_FILE, 'r') as f:
            posts = set(line.strip() for line in f.readlines())
            print(f"[DEBUG] Loaded {len(posts)} seen posts")
            return posts
    print("[DEBUG] No seen posts file found, creating new set")
    return set()

def save_seen_posts(seen_posts):
    """Save seen posts to file."""
    print(f"\n[DEBUG] Saving {len(seen_posts)} posts to file...")
    with open(SEEN_POSTS_FILE, 'w') as f:
        for post_id in seen_posts:
            f.write(post_id + '\n')
    print("[DEBUG] Posts saved successfully")

# URL and Data Extraction Functions
def extract_url(text):
    """Extract the first URL from text."""
    print("\n[DEBUG] Extracting URL from text...")
    extractor = URLExtract()
    urls = extractor.find_urls(text)
    result = urls[0] if urls else None
    print(f"[DEBUG] Extracted URL: {result}")
    return result


async def send_message(message, poster_file):
    print("\n[DEBUG] Preparing to send message to Telegram...")
    print(f"[DEBUG] Message length: {len(message)} characters")
    print(f"[DEBUG] Poster file: {poster_file}")
    try:
 #       await bot.send_message(chat_id=GROUP_CHAT_ID, text=message)
        print("[DEBUG] Message sent successfully to Telegram")
    except Exception as e:
        print(f"[ERROR] Failed to send message: {str(e)}")

# Reddit Functions
def fetch_latest_posts():
    """Fetch the latest posts from Reddit."""
    print("\n[DEBUG] Fetching latest posts from Reddit...")
    try:
        request = urllib.request.Request(REDDIT_URL, headers=HEADERS)
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode())
        posts = data['data']['children']
        print(f"[DEBUG] Successfully fetched {len(posts)} posts")
        return posts
    except Exception as e:
        print(f"[ERROR] Error fetching Reddit posts: {str(e)}")
        return []

async def notify_new_posts(new_posts, seen_posts):
    """Process and notify about new posts."""
    print(f"\n[DEBUG] Processing {len(new_posts)} new posts...")
    for post in new_posts:
        post_data = post['data']
        title = post_data['title']
        post_id = post_data['id']
        print(f"\n[DEBUG] Processing post: {title[:50]}...")
        
        created = post_data['created']
        date = datetime.datetime.fromtimestamp(created)
        print(f"[DEBUG] Post date: {date}")
        
        url = extract_url(post_data['selftext'])
        if not url:
            print("[DEBUG] No URL found in post, skipping...")
            continue
            
        if "trakt.tv" in url:
            print("[DEBUG] Trakt.tv URL detected, skipping...")
            continue
            
        if "imdb.com" not in url:
            print("[DEBUG] Not an IMDB URL, skipping...")
            continue

        print(f"[DEBUG] Valid IMDB URL found: {url}")
        print(f"[DEBUG] Extracting film ID from URL: {url}")
        try:
            film_id = url.split("title/")[1].split("/")[0].strip()
            poster_url = mp.get_poster(id=film_id)
            print(f"[DEBUG] Found poster URL: {poster_url}")
        except Exception as e:
            print(f"[ERROR] Failed to get poster: {str(e)}")
            continue
        
        # Handle movie poster
        if not os.path.exists('posters'):
            os.makedirs('posters')
        poster_file = os.path.join('posters', f'{film_id}.jpg')
        urllib.request.urlretrieve(poster_url, poster_file)

        # Prepare and send message
        message = (f"New Film: {title}\n"
                  f"Date: {date}\n"
                  f"Link: {post_data['selftext']}\n\n")

        await send_message(message, poster_file)
        seen_posts.add(post_id)

async def check_for_new_films(seen_posts):
    """Check for new films and process them."""
    latest_posts = fetch_latest_posts()
    new_posts = [post for post in latest_posts if post['data']['id'] not in seen_posts]
    if new_posts:
        await notify_new_posts(new_posts, seen_posts)
        save_seen_posts(seen_posts)

# Main Function
async def main():
    """Main function to poll the Reddit page."""
    print("\n[DEBUG] Starting Movie News Bot...")
    print("[DEBUG] Loading configuration...")
    print(f"[DEBUG] Reddit URL: {REDDIT_URL}")
    print(f"[DEBUG] Telegram Chat ID: {GROUP_CHAT_ID}")
    
    seen_posts = load_seen_posts()
    while True:
        try:
            print("\n[DEBUG] Starting new polling cycle...")
            await check_for_new_films(seen_posts)
            print("[DEBUG] Sleeping for 30 minutes before next check...")
            await asyncio.sleep(1800)
        except Exception as e:
            print(f"[ERROR] Error in main loop: {str(e)}")
            await asyncio.sleep(60)  # Wait a minute before retrying

if __name__ == '__main__':
    asyncio.run(main())
