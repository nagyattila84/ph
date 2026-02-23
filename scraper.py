import re
import requests
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup

#formazott uzenetek
def error(msg):
    print(f"\033[1;91m{msg}\033[0m")

def warn(msg):
    print(f"\033[93m{msg}\033[0m")

def ok(msg):
    print(f"\033[92m{msg}\033[0m")

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class Webshop:
    id: int
    name: str
    base_url: str
    search_url: str
    company: str
    product_container_selector: str
    product_container_class: str
    name_selector: str
    name_class: str
    sku_selector: str | None
    sku_class: str | None
    sku_attr: str | None
    link_selector: str
    link_class: str
    price_selector: str
    price_class: str
    sale_price_selector: str
    sale_price_class: str

@dataclass
class AbstractProduct(ABC):
    id: int
    webshop_id: int
    cluster_id: int | None
    sku: str | None
    url: str | None
    name: str
    price: int

    def get_price(self):
        return self.price

@dataclass
class Product(AbstractProduct):
    id: int
    webshop_id: int
    cluster_id: int | None
    sku: str
    name: str
    url: str
    price: int
    sale_price: int
    scraped_date: str

#Novitax SQL lekérdezés:
#SELECT 0 as webshop_id, c.CIKKKOD1 as sku, c.CNEV as name, c.CAR1 as price, c.CAR2 as price2, c.CAR3 as price3, c.CAR4 as price4,c.CAR5 as price5, c.CAR6 as price6, c.UTBESZAR as purchase_price, CURRENT_DATE as scraped_date FROM CIKK c  WHERE alapraktar > 3;
@dataclass
class OwnProduct(AbstractProduct):
    id: int
    webshop_id: int
    cluster_id: int | None
    sku: str
    name: str
    url: str | None
    price: int
    price2: int
    price3: int
    price4: int
    price5: int
    price6: int
    purchase_price: int
    scraped_date: str

@dataclass
class Cluster(AbstractProduct):
    id: int
    name: str

