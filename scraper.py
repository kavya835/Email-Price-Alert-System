from playwright.sync_api import sync_playwright
import pandas as pd                 #filtering, reading and writing data
from bs4 import BeautifulSoup       #querying HTML for elements
from price_parser import Price      #extracting the price
from twilio.rest import Client


PRODUCT_URL_CSV = "products.csv"
SAVE_TO_CSV = False      #fetch prices
PRICES_CSV = "prices.csv"
SEND_TEXT = True

# Twilio setup
ACCOUNT_SID = ""
AUTH_TOKEN = ""
TWILIO_NUMBER = ""
MY_PHONE_NUMBER = ""

client = Client(ACCOUNT_SID, AUTH_TOKEN)


def get_urls(csv_file):
    df = pd.read_csv(csv_file)
    return df   #returns a DataFrame object

def process_products(df):
    updated_products = []
    for product in df.to_dict("records"):   #converts DataFrame into a list of dictionaries
        # product is a dictionary which uses url as the key to identify the URL
        # i.e. product["url"] is the URL

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # set headless=False to watch it run
            page = browser.new_page()
            page.goto(product["url"], timeout=60000)

            # Wait until the price element is present in the DOM
            page.wait_for_selector(".product-sales-price")

            # Get the fully rendered HTML
            html = page.content()

            browser.close()

        product["price"] = get_price(html)  #new key-value of price -> price-value
        if(product["price"] > 0):
            product["alert"] = product["price"] < product["alert_price"]    #boolean value
        else:
            product["alert"] = False

        updated_products.append(product)    #product price is done being checked
        #continue this for all the products
    return pd.DataFrame(updated_products)   #new DataFrame

def get_price(html):
    price = 0
    soup = BeautifulSoup(html, "lxml")  #creating a BeautifulSoup object using the HTML response
    el = soup.select_one(".product-sales-price")    #'price_color' is the class of the HTML element #the . in front of it is used to select the elements of this class in the CSS
    if el:
        price = Price.fromstring(el.get_text(strip=True))
        price = Price.fromstring(el.text)   #el.text contains the price and currency symbol which needs to be removed
    else:
        print("Price element not found")
    return price.amount_float


def send_text(df, TWILIO_NUMBER, MY_PHONE_NUMBER):
    data = df[df["alert"]]
    if data.empty:
        return
    
    message = "NOW ON SALE!"

    
    for index, row in data.iterrows():
        message += "\n"
        message += (row["product"] +": " + str(row["price"]))

    
    client.messages.create(
        body=message,
        from_=TWILIO_NUMBER,
        to=MY_PHONE_NUMBER
    )


def main():
    df = get_urls(PRODUCT_URL_CSV)
    df_updated = process_products(df)
    if SAVE_TO_CSV:
        df_updated.to_csv(PRICES_CSV, index=False, mode="w")
    if SEND_TEXT:
        send_text(df_updated, TWILIO_NUMBER, MY_PHONE_NUMBER)


main()