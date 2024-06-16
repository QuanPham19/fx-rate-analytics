import os
import pandas as pd
import numpy as np
from countryinfo import CountryInfo
from prefect import task, flow
from prefect_email import EmailServerCredentials, email_send_message

class ExchangeRateAnalytics:
    def __init__(self, wise_dir, wu_dir, corridor_dir, output_dir):
        self.wise_dir = wise_dir
        self.wu_dir = wu_dir
        self.corridor_dir = corridor_dir
        self.output_dir = output_dir

    def country_name_to_currency(self, name):
        country = CountryInfo(name)
        currency = country.currencies()[0]
        return currency
    
    def get_corridor_data(self, input_dir):
        df = pd.read_excel(input_dir)
        print('Retrieving corridor data...')

        df = df.melt(
            id_vars=['Sending country', 'Receiving country'], 
            var_name='ticket_type', 
            value_vars=['ticket size 1', 'ticket size 2', 'ticket size 3'], 
            value_name='ticket_size'
            )
        
        df['Sending country'] = df['Sending country'].apply(self.country_name_to_currency)
        df['Receiving country'] = df['Receiving country'].apply(self.country_name_to_currency)
        df.sort_values(by=['Receiving country', 'Sending country', 'ticket_size'], inplace=True)

        return df
    
    def get_fx_data(self, input_dir, country_receive):
        df = pd.read_csv(input_dir)
        df = df[df['country_receive']==country_receive]

        print(f'Processing data of {country_receive}...')

        df['ticket_size'] = df['ticket_size'].astype(int)
        df[['fx_rate_3', 'service_fee']] = df[['fx_rate_3', 'service_fee']].astype(float)
        df['amount_receive'] = round( (df['ticket_size'] - df['service_fee']) * df['fx_rate_3'], 2)

        df.sort_values(by=['country_receive', 'country_send'], inplace=True)
        return df
    
    def bps_comparison(self, df_target, df_compare):
        df_target['bps'] = 0
        df_compare['bps'] = 10000 * (df_target['fx_rate_3'].values / df_compare['fx_rate_3'].values - 1)
        df_compare['bps'] = df_compare['bps'].apply(round)

    def get_unit_df(self, df_list, country_send, ticket_size):
        concat_list = list()
        for df in df_list:
            df_filter = df[(df['country_send']==country_send) & (df['ticket_size']==ticket_size)]
            concat_list.append(df_filter.set_index('company_name').T)
        
        out = pd.concat(concat_list, axis=1)
        return out
    
    def excel_writer(self, df_list, country_receive, writer):
        corridor = self.get_corridor_data(self.corridor_dir)
        corridor = corridor[corridor['Receiving country'] == country_receive][['Sending country', 'ticket_size']]
        print(f'Writing to sheet name {country_receive}...')

        pivot = list(corridor.itertuples(index=False, name=None))
        print('List of sending country and ticket size...')
        print(pivot)
        
        startrow, startcol = 0, 0
        curr_send_country = None

        for element in pivot:
            if curr_send_country and curr_send_country != element[0]:
                startrow += curr_df.shape[0] + 2
                startcol = 0
                
            curr_send_country = element[0]
            curr_df = self.get_unit_df(df_list, element[0], element[1])
            curr_df.to_excel(writer, sheet_name=country_receive, startrow=startrow, startcol=startcol, index=True)
            startcol += (3 + 2) 

    def run(self):
        print('Current Directory:', os.getcwd())
        print('Currrent Excel directory:', self.output_dir)
        country_receive_list = self.get_corridor_data(self.corridor_dir)['Receiving country'].unique()
        with pd.ExcelWriter(self.output_dir, engine='openpyxl') as writer:
            for country in country_receive_list:
                df_wise = self.get_fx_data(self.wise_dir, country)
                df_wu = self.get_fx_data(self.wu_dir, country)
                # bps_comparison(df_wise, df_wu)
                self.excel_writer([df_wise, df_wu], country, writer)
                print('Successfully write to Excel')

        credentials = EmailServerCredentials(
            username='aminh6c.pmq@gmail.com',
            password='wqbj lpcj ckoi lahr'
        )
        credentials.save('fx-analytics-block', overwrite=True)
        email_server_credentials = EmailServerCredentials.load('fx-analytics-block')
        for email_address in ['aminh6c.pmq2@gmail.com']:
            subject = email_send_message.with_options(name=f'email {email_address}').submit(
                email_server_credentials=email_server_credentials,
                subject='Example Flow Notification using Gmail',
                msg='This proves email_send_message works!',
                email_to=email_address,
                attachments=['output.xlsx']
            )
        return writer

@flow(log_prints=True)
def run_exchange_rate_analytics():
    test = ExchangeRateAnalytics(
        wise_dir='wise.csv',
        wu_dir='wu_new.csv',
        corridor_dir='sending_receiving_country_pair.xlsx',
        output_dir='output.xlsx'
    )
    out = test.run()
    return out