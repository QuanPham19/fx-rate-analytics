import os
from os import path
import re
import time
from time import localtime, strftime
import pandas as pd
import requests
from bs4 import BeautifulSoup
import pycountry
from fuzzywuzzy import process
from fuzzywuzzy import fuzz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from concurrent.futures import ThreadPoolExecutor, as_completed

def wu_scraping():
    print('---------------------------------------------')
    print('Part 2/3: Scraping data from Western Union...')
    print('---------------------------------------------')    

    start_time = time.time()
    df = pd.read_excel('input/sending_receiving_country_pair.xlsx', 'Corridor pair')   
    
    df.reset_index(drop=True, inplace=True)
    
    time_export = strftime("%Y-%m-%d %H%M%S", localtime())
    file_dir = os.path.join(os.getcwd(), f"WU_exports_{time_export}")

    all_pycountry_countries = [country.name for country in pycountry.countries]

    driver_path = 'chrome/chromedriver'
    chrome_path = 'chrome/google-chrome'

    def process_corridor(i):
        driver = initialize_chrome_driver(chrome_path, driver_path)
        output_data = []
        
        sending_country = df.loc[i, 'Sending country']
        send_path = get_country_isocode(sending_country, all_pycountry_countries).lower()
        
        if send_path in ['cn', 'kr', 'om', 'kw', 'ca']:
            driver.quit()
            return output_data
        
        receiving_country = df.loc[i, 'Receiving country']
        receive_path = get_country_isocode(receiving_country, all_pycountry_countries).upper()
        receive_curr_path = get_currency_code(receive_path)
        
        for j in range(len(df.filter(like='ticket').columns)):
            ticket_size = df.loc[i, f"ticket size {j+1}"]
            if ticket_size:
                url = f"https://www.westernunion.com/{send_path}/en/web/send-money/start?ReceiveCountry={receive_path}&ISOCurrency={receive_curr_path}&SendAmount={ticket_size}&FundsOut=BA&FundsIn=BA"
                driver.get(url)
                
                print(i, sending_country, receiving_country, ticket_size)
                extracted_data = extract_data(driver, url, send_path, receive_path)
                print(extracted_data)
                
                if None not in extracted_data:
                    output_data.append(extracted_data)
                
        driver.quit()
        return output_data

    output_data = []
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        future_to_corridor = {executor.submit(process_corridor, i): i for i in range(len(df))}
        for future in as_completed(future_to_corridor):
            try:
                data = future.result()
                output_data.extend(data)
            except Exception as exc:
                print(f"Generated an exception: {exc}")

    global df_new
    df_new = pd.DataFrame(output_data, 
                          columns=['country_send', 'country_receive', 
                                   'company_name', 'ticket_size', 'timestamp', 
                                   'fx_rate_3', 'service_fee'])  
    
    print("Size of output dataframe:", df_new.shape)
    print(df_new.head())
    df_new.to_csv('sample/wu_new.csv')
    print("Write to sample CSV successfully")
    
    end_time = time.time()
    time_taken = end_time - start_time
    print(f"Time taken to run program: {round(time_taken, 2)} seconds")

    return df_new

def initialize_chrome_driver(chrome_path, driver_path):
    # Set up Chrome options
    options = Options()
    options.binary_location = chrome_path
    options.page_load_strategy = 'normal'
    options.add_argument("start-maximized")
    options.add_argument("enable-automation")
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Set up ChromeDriver service
    service = Service(executable_path=driver_path)

    # Initialize the web driver
    driver = webdriver.Chrome(service=service, options=options)
    return driver    
    

# Gets country isocode according to the closest match obtained 
def get_country_isocode(match_name, match_list):
    # Find the close matches between the country strings in the dataframe with the ones in the pycountry library 
    close_matches = process.extractOne(match_name, match_list, scorer = fuzz.ratio)
    if close_matches:
        try:
            return pycountry.countries.lookup(close_matches[0]).alpha_2
        except LookupError:
            print(f"Isocode for '{match_name}' not found.")
            return None
    else:
        print(f"No matches found for '{match_name}'")
        return None

