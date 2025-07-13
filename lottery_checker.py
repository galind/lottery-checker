#!/usr/bin/env python3
"""
Lottery Notifier Script
Fetches lottery results from Mundo Deportivo and sends to Discord webhook
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DiscordField(BaseModel):
    """Discord embed field model"""

    name: str
    value: str
    inline: bool = False


class DiscordEmbed(BaseModel):
    """Discord embed model"""

    title: str
    description: Optional[str] = None
    color: int = 0x00FF00
    fields: List[DiscordField] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    url: Optional[str] = None


class DiscordMessage(BaseModel):
    """Discord message model"""

    content: Optional[str] = None
    embeds: List[DiscordEmbed] = Field(default_factory=list)


class LotteryData(BaseModel):
    """Lottery data model"""

    numero: str
    fecha: str
    url: str
    prize_info: Optional[str] = None
    title: Optional[str] = None
    results: Optional[List[str]] = None


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


def fetch_lottery_data(numero: str, fecha: str) -> Optional[LotteryData]:
    """Fetch lottery data from Mundo Deportivo"""
    url = f"https://nacionalloteria.mundodeportivo.com/Loteria-Nacional-Sabado.php?numero={numero}&del-dia={fecha}"

    try:
        logger.info(f"Obteniendo datos de lotería desde: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        # Parse the HTML content
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract lottery information
        lottery_info = {
            "numero": numero,
            "fecha": fecha,
            "url": url,
        }

        # Try to extract specific lottery results
        title_elem = soup.find("title")
        if title_elem:
            lottery_info["title"] = title_elem.get_text().strip()

        # Extract prize information from the specific div
        prize_div = soup.find("div", class_="text-premio-det")
        if prize_div:
            prize_text = prize_div.get_text().strip()
            lottery_info["prize_info"] = prize_text
            logger.info(f"Información de premio encontrada: {prize_text}")

        # Look for lottery result elements as fallback
        result_elements = soup.find_all(
            ["div", "span", "p"],
            class_=lambda x: x and any(word in x.lower() for word in ["resultado", "premio", "numero", "loteria"]),
        )
        if result_elements:
            lottery_info["results"] = [elem.get_text().strip() for elem in result_elements[:5]]

        return LotteryData(**lottery_info)

    except requests.RequestException as e:
        logger.error(f"Error obteniendo datos de lotería: {e}")
        return None


def create_error_message() -> DiscordMessage:
    """Create error message for Discord"""
    return DiscordMessage(
        content="❌ Error: No se pudieron obtener los datos de lotería",
        embeds=[
            DiscordEmbed(
                title="Error al Verificar Lotería",
                description="No se pudieron obtener los datos de lotería desde Mundo Deportivo",
                color=0xFF0000,
            )
        ],
    )


def create_success_message(lottery_data: LotteryData) -> DiscordMessage:
    """Create success message for Discord"""
    embed = DiscordEmbed(
        title=f"🎰 Resultados de Lotería - {lottery_data.fecha}",
        description=f"Verificando número de lotería: **{lottery_data.numero}**",
        color=0x00FF00,
        url=lottery_data.url,
    )

    if lottery_data.prize_info:
        embed.fields.append(DiscordField(name="🎉 Información del Premio", value=lottery_data.prize_info))
    elif lottery_data.title:
        embed.fields.append(DiscordField(name="Título de la Página", value=lottery_data.title))

    if lottery_data.results:
        embed.fields.append(DiscordField(name="Resultados Encontrados", value="\n".join(lottery_data.results[:3])))

    return DiscordMessage(embeds=[embed])


def send_discord_message(webhook_url: str, lottery_data: Optional[LotteryData]) -> bool:
    """Send lottery data to Discord webhook"""
    if not lottery_data:
        message = create_error_message()
    else:
        message = create_success_message(lottery_data)

    try:
        logger.info("Enviando mensaje al webhook de Discord")
        response = requests.post(webhook_url, json=message.model_dump(), timeout=30)
        response.raise_for_status()
        logger.info("Mensaje enviado exitosamente a Discord")
        return True
    except requests.RequestException as e:
        logger.error(f"Error enviando mensaje a Discord: {e}")
        return False


def main():
    """Main function to run the lottery checker"""
    logger.info("Iniciando verificador de lotería...")

    # Get environment variables
    numero = os.getenv("LOTTERY_NUMBER")
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")

    if not numero:
        logger.error("Variable de entorno LOTTERY_NUMBER no configurada")
        return False

    if not webhook_url:
        logger.error("Variable de entorno DISCORD_WEBHOOK_URL no configurada")
        return False

    # Get Saturday's date
    saturday_date = get_saturday_date()
    logger.info(f"Verificando lotería para el sábado: {saturday_date}")

    # Fetch lottery data
    lottery_data = fetch_lottery_data(numero, saturday_date)

    # Send to Discord
    success = send_discord_message(webhook_url, lottery_data)

    if success:
        logger.info("Verificación de lotería completada exitosamente")
    else:
        logger.error("Verificación de lotería falló")

    return success


if __name__ == "__main__":
    main()
