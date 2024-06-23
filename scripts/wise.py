import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import pandas as pd
from datetime import datetime
import pycountry
import concurrent.futures
import os


def wise_scraping():
    print('------------------------------------')
    print('Part 1/3: Scraping data from Wise...')
    print('------------------------------------')

    start_time = time.time()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Path to the web driver (adjust if necessary)
    driver_path = 'chrome/chromedriver'
    chrome_path = 'chrome/chrome/google-chrome'
    url = 'https://wise.com/sg/send-money/'

    sendingandreceivingdf = read_sending_receiving_country_pair_excel()

    list_of_tuples = list(
        sendingandreceivingdf[['Sending country', 'Receiving country']].itertuples(index=False, name=None))
    # print(list_of_tuples)

    # Extract and print all possible values under the 'you send exactly'
    driver = initialize_chrome_driver(chrome_path, driver_path)
    driver.get(url)
    webpage = WebpageInteractions(driver)
    you_send_exactly_options = webpage.get_all_options(0)
    you_send_exactly_options = list(
        filter(lambda x: x in sendingandreceivingdf['Sending country'].values, you_send_exactly_options))
    driver.quit()

    # print(you_send_exactly_options)

    # Split the you_send_exactly_options into 5 parts
    options_split = [you_send_exactly_options[i::5] for i in range(5)]

    # Initialize a DataFrame to collect results from all workers
    df = pd.DataFrame()

    # Worker function to be executed in parallel
    def worker(options_subset):
        worker_df = pd.DataFrame()


        driver = initialize_chrome_driver(chrome_path, driver_path)
        driver.get(url)
        webpage = WebpageInteractions(driver)

        for optiontoclick in options_subset:
            webpage.click_option(optiontoclick, 0)

            try:
                recipient_options = webpage.get_all_options(1)
                recipient_options = [element for element in recipient_options if (optiontoclick, element) in list_of_tuples]
                print(f'Processing {optiontoclick} with available options: {recipient_options}...')

                for recipientoption in recipient_options:

                    # if both you send exactly and recipient are the same country skip and continue the program
                    if (recipientoption == optiontoclick):
                        break

                    webpage.click_option(recipientoption, 1)
                    values = ProcessScrapedOutput.check_if_value_present_in_country_pair_excel(optiontoclick, recipientoption,
                                                                                              sendingandreceivingdf)
                    if not values.empty:
                        ticket_size_columns = [col for col in values.index if 'ticket size' in col]

                        for col in ticket_size_columns:
                            ticket_size = values[col]
                            worker_df = process_currency(ticket_size, timestamp, webpage, worker_df)
                            # webpage.take_screenshot(optiontoclick, recipientoption)
                    else:
                        ticket_size = 1000
                        worker_df = process_currency(ticket_size, timestamp, webpage, worker_df)
                        # webpage.take_screenshot(optiontoclick, recipientoption)

            except IndexError as e:
                ticket_size = 1000
                worker_df = process_currency(ticket_size, timestamp, webpage, worker_df)
                # webpage.take_screenshot(optiontoclick, "nil")
                continue

        driver.quit()
        return worker_df

    # Execute the worker function in parallel using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(worker, options) for options in options_split]
        for future in concurrent.futures.as_completed(futures):
            df = pd.concat([df, future.result()])

    # QUAN INSERT CODE HERE

    # write_to_excel(df, timestamp)
    end_time = time.time()
    time_taken = end_time - start_time
    print(f"Time taken to run program: {round(time_taken, 2)} seconds")

    print("Size of output dataframe:", df.shape)
    print(df.head())

    df.to_csv('sample/wise_new.csv')
    print("Write to sample CSV successfully")

    return df


def scrape_text(driver):
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    container = soup.find('div', class_='preset--light')
    if container:
        return container.get_text(separator='\n', strip=True)
    return ""

