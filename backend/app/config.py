import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_VISION_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
MAX_SCRAPE = 20
TOP_CARS_FOR_AI = 10
TOP_CARS_FOR_VISION = 4