class Scraper():
    def __init__(self):
        pass

    def get_price_from_multi_webshop_df(self, shops, search_word):
        results = pd.DataFrame()
        for _, row in shops.iterrows():
            results.append(self.get_price_from_webshop_df(row, search_word))
        return results

    # search_word - erre a szora keres az oldalon
    # visszadja a táblázatot, fejléc nélkül
    def get_price_from_webshop_df(self, shop, search_word):
        #kereső oldal linkej a kulcsszóra
        url = shop["search_url"].replace("SEARCH_WORD", search_word)
    
        #mai dátum megy a táblázatba, hogy visszakereshető egyen
        current_date = datetime.now().strftime("%Y-%m-%d")
    
        # Lekérjük a weboldal HTML tartalmát
        response = requests.get(url)
        print(f"Fetching URL: {url}\nHTTP Status Code: {response.status_code}")
    
        if response.status_code != 200:
            error("Error: Could not retrieve the webpage. Please check the URL or your internet connection.")
            return # Exit if the request failed
    
        soup = BeautifulSoup(response.content, "html.parser")
    
        # Megkeressük a termékeket tartalmazó elemeket
        products = soup.find_all(shop["product_container_selector"], class_=shop["product_container_class"])
        ok(f"Number of products found: {len(products)}")
    
        # Létrehozunk egy üres listát az adatok tárolására
        data = []
    
        # Végigiterálunk a termékeken és kinyerjük az adatokat
        for i, product in enumerate(products):
    
            #terméknév kikeresése
            name_element = product.find(shop["name_selector"], class_=shop["name_class"])
            if name_element:
                name = name_element.text.strip()
            else:
                error(f"Nincs terméknév")
                name = None
    
            #sku, cikkszám kikeresése
            sku_element = product.find(shop["sku_selector"], class_=shop["name_class"])
            if sku_element:
                if shop["sku_attr"]:
                    # Safely get attribute value, default to "Hiányzik" if not found
                    sku = sku_element.attrs.get(shop["sku_attr"], "Hiányzik")
                else:
                    # If sku_attr is None, assume SKU is the text content
                    sku = sku_element.text.strip()
            else:
                sku = None
    
            #url kikeresése
            link_element = product.find(shop["link_selector"], class_=shop["link_class"])
            if link_element and 'href' in link_element.attrs:
                url = link_element['href']
            else:
                warn(f"Nincs link")
                url = None
    
            #ár kikeresése
            price_element = product.find(shop["price_selector"], class_=shop["price_class"])
            if price_element:
                price = price_element.text.strip()
                price = re.sub(r'\D', '', price)
            else:
                error(f"Nincs ár!")
                price = None
    
            #akciós ár kikeresése
            sale_price_element = product.find(shop["sale_price_selector"], class_=shop["sale_price_class"])
            if sale_price_element:
                sale_price = sale_price_element.text.strip()
                sale_price = re.sub(r'\D', '', sale_price)
            else:
                sale_price = None
    
            data.append([shop["id"], sku, name, url, price, sale_price])
    
        # Létrehozunk egy pandas DataFrame-et az adatokból
        df = pd.DataFrame(data, columns=["webshop_id", "sku","name", "url", "price", "sale_price"])
    
        # Megjelenítjük/visszaadjuk a táblázatot
        return df

    # search_word - erre a szora keres az oldalon
    # visszadja a táblázatot, fejléc nélkül
    def download_price_from_webshop(self, ws, search_word):
        #kereső oldal linkej a kulcsszóra
        url = ws.search_url.replace("SEARCH_WORD", search_word)
    
        #mai dátum megy a táblázatba, hogy visszakereshető egyen
        current_date = datetime.now().strftime("%Y-%m-%d")
    
        # Lekérjük a weboldal HTML tartalmát
        response = requests.get(url)
        print(f"Fetching URL: {url}\nHTTP Status Code: {response.status_code}")
    
        if response.status_code != 200:
            error("Error: Could not retrieve the webpage. Please check the URL or your internet connection.")
            return # Exit if the request failed
    
        soup = BeautifulSoup(response.content, "html.parser")
    
        # Megkeressük a termékeket tartalmazó elemeket
        products = soup.find_all(ws.product_container_selector, class_=ws.product_container_class)
        ok(f"Number of products found: {len(products)}")
    
        # Létrehozunk egy üres listát az adatok tárolására
        data = []
    
        # Végigiterálunk a termékeken és kinyerjük az adatokat
        for i, product in enumerate(products):
    
            #terméknév kikeresése
            name_element = product.find(ws.name_selector, class_=ws.name_class)
            if name_element:
                name = name_element.text.strip()
            else:
                error(f"Nincs terméknév")
                name = None
    
            #sku, cikkszám kikeresése
            sku_element = product.find(ws.sku_selector, class_=ws.sku_class)
            if sku_element:
                if ws.sku_attr:
                    # Safely get attribute value, default to "Hiányzik" if not found
                    sku = sku_element.attrs.get(ws.sku_attr, "Hiányzik")
                else:
                    # If sku_attr is None, assume SKU is the text content
                    sku = sku_element.text.strip()
            else:
                sku = None
    
            #url kikeresése
            link_element = product.find(ws.link_selector, class_=ws.link_class)
            if link_element and 'href' in link_element.attrs:
                url = link_element['href']
            else:
                warn(f"Nincs link")
                url = None
    
            #ár kikeresése
            price_element = product.find(ws.price_selector, class_=ws.price_class)
            if price_element:
                price = price_element.text.strip()
                price = re.sub(r'\D', '', price)
            else:
                error(f"Nincs ár!")
                price = None
    
            #akciós ár kikeresése
            sale_price_element = product.find(ws.sale_price_selector, class_=ws.sale_price_class)
            if sale_price_element:
                sale_price = sale_price_element.text.strip()
                sale_price = re.sub(r'\D', '', sale_price)
            else:
                sale_price = None
    
            data.append([ws.id, sku, name, url, price, sale_price])
    
        # Létrehozunk egy pandas DataFrame-et az adatokból
        df = pd.DataFrame(data, columns=["webshop_id", "sku","name", "url", "price", "sale_price"])
    
        # Megjelenítjük/visszaadjuk a táblázatot
        return df

    def download_prices_from_df(self, webshops_df: pd.DataFrame, search_word: str):

        all_results = []

        current_date = datetime.now().strftime("%Y-%m-%d")

        for _, ws in webshops_df.iterrows():

            url = ws["search_url"].replace("SEARCH_WORD", search_word)

            response = requests.get(url, timeout=20)

            print(f"Fetching: {url} → {response.status_code}")

            if response.status_code != 200:
                print(f"❌ Failed: {url}")
                continue

            soup = BeautifulSoup(response.content, "html.parser")

            products = soup.find_all(
                ws["product_container_selector"],
                class_=ws["product_container_class"]
            )

            print(f"✓ {len(products)} products")

            for product in products:

                # NAME
                name_el = product.find(ws["name_selector"], class_=ws["name_class"])
                name = name_el.text.strip() if name_el else None

                # SKU
                sku_el = product.find(ws["sku_selector"], class_=ws["sku_class"])
                if sku_el:
                    if pd.notna(ws["sku_attr"]):
                        sku = sku_el.attrs.get(ws["sku_attr"])
                    else:
                        sku = sku_el.text.strip()
                else:
                    sku = None

                # LINK
                link_el = product.find(ws["link_selector"], class_=ws["link_class"])
                url_prod = link_el["href"] if link_el and "href" in link_el.attrs else None

                # PRICE
                price_el = product.find(ws["price_selector"], class_=ws["price_class"])
                price = re.sub(r"\D", "", price_el.text) if price_el else None

                # SALE PRICE
                sale_el = product.find(ws["sale_price_selector"], class_=ws["sale_price_class"])
                sale_price = re.sub(r"\D", "", sale_el.text) if sale_el else None

                all_results.append({
                    "webshop_id": ws["id"],
                    "sku": sku,
                    "name": name,
                    "url": url_prod,
                    "price": price,
                    "sale_price": sale_price,
                    "search_word": search_word,
                    "scrape_date": current_date
                })

        return pd.DataFrame(all_results)
        
