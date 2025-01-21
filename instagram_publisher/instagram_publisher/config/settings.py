"""Configuration settings for Instagram Publisher"""
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

# Base paths
BASE_PATH = Path('/mongodb/silicon_sentiments')
INSTAGRAM_IMAGES_DIR = BASE_PATH / 'data/images/instagram'
LOG_DIR = BASE_PATH / 'logs'

# MongoDB configuration
MONGO_URI = 'mongodb://tappiera00:tappiera00@127.0.0.1:27017/instagram_db?authSource=admin'
DB_NAME = 'instagram_db'

# Instagram API configuration
INSTAGRAM_APP_ID = os.getenv("INSTAGRAM_APP_ID")
INSTAGRAM_APP_SECRET = os.getenv("INSTAGRAM_APP_SECRET")
INSTAGRAM_LONG_TOKEN = os.getenv("INSTAGRAM_LONG_TOKEN")
INSTAGRAM_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

API_VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

# Image hosting
IMAGE_HOST = "https://siliconsents.duckdns.org/images/instagram"

# Hashtags configuration
ALL_HASHTAGS = [
    "#aiart", "#aiartwork", "#aiartcommunity", "#aiartist", "#artificialintelligence", 
    "#aiartwork", "#digitalart", "#digitalartist", "#modernart", "#contemporaryart",
    "#abstractart", "#surrealism", "#surreal", "#surrealist", "#psychedelic",
    "#psychedelicart", "#trippy", "#trippyart", "#fantasy", "#fantasyart",
    "#scifi", "#scifiart", "#cyberpunk", "#cyberpunkart", "#futuristic",
    "#futurism", "#future", "#generativeart", "#generative", "#proceduralart",
    "#computerart", "#computergeneratedart", "#newmediaart", "#creativecoding",
    "#codeart", "#algorithmicart", "#glitchart", "#cryptoart", "#nft", "#nftart",
    "#midjourney", "#midjourneyart", "#stablediffusion", "#dalle", "#openai",
    "#deeplearning", "#machinelearning", "#neuralart", "#aipainting", "#aigenerated",
    "#aicreativity", "#creativetechnology", "#arttech", "#arttechnology", "#techart",
    "#digitalillustration", "#conceptart", "#imaginativeart", "#imaginative", "#dreamy",
    "#dreamlike", "#ethereal", "#surrealdreams", "#unrealart", "#unrealengine",
    "#3dart", "#3dartist", "#render", "#cgi", "#vfx", "#visualeffects", "#animation",
    "#motionart", "#motiongraphics", "#experimentalart", "#artoftheday", "#artgallery",
    "#artwork", "#artistic", "#artlovers", "#artcollector", "#artcurator", "#artworld",
    "#contemporaryartist", "#emergingartist", "#newart", "#newartist", "#artmovement",
    "#arttrends", "#artinnovation", "#innovativeart", "#futureofart", "#artevolution",
    "#siliconsentiments", "#circuitdreams", "#bytevisions", "#quantumart", "#quantumdreams",
    "#neuralvisions", "#neuralart", "#neuralnetwork", "#deepdream", "#deepstyle"
]

# Social media engagement text
ENGAGEMENT_TEXT = """
💻 Like to empower the circuit
🔧 Comment to boost the bandwidth  
🤖 Follow for more silicon sentiments
"""