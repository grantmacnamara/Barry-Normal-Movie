# Movie News Bot

A Python-based bot that automatically aggregates movie news from Reddit and posts updates to Telegram and Instagram. The bot monitors specified subreddits for new movie-related content and shares it with your audience through configured channels.

## Features

- 🤖 Automated content aggregation from Reddit
- 📱 Cross-platform posting to Telegram and Instagram
- 🔄 Duplicate post prevention
- ⚡ Real-time updates
- 🔒 Secure credential management
- 📝 Post history tracking

## Prerequisites

- Python 3.8 or higher
- A Telegram Bot Token (obtained from [@BotFather](https://t.me/botfather))
- A Telegram Group/Channel ID
- Reddit API access
- Instagram account credentials

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/movie-news-bot.git
   cd movie-news-bot
   ```

2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   venv\Scripts\activate

   # macOS/Linux
   python -m venv venv
   source venv/bin/activate
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
   REDDIT_URL=https://www.reddit.com/r/movieleaks.json

   # Instagram Settings
   INSTAGRAM_USERNAME=your_instagram_username
   INSTAGRAM_PASSWORD=your_instagram_password
   ```

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

1. Start the bot:
   ```bash
   python movies.py
   ```

2. The bot will:
   - Monitor specified subreddits for new posts
   - Filter and process relevant content
   - Post updates to Telegram and Instagram
   - Track posted content to prevent duplicates

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| BOT_TOKEN | Telegram bot API token | `5555555555:AAHtby6kGqXGNgDuTYM7IeCQ2eUgl_dmhHY` |
| GROUP_CHAT_ID | Telegram group/channel ID | `-1002475527084` |
| REDDIT_URL | Reddit JSON feed URL | `https://www.reddit.com/r/movieleaks.json` |
| INSTAGRAM_USERNAME | Instagram account username | `movieupdates` |
| INSTAGRAM_PASSWORD | Instagram account password | `yourpassword` |

## File Structure

```
movie-news-bot/
├── movies.py           # Main bot script
├── requirements.txt    # Python dependencies
├── .env               # Environment variables
├── .gitignore         # Git ignore rules
└── seen_posts.txt     # Tracking file for posted content
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

2. **Instagram login fails**
   - Verify credentials are correct
   - Check for Instagram security challenges
   - Consider using 2FA if required

3. **Missing posts**
   - Check seen_posts.txt permissions
   - Verify Reddit URL is accessible
   - Check internet connectivity

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Reddit API
- python-telegram-bot
- Instabot
- Python dotenv


