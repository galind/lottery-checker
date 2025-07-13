#!/usr/bin/env python3
"""
Lottery Notifier Script
Fetches lottery results from Mundo Deportivo and sends to Discord webhook
"""

import json
import logging
import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_saturday_date():
    """Get the current Saturday's date in YYYY-MM-DD format"""
    today = datetime.now()
    # Calculate days until next Saturday (5 = Saturday)
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0:
        # Today is Saturday
        saturday_date = today
    else:
        # Get next Saturday
        saturday_date = today + timedelta(days=days_until_saturday)

    return saturday_date.strftime("%Y-%m-%d")


def fetch_lottery_data(numero, fecha):
    """Fetch lottery data from Mundo Deportivo"""
    url = f"https://nacionalloteria.mundodeportivo.com/Loteria-Nacional-Sabado.php?numero={numero}&del-dia={fecha}"

    try:
        logger.info(f"Fetching lottery data from: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract lottery information
        # Note: The actual selectors may need adjustment based on the website structure
        lottery_info = {
            "numero": numero,
            "fecha": fecha,
            "url": url,
            "raw_content": response.text[:500] + "..." if len(response.text) > 500 else response.text,
        }

        # Try to extract specific lottery results
        # This is a placeholder - you may need to adjust based on actual website structure
        title_elem = soup.find("title")
        if title_elem:
            lottery_info["title"] = title_elem.get_text().strip()

        # Look for lottery result elements
        result_elements = soup.find_all(
            ["div", "span", "p"],
            class_=lambda x: x and any(word in x.lower() for word in ["resultado", "premio", "numero", "loteria"]),
        )
        if result_elements:
            lottery_info["results"] = [elem.get_text().strip() for elem in result_elements[:5]]

        return lottery_info

    except requests.RequestException as e:
        logger.error(f"Error fetching lottery data: {e}")
        return None


def send_discord_message(webhook_url, lottery_data):
    """Send lottery data to Discord webhook"""
    if not lottery_data:
        message = {
            "content": "❌ Error: Could not fetch lottery data",
            "embeds": [
                {
                    "title": "Lottery Check Failed",
                    "description": "Failed to fetch lottery data from Mundo Deportivo",
                    "color": 0xFF0000,
                    "timestamp": datetime.now().isoformat(),
                }
            ],
        }
    else:
        # Create a formatted message
        embed = {
            "title": f"🎰 Lottery Results - {lottery_data['fecha']}",
            "description": f"Checking lottery number: **{lottery_data['numero']}**",
            "color": 0x00FF00,
            "fields": [],
            "timestamp": datetime.now().isoformat(),
            "url": lottery_data["url"],
        }

        if "title" in lottery_data:
            embed["fields"].append({"name": "Page Title", "value": lottery_data["title"], "inline": False})

        if "results" in lottery_data and lottery_data["results"]:
            embed["fields"].append(
                {"name": "Results Found", "value": "\n".join(lottery_data["results"][:3]), "inline": False}
            )

        message = {"embeds": [embed]}

    try:
        logger.info("Sending message to Discord webhook")
        response = requests.post(webhook_url, json=message, timeout=30)
        response.raise_for_status()
        logger.info("Message sent successfully to Discord")
        return True
    except requests.RequestException as e:
        logger.error(f"Error sending Discord message: {e}")
        return False


def main():
    """Main function to run the lottery checker"""
    logger.info("Starting lottery checker...")

    # Get environment variables
    numero = os.getenv("LOTTERY_NUMBER")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not numero:
        logger.error("LOTTERY_NUMBER environment variable not set")
        return False

    if not webhook_url:
        logger.error("DISCORD_WEBHOOK_URL environment variable not set")
        return False

    # Get Saturday's date
    saturday_date = get_saturday_date()
    logger.info(f"Checking lottery for Saturday: {saturday_date}")

    # Fetch lottery data
    lottery_data = fetch_lottery_data(numero, saturday_date)

    # Send to Discord
    success = send_discord_message(webhook_url, lottery_data)

    if success:
        logger.info("Lottery check completed successfully")
    else:
        logger.error("Lottery check failed")

    return success


if __name__ == "__main__":
    main()