# Gets currency isocode according to the currency code by referring to a pre-defined excel table
def get_currency_code(country_isocode):
    # Pre-defined excel table
    df_isocodes = pd.read_excel('input/country_code.xlsx')
    receive_curr_path = df_isocodes.loc[df_isocodes["ISO2 Name"] == country_isocode, 
                                        "CURRENCY CODE"].to_string(index=False)
    return receive_curr_path


# ------------------ IN PROGRESS ------------------
# def exceed_max_amt(driver, ticket_size):
#     soup = BeautifulSoup(driver.page_source, 'html.parser')

#     limit_exceed = soup.find('div', class_='font-input-label-focus SenderAmount_errorMessage___u1Wp')
#     if limit_exceed:
#         limit_exceed_message = limit_exceed.get_text().replace(u'\xa0', u' ').strip()
#         max_amt = float(match_text(r"([\d\.\,]+)\s*[A-Z]{3}", limit_exceed_message, 1).replace(",", ""))
#         print(f"Max limit exceeded. Readjusting ticket size to {max_amt}")
#         return max_amt 
    
#     return ticket_size
    
# #     #if max_amt > ticket_size:
#         # div class = font-input-label-focus SenderAmount_errorMessage___u1Wp
#         # div id = error_estimate_details_sender 
#         # "sender_field"
#         # "receiver_field"
#         # "TotalPayout"
#         #error_estimate_details_sender
# ------------------ IN PROGRESS ------------------


def extract_data(driver, url, send_path, receive_path):
    match_country_send = get_currency_code(send_path.upper())
    match_country_receive = get_currency_code(receive_path.upper())
    data = [match_country_send, match_country_receive, "Western Union", None, None, None, None]
    
    #ui1
    if 'start' in requests.get(url).url: 
        data = ui1_clean_text(ui1_scrape_text(driver, url))
        
        # readjust window size for screenshot purposes         
        driver.execute_script("document.body.style.zoom='50%'")
        payment_window = driver.find_element(By.CSS_SELECTOR, ".left-container.mob-container-new")
        driver.execute_script("arguments[0].scrollIntoView(true);", payment_window)
    
    #ui2
    elif 'estimate-details' in requests.get(url).url:
        data = ui2_scrape_text(driver, url)
        
        # readjust window size for screenshot purposes         
        driver.execute_script("document.body.style.zoom='80%'")
    
    return [match_country_send, match_country_receive, "Western Union", data[0], data[1], data[2], data[3]]


def ui1_adjust_payment_options(driver):
    #select receiver payment options for interface1
    ui1_select_bank_payment(driver, 'in')
    #select sender payment options for interface1
    ui1_select_bank_payment(driver, 'out')
    
    #close any pop-up boxes
    try:
        x_btn = driver.find_element(By.XPATH, "//button[contains(@class, 'close wu-outline-none')]")
        driver.execute_script("arguments[0].click();", x_btn)
    except:
        pass 
    

def ui1_select_bank_payment(driver,funds_in_or_out):
    #get the container with all the payment options
    if funds_in_or_out == 'in':
        funds_container = driver.find_element(By.XPATH, "//div[@id='funds-in-container']")
    elif funds_in_or_out == 'out':
        funds_out_class = ".row margin-left-0 margin-right-minus-15 ng-scope tiles-container ng-star-inserted".replace(' ', '.')
        try:
            funds_container = driver.find_element(By.CSS_SELECTOR, funds_out_class)
        except Exception as e:
            return
        
    # find all payment options with strings "Bank transfer"/ "Bank account" in the container
    try:
        funds_options = funds_container.find_elements(By.XPATH, ".//*[contains(text(),'Bank account') or contains(text(),'Bank transfer')]")
        driver.execute_script("arguments[0].click();", funds_options[0])
    except:
        # if the above 2 strings don't exist, try to find and select "Instant bank transfer"
        try:
            funds_options = funds_container.find_elements(By.XPATH, ".//*[contains(text(),'Instant bank transfer')]")
            driver.execute_script("arguments[0].click();", funds_options[0])
        #If all 3 strings don't exist, proceed with default selection
        except:
            pass
        
     # ###DEBUG ---------------------------------------------------
    if len(funds_options)>1:
        for option in funds_options:
            print(f"funds {funds_in_or_out} options:", option.text)
     # ###DEBUG ---------------------------------------------------
    
