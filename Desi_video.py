import os
import random
import asyncio
import aiohttp
import tempfile
import subprocess
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
import logging
import shutil
from PIL import Image
from io import BytesIO

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
PORT = int(os.getenv("PORT", 3000))

# Validate required environment variables
if not all([API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID]):
    logger.error("Missing one or more required environment variables: API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID")
    exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error("API_ID must be an integer")
    exit(1)

try:
    CHANNEL_ID = int(CHANNEL_ID)
except ValueError:
    logger.error("CHANNEL_ID must be an integer (include -100 prefix for channels)")
    exit(1)

app = Flask(__name__)
bot = Client("video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

BLACKLIST_FILE = "blacklist.txt"

def get_random_headers():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
    ]
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "*/*",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache"
    }

def is_blacklisted(name: str) -> bool:
    if not os.path.exists(BLACKLIST_FILE):
        return False
    with open(BLACKLIST_FILE, "r", encoding="utf-8") as f:
        return name.strip().lower() in (line.strip().lower() for line in f)

def add_to_blacklist(name: str):
    with open(BLACKLIST_FILE, "a", encoding="utf-8") as f:
        f.write(f"{name.strip()}\n")

@app.route('/')
def home():
    return '✅ Bot is running!'

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

keywords = [
    # Original keywords
    "school", "desi", "college", "bhabhi",
    "aunty", "teacher", "milf", "teen",
    "stepmom", "neighbor", "office", "boss",
    "maid", "sister", "mom", "nurse",
    "secretary", "interview", "romance", "bathroom",
    "kitchen", "public", "hidden", "solo",
    "massage", "lesbian", "cousin", "student",
    "library", "bus", "train", "hotel",

    # Additional keywords
    "stepsister", "stepbrother", "stepdad", "uncle",
    "daddy", "family", "relative",

    "doctor", "patient", "cop", "lawyer",
    "therapist", "trainer", "coach", "delivery",
    "plumber", "mechanic",

    "classroom", "locker room", "dressing room",
    "office desk", "elevator", "parking lot",

    "cheating", "revenge", "blackmail", "voyeur",
    "seduction", "domination", "submission",
    "rough", "softcore", "roleplay",

    "big boobs", "curvy", "petite", "thick",
    "busty", "shaved", "natural", "tattoo", "glasses"
]

API_LIST = [f"https://you-pom-lover.vercel.app/xnxx/5/{word}" for word in keywords]

async def fetch_api_data(session, api_url):
    try:
        async with session.get(api_url, headers=get_random_headers(), timeout=20) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("data", [])
            else:
                logger.warning(f"API returned status {resp.status} for URL: {api_url}")
    except Exception as e:
        logger.error(f"Error fetching API data from {api_url}: {e}")
    return []

async def download_video(video_url, output_path):
    try:
        cmd = [
            "aria2c",
            video_url,
            "--out", os.path.basename(output_path),
            "--dir", os.path.dirname(output_path),
            "--allow-overwrite=true",
            "--max-connection-per-server=16",
            "--split=16",
            "--summary-interval=0",
            "--console-log-level=warn"
        ]
        logger.info(f"Downloading video: {video_url}")
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            await asyncio.wait_for(process.communicate(), timeout=300)
        except asyncio.TimeoutError:
            logger.error("Video download timed out")
            process.kill()
            await process.communicate()
            return False

        if process.returncode != 0:
            logger.error(f"aria2c exited with code {process.returncode}")
            return False

        file_exists = os.path.exists(output_path) and os.path.getsize(output_path) > 0
        if not file_exists:
            logger.error("Downloaded file not found or empty")
        return file_exists
    except Exception as e:
        logger.error(f"Exception in downloading video: {e}")
        return False

async def prepare_thumbnail(url, path):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    img_bytes = await resp.read()
                    img = Image.open(BytesIO(img_bytes)).convert("RGB")
                    img.save(path, "JPEG")
                    return True
                else:
                    logger.warning(f"Thumbnail request returned status {resp.status}")
    except Exception as e:
        logger.error(f"Failed to prepare thumbnail: {e}")
    return False

async def auto_post():
    logger.info("🔁 Auto post started...")
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                for selected_api in API_LIST:
                    logger.info(f"🌐 Processing API: {selected_api}")

                    with tempfile.TemporaryDirectory() as temp_dir:
                        api_data = await fetch_api_data(session, selected_api)

                        if not api_data:
                            logger.warning(f"⚠️ No data received from API: {selected_api}")
                            await asyncio.sleep(60)
                            continue

                        success_count = 0
                        for idx, item in enumerate(api_data[:5]):
                            if 'name' not in item or 'content_url' not in item:
                                logger.warning(f"❌ Invalid data format at index {idx} in API data")
                                continue

                            video_name = item['name'].strip()
                            video_date = item.get('upload_date', 'Unknown Date')
                            video_url = item['content_url']
                            thumb_url = item.get('thumbnail')

                            if is_blacklisted(video_name):
                                logger.info(f"🚫 Skipping blacklisted video: {video_name}")
                                continue

                            caption = (
                                f"Filename :<b>{video_name}</b>\n"
                                f"Uploading Date : <b>{video_date}</b>\n"
                            )

                            file_name = f"video_{idx}_{random.randint(1000,9999)}.mp4"
                            file_path = os.path.join(temp_dir, file_name)

                            download_success = await download_video(video_url, file_path)
                            if not download_success:
                                logger.error(f"❌ Failed to download video: {video_name}")
                                continue

                            thumb_path = os.path.join(temp_dir, f"thumb_{idx}.jpg")
                            thumb_ok = False
                            if thumb_url:
                                thumb_ok = await prepare_thumbnail(thumb_url, thumb_path)

                            try:
                                await bot.send_video(
                                    chat_id=CHANNEL_ID,
                                    video=file_path,
                                    caption=caption,
                                    parse_mode=ParseMode.HTML,
                                    supports_streaming=True,
                                    thumb=thumb_path if thumb_ok else None
                                )
                                add_to_blacklist(video_name)
                                success_count += 1
                                logger.info(f"✅ Posted video: {video_name}")
                            except Exception as e:
                                logger.error(f"❌ Failed to send video '{video_name}': {e}")

                            await asyncio.sleep(30)  # Delay to avoid Telegram rate limit

                    logger.info(f"✅ Finished API: {selected_api} | Videos posted: {success_count}")
                    await asyncio.sleep(60)

            except Exception as e:
                logger.exception(f"🚨 Error in auto_post loop: {e}")

            logger.info("🕒 Sleeping for 5 minutes before next round...")
            await asyncio.sleep(300)

@bot.on_message(filters.command("start"))
async def start_handler(client, message):
    await message.reply("🤖 Bot is running!")

@bot.on_message(filters.command("check"))
async def check_channel_access(client, message):
    try:
        await bot.send_message(CHANNEL_ID, "✅ Check: Bot has access to this chat!")
        await message.reply("✅ Successfully sent message to the channel/group!")
    except Exception as e:
        await message.reply(f"❌ Failed to send message to channel/group. Error:\n{e}")

if __name__ == "__main__":
    if shutil.which("aria2c") is None:
        logger.error("aria2c is not installed! Please install aria2c first.")
        exit(1)

    # Start Flask server in a separate thread
    Thread(target=run_flask, daemon=True).start()

    # Start the auto_post coroutine
    bot.loop.create_task(auto_post())

    logger.info("🤖 Bot is starting...")
    bot.run()
