from scripts.auto import ExchangeRateAnalytics
from scripts.wise import wise_scraping
from scripts.wu import wu_scraping

# @flow(log_prints=True)
# def run_exchange_rate_analytics():
#     test = ExchangeRateAnalytics(
#         wise_dir='sample/wise.csv',
#         wu_dir='sample/wu_new.csv',
#         corridor_dir='input/sending_receiving_country_pair.xlsx',
#         output_dir='output.xlsx'
#     )
#     test.run()

# wise_scraping()
wu_scraping()
    