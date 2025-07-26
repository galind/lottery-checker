# Lottery Notifier

A Python script that automatically checks lottery results every Saturday at 17:00 CET and sends notifications to a Discord webhook.

## Features

- 🎰 Fetches lottery data from Mundo Deportivo
- ⏰ Runs automatically every Saturday at 17:00 CET
- 📱 Sends formatted notifications to Discord
- 📊 Analyzes historical lottery data and calculates statistics
- 💰 Tracks money spent, won, and ROI
- 🔧 Configurable via GitHub Secrets
- 🚀 Runs on GitHub Actions

## Setup

### 1. Repository Secrets

You need to configure two secrets in your GitHub repository:

1. **LOTTERY_NUMBER**: Your lottery number to check
2. **DISCORD_WEBHOOK_URL**: Your Discord webhook URL

#### Setting up GitHub Secrets:

1. Go to your repository on GitHub
2. Click on "Settings" tab
3. Click on "Secrets and variables" → "Actions"
4. Click "New repository secret"
5. Add the following secrets:
   - Name: `LOTTERY_NUMBER`, Value: Your lottery number (e.g., "23765")
   - Name: `DISCORD_WEBHOOK_URL`, Value: Your Discord webhook URL

#### Creating a Discord Webhook:

1. Go to your Discord server
2. Right-click on the channel where you want notifications
3. Select "Edit Channel"
4. Go to "Integrations" tab
5. Click "Create Webhook"
6. Copy the webhook URL

### 2. Local Testing

To test the script locally:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set up pre-commit hooks (optional but recommended):
   ```bash
   pre-commit install
   ```

3. Set environment variables:
   ```bash
   export LOTTERY_NUMBER="your_lottery_number"
   export DISCORD_WEBHOOK_URL="your_discord_webhook_url"
   ```

4. Run the script:
   ```bash
   python lottery_checker.py
   ```

## How it Works

1. **Scheduling**: The GitHub Actions workflow runs every Saturday at 17:00 CET
2. **Data Fetching**: The script fetches lottery data from Mundo Deportivo using your lottery number
3. **Date Calculation**: Automatically calculates the current Saturday's date
4. **Discord Notification**: Sends a formatted message to your Discord channel

## File Structure

```
lottery-notifier/
├── .github/workflows/
│   ├── lottery-checker.yml    # GitHub Actions workflow for notifications
│   └── lottery-analyzer.yml   # GitHub Actions workflow for analysis
├── lottery_checker.py         # Main Python script for notifications
├── lottery_analyzer.py        # Lottery analysis script
├── requirements.txt           # Python dependencies
├── README.md                 # This file
└── LICENSE                   # License file
```

## Lottery Analyzer

The project includes a comprehensive lottery analyzer that can check historical results and calculate statistics.

### Features

- **Historical Analysis**: Checks all Saturday results for a given date range
- **Financial Tracking**: Calculates total spent, won, and net profit
- **Statistics**: Win rate, biggest prize, last win date
- **Detailed Reports**: Shows last 10 results with full history saved to JSON

### Usage

#### Local Usage

```bash
# Analyze ALL available data for a number
python lottery_analyzer.py 23765

# With custom date range
python lottery_analyzer.py 23765 2024-01-01 2024-12-31

# Using environment variables for dates
export ANALYSIS_START_DATE="2024-01-01"
export ANALYSIS_END_DATE="2024-12-31"
python lottery_analyzer.py 23765
```

#### GitHub Actions

1. Go to your repository → Actions
2. Select "Lottery Analyzer" workflow
3. Click "Run workflow"
4. Enter your lottery number (required)
5. Optionally set start and end dates
6. Download results from artifacts

**Artifacts uploaded:**
- `lottery-analysis-results`: JSON file containing complete analysis data
  - All lottery results with dates and prize information
  - Financial statistics (total spent, won, net profit)
  - Win rate and other metrics
  - File format: `lottery_analysis_<numero>_<timestamp>.json`

### Sample Report

```
🎰 ANÁLISIS DE LOTERÍA NACIONAL

Número analizado: 23765
Período: 2024-07-01 - 2024-12-31

📊 ESTADÍSTICAS GENERALES
• Total de boletos: 26
• Tasa de acierto: 7.7%
• Mayor premio: €15.00
• Última victoria: 2024-12-14

💰 ANÁLISIS ECONÓMICO
• Total gastado: €156.00
• Total ganado: €30.00
• Beneficio neto: -€126.00
• ROI: -80.8%

🎯 RESULTADOS DETALLADOS
❌ 2024-12-28: El número 23765 no tiene premio
🎉 2024-12-14: Reintegro - Premio de 15 €
❌ 2024-12-07: El número 23765 no tiene premio
...
```

## Development

### Code Formatting

This project uses [Black](https://black.readthedocs.io/) for code formatting and [isort](https://pycqa.github.io/isort/) for import sorting. These are configured as pre-commit hooks.

To format your code:
```bash
# Format with Black
black .

# Sort imports with isort
isort .

# Or run both via pre-commit
pre-commit run --all-files
```

### Pre-commit Hooks

The project includes pre-commit hooks for code quality:
- **Black**: Code formatting
- **isort**: Import sorting

To set up pre-commit hooks:
```bash
pip install -r requirements.txt
pre-commit install
```

## Customization

### Modifying the Schedule

To change when the script runs, edit the cron expression in `.github/workflows/lottery-checker.yml`:

```yaml
- cron: '0 16 * * 6'  # Every Saturday at 16:00 UTC
```

### Adjusting Data Extraction

The script currently extracts basic information from the lottery website. You may need to adjust the HTML parsing logic in `lottery_checker.py` based on the actual structure of the Mundo Deportivo website.

## Troubleshooting

### Common Issues

1. **Script not running**: Check that the GitHub Secrets are properly configured
2. **No Discord messages**: Verify your webhook URL is correct and the channel has proper permissions
3. **Data extraction issues**: The website structure may have changed; you might need to update the parsing logic

### Manual Trigger

You can manually trigger the workflow:
1. Go to your repository on GitHub
2. Click on "Actions" tab
3. Select "Lottery Checker" workflow
4. Click "Run workflow"

## License

This project is licensed under the MIT License - see the LICENSE file for details. 