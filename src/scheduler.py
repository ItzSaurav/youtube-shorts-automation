# src/scheduler.py
"""
Automated YouTube Shorts Content Scheduler
Runs the complete YouTube Automation pipeline automatically at peak daily posting hours.

Usage:
  python src/scheduler.py          # Run continuously in the background (post at 09:00, 14:00, 19:00)
  python src/scheduler.py --now    # Run immediately once and exit
"""
import sys
import time
import logging
import subprocess
import argparse
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ShortsScheduler")

PEAK_HOURS = ["09:00", "14:00", "19:00"]


def run_pipeline():
    logger.info("🎬 Starting automated YouTube Short generation & publishing pipeline...")
    start_time = time.time()
    try:
        cmd = [sys.executable, "src/main.py"]
        res = subprocess.run(cmd, check=True)
        duration = time.time() - start_time
        logger.info(f"✅ Automated Short completed successfully in {duration:.1f}s!")
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Automated Short pipeline failed with exit code {e.returncode}")
    except Exception as e:
        logger.error(f"❌ Exception running automated pipeline: {e}")


def main():
    parser = argparse.ArgumentParser(description="YouTube Shorts Automated Scheduler")
    parser.add_argument("--now", action="store_true", help="Run the pipeline immediately once and exit")
    args = parser.parse_args()

    if args.now:
        logger.info("Running single immediate execution (--now flag detected)...")
        run_pipeline()
        return

    try:
        import schedule
    except ImportError:
        logger.error("❌ 'schedule' library not installed. Please run: pip install schedule")
        logger.info("Running immediately as fallback...")
        run_pipeline()
        return

    for hour in PEAK_HOURS:
        schedule.every().day.at(hour).do(run_pipeline)
        logger.info(f"⏰ Scheduled daily automatic Short generation at {hour}")

    logger.info("🚀 Scheduler is active and waiting for next scheduled posting hour. Press Ctrl+C to exit.")
    while True:
        try:
            schedule.run_pending()
            time.sleep(30)
        except KeyboardInterrupt:
            logger.info("🛑 Scheduler stopped by user.")
            break


if __name__ == "__main__":
    main()
