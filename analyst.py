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
                if pd.isna(val):
                    worksheet.write_blank(excel_row, col_idx, None)
                elif isinstance(val, (int, float)):
                    worksheet.write_number(excel_row, col_idx, float(val))
                else:
                    worksheet.write(excel_row, col_idx, str(val))


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

    def price_to_9(self, price):
        if pd.isna(price):
            return price
        price = int(round(price))
        return int(str(price)[:-1] + "9") if price > 9 else 9

    def calculate_recommended_price(self, row):

        min_price = row["competitor_min_price"]
        my_price = row["m_p1"]
        purchase_price = row["m_pp"]

        # --- VALIDÁLÁS ---
        if pd.isna(min_price):
            return np.nan

        if pd.isna(purchase_price):
            return np.nan

        # --- ALAP ÁR ---
        price = float(min_price)

        # --- LOGIKA ---
        if pd.notna(my_price) and my_price <= min_price:
            price = float(min_price)

        # --- RANDOM ---
        rand = random.uniform(-0.01, 0.01)
        price = price * (1 + rand)

        # --- KEREKÍTÉS ---
        price = self.price_to_9(price)

        # --- MIN PROFIT ---
        min_allowed = float(purchase_price) * 1.1

        if price < min_allowed:
            price = self.price_to_9(min_allowed)

        return price

    def analys_price_data(self, df):
        df["m_p1"] = pd.to_numeric(df["m_p1"], errors="coerce")
        df["m_pp"] = pd.to_numeric(df["m_pp"], errors="coerce")

        price_cols = [c for c in df.columns if c.endswith("_price") and not c.endswith("_sale_price")]

        df[price_cols] = df[price_cols].apply(pd.to_numeric, errors="coerce")

        df["competitor_count"] = df[price_cols].notna().sum(axis=1)
        df["competitor_avg_price"] = df[price_cols].mean(axis=1)
        df["competitor_min_price"] = df[price_cols].min(axis=1)

        df["m_price_vs_min_%"] = (
            df["shop0_p"] / df["competitor_min_price"] * 100
        ).replace([np.inf, -np.inf], np.nan)

        df["min_price_vs_purchase_%"] = (
            df["competitor_min_price"] / df["m_pp"] * 100
        ).replace([np.inf, -np.inf], np.nan)

        df["price_diff"] = df["shop0_p"] - df["competitor_min_price"]

        df["recommended_price"] = df.apply(self.calculate_recommended_price, axis=1)

        df["price_change"] = df["recommended_price"] - df["m_p1"]

        return df

    def rename_price_df(self, df, webshops_df):
        shop_map = dict(zip(webshops_df["id"], webshops_df["name"]))
        
        rename_map = {}

        for shop_id, shop_name in shop_map.items():

            rename_map[f"shop{shop_id}_price"] = f"{shop_name} ár"
            rename_map[f"shop{shop_id}_sale_price"] = f"{shop_name} akciós ár"
            rename_map[f"shop{shop_id}_url"] = f"{shop_name} link"

        df = df.rename(columns=rename_map)

        return df
