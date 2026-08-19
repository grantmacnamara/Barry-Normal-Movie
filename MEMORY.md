# Barry Normal Movie Bot - Memory

## Process Management
- Bot runs under **PM2** as process name `barry`
- Start: `pm2 start barry`
- Stop: `pm2 stop barry`
- Restart: `pm2 restart barry`
- Logs: `pm2 logs barry`
- **Do NOT kill PID manually** - use PM2 commands

## Previous Fixes
1. **Admin tag in titles** - Reddit RSS now prepends "(admin)" to some post titles. Fixed by adding `clean_title()` function to strip it.
2. **URL preview missing** - `disable_web_page_preview=True` was set in `send_telegram_message()`. Changed to `False` to restore previews.

## Missing Posts
- If a movie is in `seen_posts.txt` but not in Telegram, the send likely failed after 5 retries
- To resend: remove the line from `seen_posts.txt`, then `pm2 restart barry`
- Pending queue (`pending_posts.json`) stores failed sends for retry

## Key Files
- `movies.py` - Main bot script
- `seen_posts.txt` - Tracks processed posts (format: `post_id | date | title | url | ratings | genre`)
- `pending_posts.json` - Queue of failed sends awaiting retry
- `omdb_cache.json` - Cached OMDB API responses
- `start.sh` - Legacy startup script (PM2 is preferred)
- `.env` - Environment variables (BOT_TOKEN, GROUP_CHAT_ID, REDDIT_URL, OMDB_API_KEY)

## Environment Variables
- `BOT_TOKEN` - Telegram bot token
- `GROUP_CHAT_ID` - Target Telegram group/channel
- `ALERT_CHAT_ID` - Alert destination (defaults to GROUP_CHAT_ID)
- `REDDIT_URL` - Reddit RSS feed URL
- `OMDB_API_KEY` - OMDB API key
- `POLL_INTERVAL` - Seconds between polls (default: 1800)
- `HEARTBEAT_INTERVAL` - Seconds between heartbeat messages (default: 86400)
