#!/usr/bin/env python3
"""
Lottery Analyzer Script
Analyzes historical lottery results for a given number and calculates statistics
"""

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from collections import defaultdict

import requests
from pydantic import BaseModel, Field

from lottery_utils import (
    fetch_lottery_data,
    generate_date_range,
    get_previous_saturday,
    parse_prize_amount,
    get_ticket_cost,
)


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


def fetch_lottery_data_for_date(numero: str, fecha: str) -> Optional[LotteryResult]:
    """Fetch lottery data for a specific date"""
    data = fetch_lottery_data(numero, fecha)
    if data:
        return LotteryResult(
            date=fecha,
            numero=numero,
            prize_info=data["prize_info"],
            has_prize=data["has_prize"],
            prize_amount=data["prize_amount"],
            ticket_cost=data["ticket_cost"],
        )
    return None


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

    # First, find the earliest available data by checking recent dates
    earliest_date = find_earliest_available_data(numero, max_lookback_days=365)
    if not earliest_date:
        logger.warning("No se encontraron datos disponibles")
        return LotteryAnalysis(
            numero=numero,
            total_tickets=0,
            total_spent=0.0,
            total_won=0.0,
            net_profit=0.0,
            win_rate=0.0,
            biggest_prize=0.0,
            results=[]
        )

    # Generate all Saturday dates from earliest to today
    end_date = datetime.now().strftime("%Y-%m-%d")
    saturday_dates = generate_date_range(earliest_date, end_date)
    logger.info(f"Verificando {len(saturday_dates)} sábados con multithreading")

    results = []
    total_spent = 0.0
    total_won = 0.0
    wins = 0
    biggest_prize = 0.0
    last_win_date = None

    # Use ThreadPoolExecutor for concurrent requests
    max_workers = 5  # Limit concurrent requests to be respectful to the server
    
    def fetch_single_date(date: str) -> Optional[LotteryResult]:
        """Fetch data for a single date"""
        result = fetch_lottery_data_for_date(numero, date)
        if result:
            status = "🎉" if result.has_prize else "❌"
            logger.info(f"{status} {date}: {result.prize_info}")
        else:
            logger.info(f"📭 {date}: Sin datos disponibles")
        return result

    # Fetch all dates concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_date = {executor.submit(fetch_single_date, date): date for date in saturday_dates}
        
        # Collect results as they complete
        for future in as_completed(future_to_date):
            date = future_to_date[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    total_spent += result.ticket_cost

                    if result.has_prize:
                        total_won += result.prize_amount
                        wins += 1
                        last_win_date = date
                        biggest_prize = max(biggest_prize, result.prize_amount)
            except Exception as e:
                logger.error(f"Error procesando {date}: {e}")

    # Sort results by date (oldest first)
    results.sort(key=lambda x: x.date)

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
    logger.info(f"Verificando {len(saturday_dates)} sábados con multithreading")

    results = []
    total_spent = 0.0
    total_won = 0.0
    wins = 0
    biggest_prize = 0.0
    last_win_date = None

    # Use ThreadPoolExecutor for concurrent requests
    max_workers = 5  # Limit concurrent requests to be respectful to the server
    
    def fetch_single_date(date: str) -> Optional[LotteryResult]:
        """Fetch data for a single date"""
        result = fetch_lottery_data_for_date(numero, date)
        if result:
            status = "🎉" if result.has_prize else "❌"
            logger.info(f"{status} {date}: {result.prize_info}")
        else:
            logger.info(f"📭 {date}: Sin datos disponibles")
        return result

    # Fetch all dates concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_date = {executor.submit(fetch_single_date, date): date for date in saturday_dates}
        
        # Collect results as they complete
        for future in as_completed(future_to_date):
            date = future_to_date[future]
            try:
                result = future.result()
                if result:
                    results.append(result)
                    total_spent += result.ticket_cost

                    if result.has_prize:
                        total_won += result.prize_amount
                        wins += 1
                        last_win_date = date
                        biggest_prize = max(biggest_prize, result.prize_amount)
            except Exception as e:
                logger.error(f"Error procesando {date}: {e}")

    # Sort results by date (oldest first)
    results.sort(key=lambda x: x.date)

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
    
    # Get lottery number from command line argument
    import sys
    if len(sys.argv) < 2:
        logger.error("Debe proporcionar un número de lotería")
        logger.error("Uso: python lottery_analyzer.py <numero> [fecha_inicio] [fecha_fin]")
        logger.error("Ejemplo: python lottery_analyzer.py 23765")
        logger.error("Ejemplo: python lottery_analyzer.py 23765 2024-01-01 2024-12-31")
        return False
    
    numero = sys.argv[1]
    logger.info(f"Número de lotería: {numero}")
    
    # Get date range from command line arguments or environment variables
    start_date = None
    end_date = None
    
    if len(sys.argv) >= 3:
        start_date = sys.argv[2]
    if len(sys.argv) >= 4:
        end_date = sys.argv[3]
    
    # Fallback to environment variables if not provided as arguments
    if not start_date:
        start_date = os.getenv("ANALYSIS_START_DATE")
    if not end_date:
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