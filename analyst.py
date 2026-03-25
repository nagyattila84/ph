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

        workbook = writer.book
        worksheet = workbook.add_worksheet("Prices")
        writer.sheets["Prices"] = worksheet

        # --- FORMÁTUMOK (egyszer létrehozva!) ---
        red_format = workbook.add_format({"font_color": "red"})
        bold_format = workbook.add_format({"bold": True})
        green_bold = workbook.add_format({"font_color": "green", "bold": True})

        link_formats = {
            "default": workbook.add_format({"font_color": "blue", "underline": 1}),
            "red": workbook.add_format({"font_color": "red", "underline": 1}),
            "bold": workbook.add_format({"bold": True, "underline": 1}),
            "green": workbook.add_format({"font_color": "green", "bold": True, "underline": 1}),
        }

        # --- OSZLOPOK SZÉTVÁLASZTÁSA ---
        price_cols = [c for c in df.columns if c.endswith("_price")]
        url_cols = [c for c in df.columns if c.endswith("_url")]

        export_cols = [c for c in df.columns if c not in price_cols + url_cols]

        my_price_col = "shop0_p"

        # --- HEADER KIÍRÁS ---
        for col_idx, col in enumerate(export_cols):
            worksheet.write(0, col_idx, col)

        start_col = len(export_cols)

        for i, col in enumerate(price_cols):
            worksheet.write(0, start_col + i, col)

        # --- ADATOK ---
        for row in range(len(df)):

            excel_row = row + 1

            # normál mezők
            for col_idx, col in enumerate(export_cols):
                val = df.iloc[row][col]
                worksheet.write(excel_row, col_idx, val)

            my_price = df.iloc[row].get(my_price_col)

            prices = [
                df.iloc[row][c]
                for c in price_cols
                if pd.notna(df.iloc[row][c])
            ]

            if not prices:
                continue

            min_price = min(prices)
            own_is_cheapest = pd.notna(my_price) and my_price <= min_price

            # --- PRICE + LINK ---
            for i, col in enumerate(price_cols):

                price = df.iloc[row][col]
                if pd.isna(price):
                    continue

                url_col = col.replace("_price", "_url")
                url = df.iloc[row].get(url_col)

                col_idx = start_col + i

                # --- FORMÁTUM LOGIKA ---
                cell_format = None

                if pd.notna(my_price) and price < my_price:
                    cell_format = "red"

                if price == min_price:
                    cell_format = "bold"

                if own_is_cheapest and col == my_price_col:
                    cell_format = "green"

                # --- HYPERLINKES ÍRÁS ---
                if pd.notna(url):

                    fmt = link_formats.get(cell_format, link_formats["default"])

                    worksheet.write_url(
                        excel_row,
                        col_idx,
                        url,
                        fmt,
                        string=f"{price:,.0f}"
                    )
                else:
                    fmt = None
                    if cell_format == "red":
                        fmt = red_format
                    elif cell_format == "bold":
                        fmt = bold_format
                    elif cell_format == "green":
                        fmt = green_bold

                    worksheet.write(excel_row, col_idx, price, fmt)

        # --- EXTRÁK ---
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(df), start_col + len(price_cols) - 1)

        writer.close()
        output.seek(0)

        return output