def ui2_adjust_payment_options(driver):
    ui2_select_bank_payment(driver, 'in')
    time.sleep(2)    
    
    # ------------------ IN PROGRESS ------------------
    #close any pop-up boxes
    try:
        pop_up = driver.find_element(By.ID, "popup_message")
        btn = pop_up.find_elements(By.TAG_NAME, "button")
        driver.execute_script("arguments[0].click();", btn[-1])       
    except NoSuchElementException:
        pass

    #Edge_case: for countries like UAE, selecting bank transfer redirects to a list of banks so redirect back to payment page
    try:
        driver.find_element(By.XPATH, "//div[@id='icon_back']").click()
        time.sleep(2)
    except:
        pass
    # ------------------ IN PROGRESS ------------------
    
    ui2_select_bank_payment(driver, 'out')
    #Edge_case: Canada has pop-ups that occur rather frequently
    #close pop-up
        
def ui2_select_bank_payment(driver, funds_in_or_out):
    if funds_in_or_out=='in':
        index = 0
    elif funds_in_or_out == 'out':
        index = 1
    
    #get the container with all the payment options
    try:
        funds_container = driver.find_element(By.XPATH, f"//div[@id='react-select-dropdown_estimate_details_pay{funds_in_or_out}-listbox']")
    except:
        #click to open the dropdown box if the browser doesn't open it automatically
        try:
            dropdown = driver.find_elements(By.XPATH, "//div[@id='estimate_details_fifo_tiles_container']")
            dropdown[index].click()
            funds_container = driver.find_element(By.XPATH, f"//div[@id='react-select-dropdown_estimate_details_pay{funds_in_or_out}-listbox']")
        #Edge_case: Canada has 2 different interfaces
        except:
            return 
    # find all payment options in the container
    funds_options = funds_container.find_elements(By.XPATH, f"//*[contains(@id,'funds{funds_in_or_out.capitalize()}')]")        
    # find all payment options with strings "Bank transfer"/ "Bank account" in the container
    funds_bank_options = [option for option in funds_options if 'bank' in option.text.lower()]
    
    # ###DEBUG ---------------------------------------------------
    if len(funds_bank_options)>1:
        for option in funds_bank_options:
            print(f"funds {funds_in_or_out} options:", option.text) 
     # ###DEBUG ---------------------------------------------------
    
    #find and select the payment option with the word "bank"
    if funds_bank_options!=[]:
        driver.execute_script("arguments[0].click();", funds_bank_options[0])  
    #if there are no "bank" related payment options, proceed with the first option in the payment dropdown list
    else:
        driver.execute_script("arguments[0].click();", funds_options[0])


