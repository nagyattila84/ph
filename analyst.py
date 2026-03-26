import pandas as pd
import random
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

    def create_price_data_excel_formulas(self, df):

        from io import BytesIO
        import xlsxwriter.utility as xl

        output = BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")

        workbook = writer.book
        worksheet = workbook.add_worksheet("Prices")
        writer.sheets["Prices"] = worksheet

        # --- OSZLOPOK ---
        price_cols = [c for c in df.columns if c.endswith("_price")]
        url_cols = [c for c in df.columns if c.endswith("_url")]
        export_cols = [c for c in df.columns if c not in price_cols + url_cols]

        # EXTRA oszlopok (Excel számolja)
        extra_cols = ["min_price", "recommended_price"]

        all_cols = export_cols + price_cols + extra_cols

        # --- HEADER ---
        for col_idx, col in enumerate(all_cols):
            worksheet.write(0, col_idx, col)

        col_index_map = {col: idx for idx, col in enumerate(all_cols)}

        # --- ADATOK ---
        for row in range(len(df)):
            excel_row = row + 1

            # --- SIMA ADATOK ---
            for col in export_cols:
                val = df.iloc[row][col]
                col_idx = col_index_map[col]

                if pd.isna(val):
                    worksheet.write_blank(excel_row, col_idx, None)
                elif isinstance(val, (int, float)):
                    worksheet.write_number(excel_row, col_idx, float(val))
                else:
                    worksheet.write(excel_row, col_idx, str(val))

            # --- PRICE + LINK ---
            for col in price_cols:
                price = df.iloc[row][col]
                url_col = col.replace("_price", "_url")
                url = df.iloc[row].get(url_col)

                col_idx = col_index_map[col]

                if pd.isna(price):
                    continue

                if pd.notna(url):
                    worksheet.write_formula(
                        excel_row,
                        col_idx,
                        f'=HYPERLINK("{url}","{int(price)}")'
                    )
                else:
                    worksheet.write_number(excel_row, col_idx, float(price))

            # --- MIN PRICE (Excel formula) ---
            price_cells = [
                xl.xl_rowcol_to_cell(excel_row, col_index_map[c])
                for c in price_cols
            ]

            min_formula = f"=MIN({','.join(price_cells)})"

            worksheet.write_formula(
                excel_row,
                col_index_map["min_price"],
                min_formula
            )

            # --- RECOMMENDED PRICE (egyszerűsített logika Excelben) ---
            min_cell = xl.xl_rowcol_to_cell(excel_row, col_index_map["min_price"])
            purchase_col = "m_pp"

            if purchase_col in col_index_map:
                purchase_cell = xl.xl_rowcol_to_cell(excel_row, col_index_map[purchase_col])

                rec_formula = (
                    f"=IF({min_cell}=\"\", \"\", "
                    f"MAX({min_cell}*0.99, {purchase_cell}*1.1))"
                )
            else:
                rec_formula = f"={min_cell}*0.99"

            worksheet.write_formula(
                excel_row,
                col_index_map["recommended_price"],
                rec_formula
            )

        # --- CONDITIONAL FORMATTING ---

        # min price highlight (bold)
        for col in price_cols:
            col_idx = col_index_map[col]

            worksheet.conditional_format(
                1, col_idx,
                len(df), col_idx,
                {
                    "type": "formula",
                    "criteria": f"={xl.xl_rowcol_to_cell(1, col_idx)}="
                                f"{xl.xl_rowcol_to_cell(1, col_index_map['min_price'])}",
                    "format": workbook.add_format({"bold": True})
                }
            )

        # piros: ha olcsóbb mint saját ár
        if "shop0_p" in col_index_map:
            my_col = col_index_map["shop0_p"]

            for col in price_cols:
                col_idx = col_index_map[col]

                worksheet.conditional_format(
                    1, col_idx,
                    len(df), col_idx,
                    {
                        "type": "formula",
                        "criteria": f"={xl.xl_rowcol_to_cell(1, col_idx)}"
                                    f"<{xl.xl_rowcol_to_cell(1, my_col)}",
                        "format": workbook.add_format({"font_color": "red"})
                    }
                )

        # --- EXTRÁK ---
        worksheet.freeze_panes(1, 0)
        worksheet.autofilter(0, 0, len(df), len(all_cols) - 1)

        writer.close()
        output.seek(0)

        return output

    def create_amazon_pricing_excel(self, df):

        from io import BytesIO
        import xlsxwriter.utility as xl

        output = BytesIO()
        writer = pd.ExcelWriter(output, engine="xlsxwriter")

        workbook = writer.book

        # =========================
        # 📊 CONTROL SHEET
        # =========================
        ctrl = workbook.add_worksheet("Controls")

        ctrl.write("A1", "Min margin %")
        ctrl.write("B1", 0.10)

        ctrl.write("A2", "Undercut %")
        ctrl.write("B2", -0.01)

        ctrl.write("A3", "Round to 9")
        ctrl.write("B3", 1)

        # =========================
        # 📈 PRICE SHEET
        # =========================
        ws = workbook.add_worksheet("Prices")
        writer.sheets["Prices"] = ws

        price_cols = [c for c in df.columns if c.endswith("_price")]
        url_cols = [c for c in df.columns if c.endswith("_url")]
        export_cols = [c for c in df.columns if c not in price_cols + url_cols]

        extra_cols = ["min_price", "buybox_price", "recommended_price", "profit"]

        all_cols = export_cols + price_cols + extra_cols

        col_map = {c: i for i, c in enumerate(all_cols)}

        # --- HEADER ---
        for col, idx in col_map.items():
            ws.write(0, idx, col)

        # =========================
        # 📦 ADATOK
        # =========================
        for r in range(len(df)):
            row = r + 1

            # sima mezők
            for col in export_cols:
                val = df.iloc[r][col]
                c = col_map[col]

                if pd.isna(val):
                    ws.write_blank(row, c, None)
                elif isinstance(val, (int, float)):
                    ws.write_number(row, c, float(val))
                else:
                    ws.write(row, c, str(val))

            # price + hyperlink
            for col in price_cols:
                price = df.iloc[r][col]
                url = df.iloc[r].get(col.replace("_price", "_url"))

                c = col_map[col]

                if pd.isna(price):
                    continue

                if pd.notna(url):
                    ws.write_formula(row, c, f'=HYPERLINK("{url}","{int(price)}")')
                else:
                    ws.write_number(row, c, float(price))

            # =========================
            # 🧮 MIN PRICE
            # =========================
            price_cells = [
                xl.xl_rowcol_to_cell(row, col_map[c])
                for c in price_cols
            ]

            min_formula = f"=MIN({','.join(price_cells)})"

            ws.write_formula(row, col_map["min_price"], min_formula)

            min_cell = xl.xl_rowcol_to_cell(row, col_map["min_price"])

            # =========================
            # 🏆 BUY BOX (undercut)
            # =========================
            buybox_formula = f"={min_cell}*(1+Controls!B2)"
            ws.write_formula(row, col_map["buybox_price"], buybox_formula)

            buybox_cell = xl.xl_rowcol_to_cell(row, col_map["buybox_price"])

            # =========================
            # 💰 RECOMMENDED PRICE
            # =========================
            purchase_cell = xl.xl_rowcol_to_cell(row, col_map["m_pp"])

            rec_formula = (
                f"=MAX("
                f"{buybox_cell},"
                f"{purchase_cell}*(1+Controls!B1)"
                f")"
            )

            # 9-re végződés (Excel hack 😄)
            rec_formula = (
                f"=IF(Controls!B3=1,"
                f"INT({rec_formula}/10)*10+9,"
                f"{rec_formula})"
            )

            ws.write_formula(row, col_map["recommended_price"], rec_formula)

            rec_cell = xl.xl_rowcol_to_cell(row, col_map["recommended_price"])

            # =========================
            # 📈 PROFIT
            # =========================
            profit_formula = f"={rec_cell}-{purchase_cell}"
            ws.write_formula(row, col_map["profit"], profit_formula)

        # =========================
        # 🎨 CONDITIONAL FORMATTING
        # =========================

        # profit < 0 → piros
        ws.conditional_format(
            1, col_map["profit"],
            len(df), col_map["profit"],
            {
                "type": "cell",
                "criteria": "<",
                "value": 0,
                "format": workbook.add_format({"font_color": "red"})
            }
        )

        # recommended = buybox → zöld (nyerő ár)
        ws.conditional_format(
            1, col_map["recommended_price"],
            len(df), col_map["recommended_price"],
            {
                "type": "formula",
                "criteria": f"={xl.xl_rowcol_to_cell(1, col_map['recommended_price'])}="
                            f"{xl.xl_rowcol_to_cell(1, col_map['buybox_price'])}",
                "format": workbook.add_format({"font_color": "green", "bold": True})
            }
        )

        # =========================
        # EXTRÁK
        # =========================
        ws.freeze_panes(1, 0)
        ws.autofilter(0, 0, len(df), len(all_cols) - 1)

        writer.close()
        output.seek(0)

        return output