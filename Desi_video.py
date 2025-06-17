import os
import random
import asyncio
import aiohttp
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
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

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # Use -100 prefix for channels
PORT = int(os.getenv("PORT", 3000))

DOWNLOAD_DIR = os.path.join("app", "src", "download")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

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

app = Flask(__name__)
bot = Client("video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

@app.route('/')
def home():
    return '✅ Bot is running!'

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

keywords = [
    "school", "desi", "college", "bhabhi",
    "aunty", "teacher", "milf", "teen",
    "stepmom", "neighbor", "office", "boss",
    "maid", "sister", "mom", "nurse",
    "secretary", "interview", "romance", "bathroom",
    "kitchen", "public", "hidden", "solo",
    "massage", "lesbian", "cousin", "student",
    "library", "bus", "train", "hotel",
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
                logger.warning(f"API status: {resp.status} from {api_url}")
    except Exception as e:
        logger.error(f"API Fetch Error from {api_url}: {e}")
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
            logger.error("Download timed out")
            process.kill()
            await process.communicate()
            return False

        if process.returncode != 0:
            logger.error(f"Download failed with code {process.returncode}")
            return False

        return os.path.exists(output_path) and os.path.getsize(output_path) > 0

    except Exception as e:
        logger.error(f"Download exception: {str(e)}")
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
    except Exception as e:
        logger.error(f"Thumbnail convert failed: {e}")
    return False

async def auto_post():
    logger.info("🔁 Auto post started...")

    while True:
        try:
            for selected_api in API_LIST:
                logger.info(f"🌐 Processing API: {selected_api}")

                async with aiohttp.ClientSession() as session:
                    api_data = await fetch_api_data(session, selected_api)

                if not api_data:
                    logger.warning(f"⚠️ No data from API: {selected_api}")
                    await asyncio.sleep(60)  # wait before next API
                    continue

                success_count = 0
                for idx, item in enumerate(api_data[:5]):
                    if 'name' not in item or 'content_url' not in item:
                        logger.warning(f"❌ Invalid item at index {idx}: {item}")
                        continue

                    video_name = item['name'].strip()
                    video_date = item.get('upload_date', 'Unknown')
                    video_url = item['content_url']
                    thumb_url = item.get('thumbnail')

                    caption = (
                        f"Filename :<b>{video_name}</b>\n"
                        f"Uploading Date : <b>{video_date}</b>\n"
                    )

                    file_name = f"video_{idx}_{random.randint(1000,9999)}.mp4"
                    file_path = os.path.join(DOWNLOAD_DIR, file_name)

                    download_success = await download_video(video_url, file_path)
                    if not download_success:
                        logger.error(f"❌ Download failed for video {idx}")
                        continue

                    thumb_path = os.path.join(DOWNLOAD_DIR, f"thumb_{idx}.jpg")
                    thumb_ok = await prepare_thumbnail(thumb_url, thumb_path)
                    thumb_file = thumb_path if thumb_ok else None

                    try:
                        await bot.send_video(
                            chat_id=CHANNEL_ID,
                            video=file_path,
                            caption=caption,
                            parse_mode=ParseMode.HTML,
                            supports_streaming=True,
                            thumb=thumb_file
                        )
                        success_count += 1
                        logger.info(f"✅ Posted: {video_name}")
                    except Exception as e:
                        if "PEER_ID_INVALID" in str(e):
                            logger.error(f"❌ PEER_ID_INVALID error. Check your CHANNEL_ID and bot permissions!")
                            await asyncio.sleep(600)  # wait 10 mins before retrying
                            return
                        else:
                            logger.error(f"❌ Error sending video: {e}")

                    # Delete video and thumbnail files after sending
                    try:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        if thumb_file and os.path.exists(thumb_file):
                            os.remove(thumb_file)
                    except Exception as e:
                        logger.warning(f"Failed to delete files: {e}")

                    await asyncio.sleep(30)

                logger.info(f"✅ Finished API: {selected_api} | Videos posted: {success_count}")
                await asyncio.sleep(60)

        except Exception as e:
            logger.exception(f"🚨 Auto post error: {e}")

        logger.info("🕒 Sleeping for 5 minutes before next round...")
        await asyncio.sleep(300)

@bot.on_message(filters.command("start"))
async def start_bot(client, message):
    await message.reply("🤖 Bot is running!")

async def send_test_message():
    try:
        await bot.send_message(CHANNEL_ID, "✅ Bot started and this is a test message to verify channel ID and permissions.")
        logger.info("✅ Test message sent successfully to CHANNEL_ID")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send test message on startup: {e}")
        return False

if __name__ == "__main__":
    if shutil.which("aria2c") is None:
        logger.error("aria2c is not installed! Please install it first.")
        exit(1)

    Thread(target=run_flask, daemon=True).start()

    async def main():
        await bot.start()
        valid = await send_test_message()
        if not valid:
            logger.error("Bot cannot send messages to the provided CHANNEL_ID. Exiting...")
            await bot.stop()
            return

        bot.loop.create_task(auto_post())
        logger.info("🤖 Bot started and running.")
        await bot.idle()

    asyncio.run(main())
