from scripts.auto import ExchangeRateAnalytics

@flow(log_prints=True)
def run_exchange_rate_analytics():
    test = ExchangeRateAnalytics(
        wise_dir='wise.csv',
        wu_dir='wu_new.csv',
        corridor_dir='sending_receiving_country_pair.xlsx',
        output_dir='output.xlsx'
    )
    test.run()
    