#!/usr/bin/env python3
"""
Lottery Analyzer Script
Analyzes historical lottery results for a given number and calculates statistics
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class LotteryResult:
    """Represents a single lottery result"""
    date: str
    numero: str
    prize_info: str
    has_prize: bool
    prize_amount: float
    ticket_cost: float


class LotteryAnalysis(BaseModel):
    """Lottery analysis results"""
    numero: str
    total_tickets: int
    total_spent: float
    total_won: float
    net_profit: float
    win_rate: float
    biggest_prize: float
    last_win_date: Optional[str] = None
    results: List[LotteryResult] = Field(default_factory=list)


def parse_prize_amount(prize_text: str) -> float:
    """Parse prize amount from text"""
    if not prize_text or "no tiene premio" in prize_text.lower():
        return 0.0
    
    # Look for euro amounts in the text
    import re
    euro_pattern = r'(\d+(?:,\d+)?)\s*€'
    matches = re.findall(euro_pattern, prize_text)
    
    if matches:
        # Take the first (and usually largest) amount
        amount_str = matches[0].replace(',', '.')
        try:
            return float(amount_str)
        except ValueError:
            return 0.0
    
    return 0.0


def get_ticket_cost(date: str) -> float:
    """Get ticket cost for a specific date (Saturday tickets cost 6€)"""
    return 6.0


def fetch_lottery_data_for_date(numero: str, fecha: str) -> Optional[LotteryResult]:
    """Fetch lottery data for a specific date"""
    url = f"https://nacionalloteria.mundodeportivo.com/Loteria-Nacional-Sabado.php?numero={numero}&del-dia={fecha}"
    
    try:
        logger.info(f"Verificando {fecha} para número {numero}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Check if the page indicates no data is available
        # Look for common indicators that the date is too far in the future
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
            # There's a win - extract only the text-premio-det content
            prize_text = " ".join(prize_det_div.get_text().split())
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
        
        return LotteryResult(
            date=fecha,
            numero=numero,
            prize_info=prize_text,
            has_prize=has_prize,
            prize_amount=prize_amount,
            ticket_cost=ticket_cost
        )
        
    except requests.RequestException as e:
        logger.error(f"Error obteniendo datos para {fecha}: {e}")
        return None


def generate_date_range(start_date: str, end_date: str) -> List[str]:
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


def find_earliest_available_data(numero: str, max_lookback_days: int = 365) -> Optional[str]:
    """Find the earliest date with available lottery data"""
    logger.info(f"Buscando la fecha más antigua con datos disponibles para número {numero}")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=max_lookback_days)
    
    # Generate dates in reverse order (newest to oldest)
    dates = []
    current = end_date
    while current >= start_date:
        if current.weekday() == 5:  # Saturday
            dates.append(current.strftime("%Y-%m-%d"))
        current -= timedelta(days=1)
    
    # Test dates until we find one with data
    for date in dates:
        result = fetch_lottery_data_for_date(numero, date)
        if result:
            logger.info(f"Fecha más antigua con datos: {date}")
            return date
        
        # Small delay between requests
        import time
        time.sleep(0.3)
    
    logger.warning(f"No se encontraron datos en los últimos {max_lookback_days} días")
    return None


def fetch_all_available_data(numero: str) -> LotteryAnalysis:
    """Fetch ALL available Saturday results for a given number"""
    logger.info(f"Buscando TODOS los datos disponibles para el número {numero}")
    
    results = []
    current_date = datetime.now()
    consecutive_no_data = 0
    max_consecutive_no_data = 10  # Stop after 10 consecutive dates with no data
    total_spent = 0.0
    total_won = 0.0
    wins = 0
    biggest_prize = 0.0
    last_win_date = None
    
    while consecutive_no_data < max_consecutive_no_data:
        # Get the previous Saturday
        days_since_saturday = (current_date.weekday() - 5) % 7
        if days_since_saturday == 0:
            # Today is Saturday, go back 7 days
            saturday_date = current_date - timedelta(days=7)
        else:
            saturday_date = current_date - timedelta(days=days_since_saturday)
        
        date_str = saturday_date.strftime("%Y-%m-%d")
        logger.info(f"Verificando {date_str}...")
        
        result = fetch_lottery_data_for_date(numero, date_str)
        
        if result:
            consecutive_no_data = 0  # Reset counter when we find data
            results.append(result)
            total_spent += result.ticket_cost
            
            if result.has_prize:
                total_won += result.prize_amount
                wins += 1
                last_win_date = date_str
                biggest_prize = max(biggest_prize, result.prize_amount)
                logger.info(f"🎉 {date_str}: {result.prize_info} (€{result.prize_amount})")
            else:
                logger.info(f"❌ {date_str}: Sin premio")
        else:
            consecutive_no_data += 1
            logger.info(f"📭 {date_str}: Sin datos disponibles ({consecutive_no_data}/{max_consecutive_no_data})")
        
        # Move to the previous Saturday
        current_date = saturday_date
        
        # Add a small delay to be respectful to the server
        import time
        time.sleep(0.5)
    
    logger.info(f"Deteniendo búsqueda después de {consecutive_no_data} sábados consecutivos sin datos")
    
    net_profit = total_won - total_spent
    win_rate = (wins / len(results)) * 100 if results else 0
    
    return LotteryAnalysis(
        numero=numero,
        total_tickets=len(results),
        total_spent=total_spent,
        total_won=total_won,
        net_profit=net_profit,
        win_rate=win_rate,
        biggest_prize=biggest_prize,
        last_win_date=last_win_date,
        results=results
    )


def analyze_lottery_history(numero: str, start_date: str, end_date: str) -> LotteryAnalysis:
    """Analyze lottery history for a given number and date range"""
    logger.info(f"Iniciando análisis para número {numero} desde {start_date} hasta {end_date}")
    
    # Generate all Saturday dates in the range
    saturday_dates = generate_date_range(start_date, end_date)
    logger.info(f"Verificando {len(saturday_dates)} sábados")
    
    results = []
    total_spent = 0.0
    total_won = 0.0
    wins = 0
    biggest_prize = 0.0
    last_win_date = None
    consecutive_no_data = 0
    max_consecutive_no_data = 5  # Stop after 5 consecutive dates with no data
    
    for date in saturday_dates:
        result = fetch_lottery_data_for_date(numero, date)
        
        if result:
            # Reset consecutive no-data counter when we find data
            consecutive_no_data = 0
            results.append(result)
            total_spent += result.ticket_cost
            
            if result.has_prize:
                total_won += result.prize_amount
                wins += 1
                last_win_date = date
                biggest_prize = max(biggest_prize, result.prize_amount)
                logger.info(f"🎉 {date}: {result.prize_info} (€{result.prize_amount})")
            else:
                logger.info(f"❌ {date}: Sin premio")
        else:
            consecutive_no_data += 1
            logger.info(f"📭 {date}: Sin datos disponibles")
            
            # Stop if we've hit too many consecutive dates with no data
            if consecutive_no_data >= max_consecutive_no_data:
                logger.info(f"Deteniendo análisis después de {consecutive_no_data} fechas consecutivas sin datos")
                break
        
        # Add a small delay to be respectful to the server
        import time
        time.sleep(0.5)
    
    net_profit = total_won - total_spent
    win_rate = (wins / len(results)) * 100 if results else 0
    
    return LotteryAnalysis(
        numero=numero,
        total_tickets=len(results),
        total_spent=total_spent,
        total_won=total_won,
        net_profit=net_profit,
        win_rate=win_rate,
        biggest_prize=biggest_prize,
        last_win_date=last_win_date,
        results=results
    )


def create_analysis_report(analysis: LotteryAnalysis) -> str:
    """Create a formatted analysis report"""
    report = f"""
