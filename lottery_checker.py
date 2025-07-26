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
from pydantic import BaseModel, Field

from lottery_utils import get_saturday_date, fetch_lottery_data

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
    thumbnail: Optional[dict] = None


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
    results: Optional[List[str]] = None


def fetch_lottery_data_for_checker(numero: str, fecha: str) -> Optional[LotteryData]:
    """Fetch lottery data and convert to LotteryData model for checker"""
    data = fetch_lottery_data(numero, fecha)
    if data:
        return LotteryData(
            numero=data["numero"],
            fecha=data["fecha"],
            url=data["url"],
            prize_info=data["prize_info"]
        )
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

    # Check if there's a prize by looking for "no tiene premio" in the text
    has_prize = lottery_data.prize_info and "no tiene premio" not in lottery_data.prize_info.lower()

    # Set thumbnail based on prize status
    if has_prize:
        embed.thumbnail = {"url": "https://oecorazon.wordpress.com/wp-content/uploads/2015/03/gilito.jpg"}
    else:
        embed.thumbnail = {
            "url": "https://media.istockphoto.com/id/473417884/es/vector/hombre-de-negocios-no-tiene-ning%C3%BAn-dinero.jpg?s=612x612&w=0&k=20&c=6bRxHp14noNfN4JAT-uG5OzlURNl6zSJW5QD4bI6YYc="
        }

    if lottery_data.prize_info:
        embed.fields.append(DiscordField(name="🎉 Información del Premio", value=lottery_data.prize_info))

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
    lottery_data = fetch_lottery_data_for_checker(numero, saturday_date)

    # Send to Discord
    success = send_discord_message(webhook_url, lottery_data)

    if success:
        logger.info("Verificación de lotería completada exitosamente")
    else:
        logger.error("Verificación de lotería falló")

    return success


if __name__ == "__main__":
    main()