def initialize_chrome_driver(chrome_path, driver_path):
    # Set up Chrome options
    options = Options()
    options.binary_location = chrome_path
    options.add_argument('--no-sandbox')
    options.add_argument('--headless')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")

    # Set up ChromeDriver service
    service = Service(executable_path=driver_path)

    # Initialize the web driver
    driver = webdriver.Chrome(service=service, options=options)
    return driver

    #read the excel and convert it to a dataframe with the abbreviations of the country names

def read_sending_receiving_country_pair_excel():
    # Load the Excel file
    file_path = 'input/sending_receiving_country_pair.xlsx'  # replace with the actual file path
    sheet_name = 'Sheet1'  # replace with the actual sheet name if different

    # Read the specified columns
    df = pd.read_excel(file_path, sheet_name=sheet_name,
                       usecols=['Sending country', 'Receiving country', 'ticket size 1', 'ticket size 2',
                                'ticket size 3'])

    df['Sending country'] = df['Sending country'].apply(ProcessScrapedOutput.get_country_abbr)
    df['Receiving country'] = df['Receiving country'].apply(ProcessScrapedOutput.get_country_abbr)
    return df


def write_to_excel(df, timestamp):
    excel_writer = pd.ExcelWriter('output.xlsx', engine='xlsxwriter')

    # Create a new DataFrame with the timestamp
    timestamp_df = pd.DataFrame({
        'Title': ['Timestamp'],
        'Value': [timestamp]
    }, index=[len(df)])

    # Append the timestamp row to the original DataFrame
    df = pd.concat([df, timestamp_df])

    # Write the DataFrame to an Excel sheet
    df.to_excel(excel_writer, sheet_name='Sheet1', index=False)

    # Save the Excel file
    excel_writer.close()

    print("DataFrame has been successfully saved to 'output.xlsx'")

def process_currency(ticket_size,timestamp,webpage,df):
    webpage.change_ticket_size(ticket_size)
    data = ProcessScrapedOutput.clean_text(scrape_text(webpage.driver))

    # process the dataframe as pairs and convert to df
    raw_result = ProcessScrapedOutput.convert_text_to_df(data, ticket_size, timestamp)
    result = ProcessScrapedOutput.reformat_to_quan_desired_dataframe(raw_result)
    df = pd.concat([df, result], ignore_index=True)

    return df

