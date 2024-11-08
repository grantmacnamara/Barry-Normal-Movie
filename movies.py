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
from instagrapi import Client
from urlextract import URLExtract
import movieposters as mp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
os.chdir(os.path.dirname(os.path.abspath(__file__)))
SEEN_POSTS_FILE = 'seen_posts.txt'

# API Settings
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROUP_CHAT_ID = os.getenv('GROUP_CHAT_ID')
REDDIT_URL = os.getenv('REDDIT_URL')
INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')

#group_chat_id = '-683964297' # Ladies who Festival
#group_chat_id = '-1002475527084' # Movies Updatates


# Initialize bot
bot = Bot(token=BOT_TOKEN)

# File Management Functions
def load_seen_posts():
    """Load seen posts from file."""
    if os.path.exists(SEEN_POSTS_FILE):
        with open(SEEN_POSTS_FILE, 'r') as f:
            return set(line.strip() for line in f.readlines())
    return set()

def save_seen_posts(seen_posts):
    """Save seen posts to file."""
    with open(SEEN_POSTS_FILE, 'w') as f:
        for post_id in seen_posts:
            f.write(post_id + '\n')

# URL and Data Extraction Functions
def extract_url(text):
    """Extract the first URL from text."""
    extractor = URLExtract()
    urls = extractor.find_urls(text)
    return urls[0] if urls else None

async def get_movie_rating(imdb_url):
    """Fetch movie rating from IMDB."""
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(imdb_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    rating_element = soup.find('span', class_='sc-d541859f-1 imUuxf')
    rating = rating_element.text if rating_element else 'N/A'
    return {'rating': rating}

async def get_movie_description(imdb_url):
    """Fetch movie description from IMDB."""
    description_url = f"{imdb_url.rstrip('/')}/plotsummary"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(description_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    description_element = soup.find('div', class_='ipc-html-content-inner-div')
    description = description_element.text.strip() if description_element else 'N/A'
    return {'description': description}

# Social Media Functions
def upload_post(username, password, image_path, caption):
    """Upload post to Instagram."""
    try:
        client = Client()
        client.login(username, password)
        media = client.photo_upload(image_path, caption)
        print("Instagram Post uploaded successfully")
        return True
    except Exception as e:
        print(f"Error uploading to Instagram: {str(e)}")
        return False

async def send_message(message, poster_file):

# Send to Telegram
    await bot.send_message(chat_id=GROUP_CHAT_ID, text=message)

    """Send message to Instagram."""
    try:
        success = upload_post(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD, poster_file, message)
        if success and os.path.exists(poster_file):
            os.remove(poster_file)
            print(f"Deleted poster file: {poster_file}")
        else:
            print(f"Failed to delete poster file: {poster_file}")
    except Exception as e:
        print(f"Error sending message: {str(e)}")

# Reddit Functions
def fetch_latest_posts():
    """Fetch the latest posts from Reddit."""
    try:
        request = urllib.request.Request(REDDIT_URL, headers=HEADERS)
        with urllib.request.urlopen(request) as response:
            data = json.loads(response.read().decode())
        return data['data']['children']
    except Exception as e:
        print(f"Error fetching Reddit posts: {str(e)}")
        return []

async def notify_new_posts(new_posts, seen_posts):
    """Process and notify about new posts."""
    for post in new_posts:
        post_data = post['data']
        title = post_data['title']
        post_id = post_data['id']
        created = post_data['created']
        date = datetime.datetime.fromtimestamp(created)
        url = extract_url(post_data['selftext'])

        # Handle movie poster
        film_id = url.split("title/")[1].split("/")[0].strip()
        poster_url = mp.get_poster(id=film_id)
        
        if not os.path.exists('posters'):
            os.makedirs('posters')
        poster_file = os.path.join('posters', f'{film_id}.jpg')
        urllib.request.urlretrieve(poster_url, poster_file)

        # Get movie details
        movie_rating = await get_movie_rating(url)
        movie_description = await get_movie_description(url)

        # Prepare and send message
        message = (f"New Film: {title}\n"
                  f"Date: {date}\n"
                  f"Link: {post_data['selftext']}\n\n"
                  f"Rating: {movie_rating['rating']}\n\n"
                  f"{movie_description['description']}")

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
    seen_posts = load_seen_posts()
    await check_for_new_films(seen_posts)

if __name__ == '__main__':
    asyncio.run(main())
