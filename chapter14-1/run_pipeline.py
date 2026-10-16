import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

log_path = LOG_DIR / f"pipeline_{datetime.now():%Y%m%d}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(log_path, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

STEPS = [
    "src/collect_naver.py",
    "src/collect_tourism.py",
    "src/validate_data.py",
    "src/analyze.py",
    "src/generate_llm_report.py",
    "src/generate_pdf.py",
]


def run_step(script):
    logging.info("START %s", script)
    result = subprocess.run(
        [sys.executable, script],
        cwd=BASE_DIR,
        text=True,
    )
    if result.returncode != 0:
        logging.error("FAIL %s", script)
        raise SystemExit(result.returncode)
    logging.info("PASS %s", script)


def main():
    logging.info("PIPELINE START")
    for script in STEPS:
        run_step(script)
    logging.info("PIPELINE SUCCESS")


if __name__ == "__main__":
    main()
