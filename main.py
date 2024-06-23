from scripts.auto import ExchangeRateAnalytics
from scripts.wise import wise_scraping
from scripts.wu import wu_scraping
from prefect import task, flow
import subprocess

@task(log_prints=True)
def run_multiple_commands():
    commands = ["cat /etc/*-release"]
    try:
        for command in commands:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"Command: {command}\nOutput:\n{result.stdout}")

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

@flow(log_prints=True)
def run_exchange_rate_analytics():
    run_multiple_commands()

    driver_path = 'chrome/chromedriver'
    chrome_path = 'chrome/chrome/google-chrome'
    
    wise_df = wise_scraping(driver_path, chrome_path)
    wu_df = wu_scraping(driver_path, chrome_path)
    
    test = ExchangeRateAnalytics(
        wise_df=wise_df,
        wu_df=wu_df,
        corridor_dir='input/sending_receiving_country_pair.xlsx',
        output_dir='output.xlsx',
        screenshot_dir='screenshots',
        screenshot_zip='screenshots.zip'
    )
    test.run()

run_exchange_rate_analytics()

    