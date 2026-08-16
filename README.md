# Movie News Bot

A Python-based bot that automatically aggregates movie news from Reddit and posts updates to Telegram. The bot monitors specified subreddits for new movie-related content and shares it with your audience through configured channels.

## Features

- 🤖 Automated content aggregation from Reddit
- 📱 Posting to Telegram (with Rotten Tomatoes / IMDb ratings and genres)
- 🔄 Duplicate post prevention
- 💾 Failed-send retry queue and offline cache
- 📊 Health heartbeats and failure alerts
- ⚡ Real-time updates
- 🔒 Secure credential management
- 📝 Post history tracking

## Prerequisites

- Python 3.8 or higher
- Node.js and npm (for PM2)
- A Telegram Bot Token (obtained from [@BotFather](https://t.me/botfather))
- A Telegram Group/Channel ID
- Reddit API access

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/movie-news-bot.git
   cd movie-news-bot
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the root directory:
   ```env
   # Telegram Settings
   BOT_TOKEN=your_telegram_bot_token
   GROUP_CHAT_ID=your_group_chat_id

   # Reddit Settings
   REDDIT_URL=https://www.reddit.com/r/movieleaks.rss

   # OMDB (ratings & genres) - free key from https://www.omdbapi.com/apikey.aspx
   OMDB_API_KEY=your_omdb_api_key

   # Optional - chat for alerts/heartbeats (defaults to GROUP_CHAT_ID)
   ALERT_CHAT_ID=your_alert_chat_id
   ```

5. Install PM2 globally and set up the process:
   ```bash
   npm install -g pm2
   ```

6. Start the bot with PM2:
   ```bash
   pm2 start start.sh --name barry --interpreter bash
   pm2 save
   ```

7. (Optional) Configure PM2 to auto-start on boot:
   ```bash
   pm2 startup systemd
   ```
   Run the command it outputs to enable the systemd service.

## Telegram Bot Setup

1. Create a new bot:
   - Open Telegram and search for [@BotFather](https://t.me/botfather)
   - Send `/newbot` command
   - Follow the prompts to create your bot
   - Save the provided API token

2. Get your Group Chat ID:
   - Add your bot to the target group
   - Make the bot an admin
   - Send a message to the group
   - Visit: `https://api.telegram.org/bot<YourBOTToken>/getUpdates`
   - Look for "chat":{"id": -XXXXXXXXXX} in the response
   - Use this number as your GROUP_CHAT_ID

## Usage

The bot runs via `start.sh` under PM2, which loops `movies.py` and restarts it on crash.

- **Start**: `pm2 start start.sh --name barry --interpreter bash`
- **Stop**: `pm2 stop barry`
- **Restart**: `pm2 restart barry`
- **Logs**: `pm2 logs barry`
- **Save process list** (for reboot persistence): `pm2 save`

The bot will:
   - Monitor specified subreddits for new posts
   - Filter and process relevant content
    - Post updates to Telegram
   - Track posted content to prevent duplicates

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| BOT_TOKEN | Telegram bot API token | `your_telegram_bot_token` |
| GROUP_CHAT_ID | Telegram group/channel ID | `your_group_chat_id` |
| REDDIT_URL | Reddit RSS feed URL | `https://www.reddit.com/r/movieleaks.rss` |
| OMDB_API_KEY | OMDB API key for ratings/genres | `your_omdb_api_key` |
| ALERT_CHAT_ID | Chat for alerts/heartbeats (defaults to GROUP_CHAT_ID) | `your_alert_chat_id` |
| POLL_INTERVAL | Seconds between feed checks (default `1800`) | `1800` |
| HEARTBEAT_INTERVAL | Seconds between status heartbeats (default `86400`) | `86400` |


## File Structure

```
movie-news-bot/
├── movies.py           # Main bot script
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── .gitignore         # Git ignore rules
├── start.sh           # Wrapper that restarts the bot on crash
├── seen_posts.txt     # Tracking file for posted content
├── pending_posts.json # Retry queue for failed sends
└── omdb_cache.json    # Cached ratings/genres (saves OMDB API quota)
```

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/improvement`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature/improvement`)
5. Create a Pull Request

## Security Notes

- Never commit your `.env` file to version control
- Regularly rotate your API tokens and passwords
- Use strong passwords for all accounts
- Monitor your bot's activity regularly

## Troubleshooting

### Common Issues

1. **Bot not posting to Telegram**
   - Verify bot token is correct
   - Ensure bot has admin privileges in the group
   - Check GROUP_CHAT_ID is correct

2. **Missing posts**
   - Check seen_posts.txt permissions
   - Verify Reddit URL is accessible
   - Check internet connectivity

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Reddit API
- OMDB API
- httpx
- Python dotenv


