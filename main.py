from scripts.auto import ExchangeRateAnalytics
from scripts.wise_new import wise_scraping
from scripts.wu_test import wu_scraping

wise_df = wise_scraping()
wu_df = wu_scraping()

# @flow(log_prints=True)
def run_exchange_rate_analytics():
    test = ExchangeRateAnalytics(
        wise_df=wise_df,
        wu_df=wu_df,
        corridor_dir='input/sending_receiving_country_pair.xlsx',
        output_dir='output.xlsx'
    )
    test.run()

run_exchange_rate_analytics()
    