from scripts.auto import ExchangeRateAnalytics
from scripts.wise import wise_scraping
from scripts.wu import wu_scraping
from prefect import task, flow
import subprocess

# wise_df = wise_scraping()
# wu_df = wu_scraping()

@task(log_prints=True)
def run_multiple_commands():
    commands = [
        "su - root",  
        "sudo --version"
    ]
    try:
        for command in commands:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print(f"Command: {command}\nOutput:\n{result.stdout}")

    except subprocess.CalledProcessError as e:
        print(f"Error: {e}")

@flow(log_prints=True)
def run_exchange_rate_analytics():
    run_multiple_commands()
    test = ExchangeRateAnalytics(
        wise_df=wise_df,
        wu_df=wu_df,
        corridor_dir='input/sending_receiving_country_pair.xlsx',
        output_dir='output.xlsx'
    )
    test.run()

run_exchange_rate_analytics()

    