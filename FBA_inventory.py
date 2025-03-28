import pandas as pd
import gspread , time , string
from woocommerce import API
from datetime import datetime , timedelta
import os
from dotenv import load_dotenv

load_dotenv()

def connect_fba_inventory_google_workbook():
    google_sheet_credentials_path = os.getenv("FBA_GOOGLE_CRENDETIALS_PATH")
    gc = gspread.service_account(filename=google_sheet_credentials_path)
    workbook = gc.open('FBA Inventory')
    return workbook



def read_fba_inventory(fba_sheet):
    yesterday_date = (datetime.today() - timedelta(days=1)).strftime('%m/%d/%Y')
    # yesterday_date = '03/26/2025'
    print(yesterday_date)
    # today_date = '03/03/2025'
    fba_data = pd.read_csv(fba_sheet)
    print(fba_data['Date'][0])
    if fba_data['Date'][0] == yesterday_date:
        # print(fba_data['Date'])
        print('done')
        new_fba_data = fba_data.loc[fba_data['Disposition']=='SELLABLE'][['ASIN','Ending Warehouse Balance','Location']]
        return new_fba_data
    else:
        print('Data is of not todays date')

def column_number_to_letter(column_number):
    """Converts a 1-based column index to a Google Sheets column letter (e.g., 1 -> A, 28 -> AB)."""
    result = ""
    while column_number > 0:
        column_number, remainder = divmod(column_number - 1, 26)
        result = string.ascii_uppercase[remainder] + result
        # print(f"col number letter result is = {result}")
    return result

def clear_today_stock_column():
    """Clears all values in the 'Todays Stock' column for all sheets."""
    google_workbook = connect_fba_inventory_google_workbook()
    google_sheets = google_workbook.worksheets()

    for sheet in google_sheets:
        # print(f"Clearing 'Today Stock' values in sheet - {sheet.title}")

        # Get headers and find the index of "Todays Stock" column
        google_sheet_headers = sheet.row_values(1)
        if "Today Stock" not in google_sheet_headers:
            # print(f"⚠️ 'Today Stock' column not found in {sheet.title}, skipping...")
            continue

        stock_index = google_sheet_headers.index("Today Stock") + 1  # 1-based index
        status_index = google_sheet_headers.index("UPDATE Status") + 1
        row_count = len(sheet.get_all_records()) + 1  # Total rows + header
        stock_column_letter = column_number_to_letter(stock_index)
        clear_range = f"{stock_column_letter}2:{stock_column_letter}{row_count}"
        sheet.batch_clear([clear_range]) # Efficiently clear the entire column
        
        status_column_letter = column_number_to_letter(status_index)
        clear_status_range = f"{status_column_letter}2:{status_column_letter}{row_count}"
        sheet.batch_clear([clear_status_range])

        # print(f"✅ Cleared 'Todays Stock' column in {sheet.title}")



def update_fba_today_inventory(fba_inventory_ledger_data):
    google_workbook = connect_fba_inventory_google_workbook() # This will get all records as a list of dictionaries
    google_sheet = google_workbook.worksheets()
    # print(google_sheet_data[0])
    row_count = 0

    for sheet in google_sheet:
        # print(f"Updating sheet - {sheet.title}")
        google_sheet_data = sheet.get_all_records()
        google_sheet_headers = sheet.row_values(1)
        # print(f"Google Sheet Headers of {sheet} is - {google_sheet_headers}")
        
        fba_data = {
                asin : {"stock": ending_warehouse_balance, "location" : location}
                for asin, ending_warehouse_balance, location in zip(
                    fba_inventory_ledger_data['ASIN'], fba_inventory_ledger_data['Ending Warehouse Balance'], fba_inventory_ledger_data['Location'])
                if location == sheet.title
            }
        # print(f"row count before completing {sheet.title} is {row_count}")

        for idx, row in enumerate(google_sheet_data,start=2):
            asin = row.get('ASIN')
            # print(asin)
            row_count+=1
            # print(f"row count is {row_count}")
            if asin in fba_data:
                sheet.update_cell(idx, 4, fba_data[asin]['stock'])
                # sheet.update_cell(idx, 9, "Value Updated")
                # print(f"Updated stock for {asin} to {fba_data[asin]['stock']}")
            elif asin == "":
                continue
            else:
                sheet.update_cell(idx, 9, "Value Not Updated")
                # print(f"Stock for {asin} not found in FBA data")

            if row_count % 80 == 0:
                # print("⏳ Sleeping for 60 seconds to avoid quota limits...")
                time.sleep(60)
        # print(f"row count after completing {sheet.title} is {row_count}")        



def main(fba_inventory_data_path):
    # fba_inventory_data_path = "125603020157.csv"
    fba_inventory_ledger_data = read_fba_inventory(fba_inventory_data_path)
    clear_today_stock_column()
    update_fba_today_inventory(fba_inventory_ledger_data)