def ui2_scrape_text(driver, url):
    
    wait = WebDriverWait(driver, 10)
    
    try:
        wait.until((EC.presence_of_element_located((By.XPATH, "//div[contains(@class,'TotalPayout_')]"))))
    except TimeoutException:
        #print("timeout")
        pass
    
    ui2_adjust_payment_options(driver)
    time.sleep(10)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    match_adjusted_ticket_size = soup.find('input', id = "input-estimate_details_sender_field")['value']
    # match_country_send = soup.find('div', id = "currency-estimate_details_sender_field").get_text()
    # match_value_receive = soup.find('input', id = "input-estimate_details_receiver_field")['value']
    # match_country_receive = soup.find('div', id = "currency-(dropdown-)?estimate_details_receiver_field").get_text().replace(u'\xa0', u'')
    try:
        fx_rate_text = soup.find('span', id = "label_estimate_details_exchangeRate").get_text().replace(u'\xa0', u' ').strip()
        fx_rate_pattern = r"(?:1\s([A-Z]{3})\s*\=\s*([\d\.\,]+)\s*(?:[\d\.\,]+)?\s*([A-Z]{3})?)"
        match_fx_rate = match_text(fx_rate_pattern, fx_rate_text, 2)
    except AttributeError:
        match_fx_rate = "Error"
    #match_service_fee = soup.find('div', {"aria-label":True}).get_text().replace(u'\xa0', u' ').strip()
    
    
    #scrape Western Union's fees
    #there are 3 trys because somehow Canada has 2 slightly different interfaces when I scrape it
    try:
        match_service_fee = soup.find('span', id = "label_estimate_details_strike_fees_value").get_text().replace(u'\xa0', u' ').strip()
    except AttributeError:
        try: 
            service_fee_text = soup.find('span', id = "text_estimate_details_fees").get_text().replace(u'\xa0', u' ').strip()
            service_fee_pattern = r"([\d\.\,]+)\s*(?:[\d\.\,]+)?\s*(?:[A-Z]{3})"
            match_service_fee = match_text(service_fee_pattern, service_fee_text, 1)
        except AttributeError:
            try:
                match_service_fee = soup.find('span', id = "label_estimate_details_fees_value").get_text().replace(u'\xa0', u' ').strip()
            except AttributeError:
                match_service_fee = "Error"
    
    timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
    
    return [match_adjusted_ticket_size, 
            timestamp, 
            match_fx_rate, 
            match_service_fee]
            #calculated_service_fee] 


def ui1_scrape_text(driver, url):    
    wait = WebDriverWait(driver, 10)

    try:
        wait.until((EC.text_to_be_present_in_element((By.CSS_SELECTOR, f".{'trxn-summary.sum-wid-ff'}"), 'Exchange Rate')))
        wait.until(EC.presence_of_element_located((By.ID, 'funds-in-container')))
    except TimeoutException:
        pass

    ui1_adjust_payment_options(driver)
    time.sleep(10)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    container = soup.find('section', class_='trxn-summary sum-wid-ff')
    
    if container:     
        return container.get_text().replace(u'\xa0', u' ')
    return "error"

def ui1_clean_text(text):
    #Uses regular expression to match string patterns
    match_adjusted_ticket_size = match_text(r"(?:Transfer amount)([\d\.\,]+)\s([A-Z]{3})", text, 1) 
    # match_country_send = match_text(r"(?:Transfer amount)([\d\.\,]+)\s([A-Z]{3})", text, 2)
    # match_country_receive = match_text(r"(?:Total\s+to receiver)([\d\.\,]+)([A-Z]{3})", text, 2)
    match_service_fee = match_text(r"(?:Transfer fee[\d\+\,]+)\s([\d\.\,]+)\s[A-Z]{3}", text, 1)    
    match_fx_rate = match_text(r"(?:Exchange Rate2)(?:([\d\.\,]+)\s[A-Z]{3})?(?:1\.00\s[A-Z]{3}\s\=\s([\d\.\,]+)\s[A-Z]{3})", text, 2)
    timestamp = strftime("%Y-%m-%d %H:%M:%S", localtime())
    
    if 'discount' in text.lower():
        #Scrapes the usual fee for countries that offer first time discount
        match_service_fee = match_text(r"([\d\.\,]+)\s[A-Z]{3}(?:Transfer fee[\d\+\,]+)", text, 1)     
        match_fx_rate = match_text(r"(?:Exchange Rate2)(?:([\d\.\,]+)\s[A-Z]{3})?(?:1\.00\s[A-Z]{3}\s\=\s([\d\.\,]+)\s[A-Z]{3})", text, 1)
        
    return [match_adjusted_ticket_size, 
            timestamp, 
            match_fx_rate, 
            match_service_fee]

def match_text(string, text, matchgroup):
    if re.search(string, text):
        return re.search(string, text).group(matchgroup)
    return None

