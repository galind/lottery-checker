#!/usr/bin/env python3
"""
Lottery Utils
Shared utilities for lottery data fetching and parsing
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def get_saturday_date():
    """Get the last Saturday's date in YYYY-MM-DD format"""
    today = datetime.now()

    # Calculate days since last Saturday (5 = Saturday)
    days_since_saturday = (today.weekday() - 5) % 7

    # If today is Saturday, use today; otherwise, go back to last Saturday
    if days_since_saturday == 0:
        saturday_date = today
    else:
        saturday_date = today - timedelta(days=days_since_saturday)

    return saturday_date.strftime("%Y-%m-%d")


def parse_prize_amount(prize_text: str) -> float:
    """Parse prize amount from text"""
    if not prize_text or "no tiene premio" in prize_text.lower():
        return 0.0

    # Look for euro amounts in the text
    euro_pattern = r"(\d+(?:,\d+)?)\s*€"
    matches = re.findall(euro_pattern, prize_text)

    if matches:
        # Convert all matches to floats
        amounts = []
        for match in matches:
            amount_str = match.replace(",", ".")
            try:
                amounts.append(float(amount_str))
            except ValueError:
                continue

        if amounts:
            # Return the largest amount (main prize)
            return max(amounts)

    return 0.0


def get_ticket_cost(date: str) -> float:
    """Get ticket cost for a specific date (Saturday tickets cost 6€)"""
    return 6.0


def fetch_lottery_data(numero: str, fecha: str) -> Optional[dict]:
    """Fetch lottery data from Mundo Deportivo"""
    url = f"https://nacionalloteria.mundodeportivo.com/Loteria-Nacional-Sabado.php?numero={numero}&del-dia={fecha}"

    try:
        logger.info(f"Obteniendo datos de lotería desde: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Check if the page indicates no data is available
        page_title = soup.find("title")
        if page_title:
            title_text = page_title.get_text().lower()
            if any(keyword in title_text for keyword in ["error", "no encontrado", "no disponible", "404"]):
                logger.info(f"No hay datos disponibles para {fecha}")
                return None

        # Extract prize information from the text-premio span
        prize_span = soup.find("span", class_="text-premio")
        if not prize_span:
            # If no prize span is found, the date might not have data
            logger.info(f"No se encontró información de premio para {fecha}")
            return None

        # Check if there's a text-premio-det div (indicating a win)
        prize_det_div = prize_span.find("div", class_="text-premio-det")
        if prize_det_div:
            # There's a win - extract the FULL text-premio span content (not just the div)
            for br_tag in prize_span.find_all("br"):
                br_tag.replace_with(" ")
            prize_text = prize_span.get_text().strip()
        else:
            # No win - extract the full text-premio span content
            for br_tag in prize_span.find_all("br"):
                br_tag.replace_with(" ")
            prize_text = prize_span.get_text().strip()

        # Additional check: if the text is empty or very short, might be no data
        if not prize_text or len(prize_text.strip()) < 5:
            logger.info(f"Texto de premio vacío para {fecha}")
            return None

        has_prize = "no tiene premio" not in prize_text.lower()
        prize_amount = parse_prize_amount(prize_text)
        ticket_cost = get_ticket_cost(fecha)

        if has_prize:
            logger.info(f"Información de premio encontrada: {prize_text}")

        return {
            "numero": numero,
            "fecha": fecha,
            "url": url,
            "prize_info": prize_text,
            "has_prize": has_prize,
            "prize_amount": prize_amount,
            "ticket_cost": ticket_cost,
        }

    except requests.RequestException as e:
        logger.error(f"Error obteniendo datos de lotería: {e}")
        return None


def generate_date_range(start_date: str, end_date: str) -> list[str]:
    """Generate list of Saturday dates between start and end"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")

    dates = []
    current = start

    while current <= end:
        # Only include Saturdays
        if current.weekday() == 5:  # Saturday
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def get_previous_saturday(date: datetime) -> datetime:
    """Get the previous Saturday from a given date"""
    days_since_saturday = (date.weekday() - 5) % 7
    if days_since_saturday == 0:
        # Today is Saturday, go back 7 days
        return date - timedelta(days=7)
    else:
        return date - timedelta(days=days_since_saturday) 