class WebpageInteractions:
    def __init__(self, driver):
        self.driver = driver

    #click either you send exactly box choice 0, or recipient get box choice 1
    def click_option(self, optiontoclick, whichdropdown):
        #time.sleep(1)
        #open dropdown
        self.open_dropdown(whichdropdown)
        # Locate the correct option to click by its text
        option = self.driver.find_element(By.XPATH,
                                          f"//div[@class='np-select-input-option-content-text-line-1']//h4[contains(text(),'{optiontoclick}')]")

        # Scroll to the SGD option and click it
        self.driver.execute_script("arguments[0].scrollIntoView(true);", option)
        self.driver.execute_script("arguments[0].click();", option)

    #open the first or second dropdown
    def open_dropdown(self, thefirstorsecond):
        button_class = f".form-control np-form-control np-form-control--size-lg np-button-input".replace(' ', '.')
        dropdown = self.driver.find_elements(By.CSS_SELECTOR, button_class)
        self.driver.execute_script("arguments[0].click();", dropdown[thefirstorsecond])

    #wait for the page to load finish
    def wait_for_page_to_load_finish(self):
        WebDriverWait(self.driver, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, f".{'preset--light'}")))

    #get all options from dropdown
    def get_all_options(self, whichdropdown):
        # Wait for the currency dropdown/button to be clickable and click it
        self.open_dropdown(whichdropdown)

        # Find the opened listbox section (assuming it's the one with a specific attribute or class indicating it's active)
        wait = WebDriverWait(self.driver, 10)
        dropdown = wait.until(EC.visibility_of_element_located((By.CLASS_NAME, 'np-select-input-listbox')))

        opened_listbox = dropdown.find_element(By.XPATH, "//div[contains(@class, 'np-select-input-listbox')]")

        # Find all option containers within the opened listbox
        options = opened_listbox.find_elements(By.CLASS_NAME, 'np-select-input-option-content-text-primary')

        # Filter options: remove strings with length more than 3 or blank strings
        filtered_options = [option.text for option in options if len(option.text) <= 3 and option.text != '']
        filtered_options = sorted(list(set(filtered_options)))
        # close dropdown
        self.open_dropdown(whichdropdown)

        return filtered_options

    #change the ticket size in the webpage
    def change_ticket_size(self, ticketsize):
        # Find the element by its ID
        element = self.driver.find_element(By.ID, "tw-calculator-source")

        # # Change the value of the element
        # driver.execute_script(f"arguments[0].value = '{ticketsize}';", element)
        #
        # # Trigger an input event to ensure any listeners are triggered
        # driver.execute_script("arguments[0].dispatchEvent(new Event('input'));", element)

        # Clear the existing value
        self.driver.execute_script(f"arguments[0].value = '';", element)

        # Simulate typing the new value
        for char in str(ticketsize):
            element.send_keys(char)
            time.sleep(0.1)  # small delay to simulate natural typing speed

        # Essential sleep to ensure the value change is processed
        time.sleep(1)

    def take_screenshot(self,optiontoclick, recipientoption):
        # Scroll down the page so that the white box is in view
        self.driver.execute_script("window.scrollTo(0, 500);")

        # Create the screenshots directory if it does not exist
        screenshots_dir = 'screenshots'
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)

        # takes screenshot and stores it in the screen shot folder
        screenshot_path = f'screenshots/{optiontoclick}_to_{recipientoption}.png'

        #take the screenshot
        self.driver.save_screenshot(screenshot_path)


