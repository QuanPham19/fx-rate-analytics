# fx-rate-analytics

This project aims to scrape FX rate data from multiple payment websites. The automation process provide users with real-time report Excel file and screenshots Zip file.

## 1. Clone repository
```
git clone https://github.com/QuanPham19/fx-rate-analytics.git
```

## 2. Chrome installation (OS-based)
```
https://googlechromelabs.github.io/chrome-for-testing/
```

## 3. Requirement packages
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. Prefect interaction
```
prefect cloud login
prefect deploy main.py:run_exchange_rate_analytics
```

## 5. Run the workflow
```
python main.py
```
