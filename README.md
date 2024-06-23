# fx-rate-analytics

This project aims to scrape FX rate data from multiple payment websites. The automation process provide users with real-time report Excel file and screenshots Zip file.

## Clone repository
```
git clone https://github.com/QuanPham19/fx-rate-analytics.git
```

## Chrome installation (OS-based)
```
https://googlechromelabs.github.io/chrome-for-testing/
```

## Requirement packages
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Prefect interaction
```
prefect cloud login
prefect deploy main.py:run_exchange_rate_analytics
```

## Run the workflow
```
python main.py
```