#methods to process the scraped output, as it will not be in a perfect table form when first scraped
class ProcessScrapedOutput:

    # Function to filter the extracted text with a predefined list of what to remove
    @staticmethod
    def clean_text(text):

        lines = text.strip().split('\n')

        # Define a set of text to filter e.g. arithmetic operators, buttons
        filters = {'+', '-', '*', '/', '=', 'x', '–', '×', '÷', 'Compare price', 'Get started'}

        # Use list comprehension to filter out arithmetic operators
        filtered_data = [item for item in lines if item not in filters]

        return filtered_data

    # merges everything between the title, so that we can make it into pairs
    # ['You send exactly', 'SGD', '0 SGD', 'Bank transfer fee']
    # will become ['You send exactly', 'SGD 0 SGD', 'Bank transfer fee']
    # NOTE: accepts a list of strings not just a string.
    @staticmethod
    def create_pairs(text):
        titles = [
            'You send exactly', 'Bank transfer fee', 'Our fee', 'Total fees',
            'Total amount we’ll convert', 'Guaranteed rate', 'Exchange rate', 'Recipient gets approximately',
            'Recipient gets',
            'You could save up to', 'Should arrive'
        ]
        # Initialize an empty dictionary to store the result
        result = {}

        # Initialize an empty list to collect additional information that doesn't match the titles
        additional_info = []

        # Initialize a counter to iterate over the text list
        i = 0

        # Loop through the text list
        while i < len(text):
            # Check if the current text element is a title
            if text[i] in titles:
                # If it's a title, store it as the key
                key = text[i]
                # Move to the next element in the list (which should be the value)
                i += 1
                # Check if we haven't reached the end of the list and the next element is not a title
                if i < len(text) and text[i] not in titles:
                    # If the next element is a value, add the key-value pair to the result dictionary
                    result[key] = text[i]
                    # Move to the next element in the list
                    i += 1
                else:
                    # If the next element is a title or we are at the end of the list, set the value as an empty string
                    result[key] = ""
            else:
                # If the current element is not a title, it is considered additional information
                additional_info.append(text[i])
                # Move to the next element in the list
                i += 1

        # After the loop, check if there's any additional information collected
        if additional_info:
            # If there is, add it to the result dictionary under the key 'Additional Information'
            result['Additional Information'] = additional_info

        # return the final result dictionary
        # Convert the dictionary to a DataFrame
        resultdf = pd.DataFrame(list(result.items()), columns=['Title', 'Value'])

        return resultdf

    # add to lines of space between each DF and add the ticket size and company name into df
    @staticmethod
    def convert_text_to_df(filtered_data, ticketsize, timestamp):
        pairs = ProcessScrapedOutput.create_pairs(filtered_data)

        # add ticket size
        new_row = {'Title': 'ticket_size', 'Value': ticketsize}

        pairs.loc[len(pairs)] = new_row

        # add company_name
        new_row = {'Title': 'company_name', 'Value': 'Wise'}

        pairs.loc[len(pairs)] = new_row

        # add ticket size
        new_row = {'Title': 'timestamp', 'Value': timestamp}

        pairs.loc[len(pairs)] = new_row

        # for now set to 1
        # new_row = {'Title': 'binary_is_send_currency_applicable_to_transfer', 'Value': '1'}

        # pairs.loc[len(pairs)] = new_row

        # Add two empty rows to represent Excel spacing
        new_row = {'Title': '', 'Value': ''}
        pairs.loc[len(pairs)] = new_row
        pairs.loc[len(pairs)] = new_row

        # this will be the original raw output. if you want to get the base data you can do so here
        return pd.DataFrame(pairs)



    #convert each country name to abbreviations in read_sending_receiving_country_pair excel sheet
    @staticmethod
    def get_country_abbr(country_name):
        # Custom mapping for specific cases
        custom_currency_mapping = {
            "United Kingdom": "GBP",
            "Hong Kong SAR, China": "HKD",
            "Korea, Rep.": "KOR",
            "Vietnam": "VTM",
            "Japan": "JPN"
            # NOTE: Add other custom mappings if needed
        }
        # Check in custom mapping first
        if country_name in custom_currency_mapping:
            return custom_currency_mapping[country_name]

        # Otherwise, try to find using pycountry
        country = pycountry.countries.get(name=country_name)
        if not country:
            return None

        # Attempt to get currency using country alpha_2 code
        currency = pycountry.currencies.get(numeric=country.numeric)
        return currency.alpha_3 if currency else None

    #check if value is present in the country pair excel, so that I can make it change the ticket size to what is required
    @staticmethod
    def check_if_value_present_in_country_pair_excel(optiontoclick, recipient_option, sendingandreceivingdf):
        for index, row in sendingandreceivingdf.iterrows():
            if row['Sending country'] == optiontoclick and row['Receiving country'] == recipient_option:
                return row

        return pd.DataFrame()

    # reformat the dataframe to the one desired by quan
    # so that he can use it for his program
    @staticmethod
    def reformat_to_quan_desired_dataframe(df):
        # Assuming df is your initial DataFrame
        df = pd.DataFrame(df).set_index('Title').T

        # Define the columns in the desired order
        desired_columns = ['You send exactly', 'country_receive', 'company_name', 'ticket_size',
                           'timestamp', 'Total amount we’ll convert', 'Our fee']

        # Check if the columns exist and create the new column 'country_receive'
        if 'Recipient gets' in df.columns:
            df['country_receive'] = df['Recipient gets']
        elif 'Recipient gets approximately' in df.columns:
            df['country_receive'] = df['Recipient gets approximately']

        # Reorder the DataFrame
        df = df[desired_columns]

        # Define new column names
        new_column_names = {
            "You send exactly": "country_send",
            "company_name": "company_name",
            "ticket_size": "ticket_size",
            "Total amount we’ll convert": "fx_rate_3",
            "timestamp": "timestamp",
            "Our fee": "service_fee"
        }

        # Rename the columns
        df_renamed = df.rename(columns=new_column_names)

        # Print the resulting DataFrame
        return df_renamed


if __name__ == '__main__':
    df = main()