🎰 **ANÁLISIS DE LOTERÍA NACIONAL**

**Número analizado:** {analysis.numero}
**Período:** {analysis.results[0].date if analysis.results else 'N/A'} - {analysis.results[-1].date if analysis.results else 'N/A'}

📊 **ESTADÍSTICAS GENERALES**
• Total de boletos: {analysis.total_tickets}
• Tasa de acierto: {analysis.win_rate:.1f}%
• Mayor premio: €{analysis.biggest_prize:.2f}
• Última victoria: {analysis.last_win_date or 'Nunca'}

💰 **ANÁLISIS ECONÓMICO**
• Total gastado: €{analysis.total_spent:.2f}
• Total ganado: €{analysis.total_won:.2f}
• Beneficio neto: €{analysis.net_profit:.2f}
• ROI: {(analysis.net_profit / analysis.total_spent * 100) if analysis.total_spent > 0 else 0:.1f}%

🎯 **RESULTADOS DETALLADOS**
"""
    
    for result in analysis.results[-10:]:  # Show last 10 results
        status = "🎉" if result.has_prize else "❌"
        report += f"{status} {result.date}: {result.prize_info}\n"
    
    if len(analysis.results) > 10:
        report += f"\n... y {len(analysis.results) - 10} resultados más\n"
    
    return report


def save_analysis_to_file(analysis: LotteryAnalysis, filename: str = None):
    """Save analysis results to a JSON file"""
    if not filename:
        filename = f"lottery_analysis_{analysis.numero}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    # Convert LotteryResult objects to dictionaries
    results_dict = []
    for result in analysis.results:
        results_dict.append({
            "date": result.date,
            "numero": result.numero,
            "prize_info": result.prize_info,
            "has_prize": result.has_prize,
            "prize_amount": result.prize_amount,
            "ticket_cost": result.ticket_cost
        })
    
    analysis_dict = analysis.model_dump()
    analysis_dict["results"] = results_dict
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(analysis_dict, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Análisis guardado en: {filename}")


def main():
    """Main function to run the lottery analyzer"""
    logger.info("Iniciando analizador de lotería...")
    
    # Get environment variables
    numero = os.getenv("LOTTERY_NUMBER")
    
    if not numero:
        logger.error("Variable de entorno LOTTERY_NUMBER no configurada")
        return False
    
    # Get date range from environment variables
    start_date = os.getenv("ANALYSIS_START_DATE")
    end_date = os.getenv("ANALYSIS_END_DATE")
    
    # If no dates provided, fetch ALL available data
    if not start_date and not end_date:
        logger.info("No se proporcionaron fechas, buscando TODOS los datos disponibles...")
        analysis = fetch_all_available_data(numero)
    else:
        # Use provided dates or defaults
        if not start_date:
            logger.info("No se proporcionó fecha de inicio, buscando datos más antiguos disponibles...")
            earliest_date = find_earliest_available_data(numero)
            if earliest_date:
                start_date = earliest_date
            else:
                # Fallback to last 6 months
                start_date = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
                logger.info(f"Usando fecha de inicio por defecto: {start_date}")
        
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")
        
        logger.info(f"Analizando número {numero} desde {start_date} hasta {end_date}")
        analysis = analyze_lottery_history(numero, start_date, end_date)
    
    # Create and display report
    report = create_analysis_report(analysis)
    print(report)
    
    # Save to file
    save_analysis_to_file(analysis)
    
    logger.info("Análisis completado exitosamente")
    return True


if __name__ == "__main__":
    main() 