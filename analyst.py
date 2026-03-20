import pandas as pd
import numpy as np
from io import BytesIO
from datamanager import SupaBaseDataManager

class PriceAnalyst:

    def __init__(self, dm):
        self.dm = dm

    def get_cluster_price_view(self, keyword=None):
        clusters = self.dm.get_clusters(keyword)
        own, raw = self.dm.get_products_by_keyword(keyword)
        links = self.dm.read_data("product_cluster_links")
        shops = self.dm.read_data("webshops")
        
        df = clusters.join(links, how="outer", lsuffix="_suffcluster", rsuffix="_sufflink")
    
        return df


    def create_price_data_excel(self, df):

        output = BytesIO()

        writer = pd.ExcelWriter(output, engine="xlsxwriter")
        df.to_excel(writer, sheet_name="Prices", index=False)

        workbook = writer.book
        worksheet = writer.sheets["Prices"]

        # formátumok
        red_format = workbook.add_format({"font_color": "red"})
        bold_format = workbook.add_format({"bold": True})
        green_bold = workbook.add_format({"font_color": "green", "bold": True})

        # fejléc rögzítés
        worksheet.freeze_panes(1, 0)

        # automata filter
        worksheet.autofilter(0, 0, len(df), len(df.columns) - 1)

        price_cols = [c for c in df.columns if c.startswith("shop") and c.endswith("_price")]
        my_price_col = "shop0_p"

        for row in range(len(df)):

            my_price = df.iloc[row][my_price_col]

            prices = []
            for col in price_cols:
                val = df.iloc[row][col]
                if pd.notna(val):
                    prices.append(val)

            if len(prices) == 0:
                continue

            min_price = min(prices)
            own_is_cheapest = pd.notna(my_price) and my_price <= min_price

            # saját ár kiemelés
            if own_is_cheapest:
                col_idx = df.columns.get_loc(my_price_col)
                worksheet.write(row+1, col_idx, my_price, green_bold)

            for col in price_cols:

                url_col = col.replace("_price", "_url")
                price = df.iloc[row][col]
                url = df.iloc[row][url_col] if url_col in df.columns else None

                if pd.isna(price):
                    continue

                col_idx = df.columns.get_loc(col)

                cell_format = None

                if pd.notna(my_price) and price < my_price:
                    cell_format = red_format

                if price == min_price:
                    cell_format = bold_format

                if pd.notna(url):

                    # hyperlink formátum alapból (kék + aláhúzott)
                    link_format = workbook.add_format({
                        "font_color": "blue",
                        "underline": 1
                    })

                    # kombinált formátum (ha van extra highlight)
                    if cell_format == red_format:
                        link_format = workbook.add_format({
                            "font_color": "red",
                            "underline": 1
                        })
                    elif cell_format == bold_format:
                        link_format = workbook.add_format({
                            "bold": True,
                            "underline": 1
                        })
                    elif own_is_cheapest and col == my_price_col:
                        link_format = workbook.add_format({
                            "font_color": "green",
                            "bold": True,
                            "underline": 1
                        })

                    worksheet.write_url(
                        row + 1,
                        col_idx,
                        url,
                        link_format,
                        string=f"{price:,.0f}"
                    )
                else:
                    worksheet.write(row + 1, col_idx, price, cell_format)

        # URL oszlopok elrejtése
        for col in df.columns:
            if col.endswith("_url"):
                idx = df.columns.get_loc(col)
                worksheet.set_column(idx, idx, None, None, {"hidden": True})

        writer.close()
        output.seek(0)

        return output
