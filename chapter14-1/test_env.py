import os

from dotenv import load_dotenv

load_dotenv()

for name in [
    "NAVER_CLIENT_ID",
    "NAVER_CLIENT_SECRET",
    "TOURISM_SERVICE_KEY",
    "LLM_API_KEY",
]:
    status = "CONFIGURED" if os.getenv(name) else "MISSING"
    print(name, status)
