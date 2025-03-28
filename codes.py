import pandas as pd
import gspread
from woocommerce import API
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

#credentials_path 
google_credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH")
woocommerce_consumer_key = os.getenv("WOOCOMMERCE_CONSUMER_KEY")
woocommerce_consumer_secret = os.getenv("WOOCOMMERCE_CONSUMER_SECRET")

# Google Sheets setup
def connect_google_sheets():
    gc = gspread.service_account(filename=google_credentials_path)
    sheet = gc.open('Copy of Daily Product Sales Sheet').worksheet('AMAZON FLEX')
    # don't forget to change the sheet path and credentials.json file path
    return sheet

# WooCommerce API setup
def connect_woocommerce():
    return API(
    url="https://www.remedywala.com/",
    consumer_key = woocommerce_consumer_key,
    consumer_secret= woocommerce_consumer_secret,
    version="wc/v3"
    )

last_filled_row = len(connect_google_sheets().get_all_records()) + 2
print(last_filled_row)

# Step 1: Read Amazon Excel and Update Google Sheet
def update_google_sheet_from_amazon(file_path):

    google_sheet_data = connect_google_sheets().get_all_records()
    todays_date = datetime.today().strftime('%#d-%#m-%y')
    existing_dates = [row.get("DATE","").strip() for row in google_sheet_data]

    if todays_date in existing_dates:
        print("data already existed")
    else:
        df = pd.read_csv(file_path)  # Read Excel file
        df.loc[df.duplicated(subset='Customer Order ID',keep='first'),'Customer Order ID'] = ""
        amazon_headers = {'Customer Order ID': 'ORDER ID', 'Title':'TITLE','Units':'QTY','Order Value':'ORDER VALUE'}  # Mapping of headers
        df.rename(columns=amazon_headers, inplace=True)  
        # df.to_csv('updated_amazon.csv')
        google_sheet_headers = connect_google_sheets().row_values(1)
        # print(google_sheet_headers)
        date_column_index = google_sheet_headers.index('DATE') if 'DATE' in google_sheet_headers else None
        today_date = datetime.today().strftime('%#d-%#m-%y')
        data_to_append = []
        for idx ,row in df.iterrows():
            row_data = [row[google_header] if google_header in df.columns else "" for google_header in google_sheet_headers]
            if date_column_index is not None and idx == 0:
                row_data[date_column_index] = today_date
            data_to_append.append(row_data)
        connect_google_sheets().append_rows(data_to_append, value_input_option='RAW')
        # print("Google Sheet updated successfully.")
        update_todays_inventory()


# STEP 3: CHECK STOCK AGAIN AFTER UPDATION
def check_stock_again(sku,current_stock,index):
        response2 = connect_woocommerce().get("products", params={"sku": sku}).json()

        if response2:
            product2  = response2[0]
            product_id2 = product2["id"]   
            stock_after_update = product2["stock_quantity"] if product2["stock_quantity"] else 0
            # print(f"stock after updation of {sku} = {stock_after_update}")
            if stock_after_update == current_stock:
                connect_google_sheets().update_cell(index,6,"Fail")
            else:
                connect_google_sheets().update_cell(index,6,"Pass")


# STEP 4: UPDATE STOCK IN WOOCOMMERCE
def update_stock(woocommerce, sku, quantity_sold,index,title):
    response = woocommerce.get("products", params={"sku": sku}).json()
    if response:
        
        product = response[0]  # Get the first matching product
        product_id = product["id"]

        current_stock = product["stock_quantity"] if product["stock_quantity"] else 0
        # print(f"current_stock value of {sku}= {current_stock}")

            # Calculate new stock
        new_stock = max(current_stock - quantity_sold, 0)  # Prevent negative stock

            # Update WooCommerce stock
        update_data = {"stock_quantity": new_stock}
        update_response = woocommerce.put(f"products/{product_id}", update_data).json()

        # print(f"✅ Updated SKU: {sku} | Old Stock: {current_stock} | New Stock: {new_stock}")
        check_stock_again(sku,current_stock=current_stock,index=index)

    else:
        if "strip" in title:
            connect_google_sheets().update_cell(index,6,"Pass")
            # print(f"✅ SKU {sku} (Strip Product) not found, but marked as 'Pass'.")
        else:
            connect_google_sheets().update_cell(index, 6, "Fail")
            # print(f"⚠️ SKU {sku} not found in WooCommerce!")

# STEP 5: MAIN FUNCTION TO UPDATE TODAY'S INVENTORY
def update_todays_inventory():
    # sheet = connect_google_sheets()
    woocommerce = connect_woocommerce()
    if woocommerce:
        print('Connection Successfull')

    todays_inventory = get_todays_inventory()
    if not todays_inventory:
        print("⚠️ No sales records found for today!")
        return

    for index, row in enumerate(todays_inventory,start=last_filled_row):
        sku = row.get("MSKU")  # Adjust column name as per your Google Sheet
        # print(f"index is = {index}")
        # print(f"SKU is = {sku}")
        quantity_sold = int(row.get("QTY", 0))  # Adjust column name as per your Google Sheet
        title = row.get("TITLE","").strip().lower()
        # print(f"Title is  = {title}")
        update_status = row.get("UPDATE","").strip().lower()
        # print(update_status)

        if update_status.lower() in ["pass","fail"]:
            continue
        if "strip" in title:
            connect_google_sheets().update_cell(index,6,'Pass')
            # print("pass come because of strip word")
        elif sku and quantity_sold > 0:
            update_stock(woocommerce, sku, quantity_sold,index,title)
            
    # print(todays_inventory)

def get_todays_inventory():
    google_sheet_data = connect_google_sheets().get_all_records()  # Fetch all data as a list of dictionaries

    todays_date = datetime.today().strftime("%#d-%#m-%y")  # Format as per your Google Sheet date format

    # Filter only today's records
    todays_records = []
    found_today = False  # Flag to check when today's data starts

    for row in google_sheet_data:
        row_date = row.get("DATE")  # Get the date from the row

        if row_date == todays_date:  
            found_today = True  # Start collecting today's data
            todays_records.append(row)
        elif found_today and row_date:  
            # If we already found today's records and now see another date, stop.
            break
        elif found_today and not row_date:
            # If the date column is empty, but we're still processing today’s records, continue.
            todays_records.append(row)
    return todays_records