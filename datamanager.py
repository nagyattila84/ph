import os
import pandas as pd
from supabase import create_client, Client

# @title
class SupaBaseDataManager:
    def __init__(self, url, key):
        try:
            self.client = create_client(url, key)
            print("Successfully connected to Supabase.")
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            self.client = None

    def get_view(self, view):
        response = self.client.table(view) \
            .select("*") \
            .execute()

        return pd.DataFrame(response.data)

    # UPSERT - adatbázis ellenőrzi, van-e ilyen webshop_id+sku+scraped_date
    #    ha NINCS ->beilleszti
    #    ha VAN -> felülírja, de nem duplikálja 
    def save_raw_products_prices(self, df):

        df = df.replace({np.nan: None})

        try:
            data = df.to_dict(orient="records")

            response = self.client.table("raw_products") \
                .upsert(data, on_conflict="webshop_id,sku,scraped_date") \
                .execute()

            inserted_count = len(response.data) if response.data else 0

            return {
                "success": True,
                "count": inserted_count,
                "error": None
            }

        except Exception as e:
            return {
                "success": False,
                "count": 0,
                "error": str(e)
            }

    def count_rows(self, table_name: str, filters: dict = None):
        if not self.client:
            print("Supabase client not initialized.")
            return None

        query = self.client.table(table_name).select("*", count="exact")

        if filters:
            query = query.match(filters)

        response = query.execute()

        return response.count

    def read_data(
        self,
        table_name: str,
        query: dict = None,
        neq_filters: dict = None,
        in_filters: dict = None,
        is_null: list = None,
        not_null: list = None,
        like_filters: dict = None,
        columns: list = None,
        order_by: str = None,
        descending: bool = False,
        batch_size: int = 800
    ):

        if not self.client:
            print("SupaBase client not initialized.")
            return pd.DataFrame()

        try:
            select_cols = "*"
            if columns:
                select_cols = ",".join(columns)

            all_data = []
            start = 0

            while True:

                qb = self.client.table(table_name).select(select_cols)

                # = feltételek
                if query:
                    qb = qb.match(query)

                # != feltételek
                if neq_filters:
                    for col, value in neq_filters.items():
                        qb = qb.neq(col, value)

                # IN feltételek
                if in_filters:
                    for col, values in in_filters.items():
                        qb = qb.in_(col, values)

                # LIKE feltételek
                if like_filters:
                    for col, value in like_filters.items():
                        qb = qb.ilike(col, f"%{value}%")

                # IS NULL
                if is_null:
                    if isinstance(is_null, str):
                        is_null = [is_null]
                    for col in is_null:
                        qb = qb.is_(col, None)

                # IS NOT NULL
                if not_null:
                    if isinstance(not_null, str):
                        not_null = [not_null]
                    for col in not_null:
                        qb = qb.not_.is_(col, None)

                # ORDER BY
                if order_by:
                    qb = qb.order(order_by, desc=descending)

                # BATCH RANGE
                qb = qb.range(start, start + batch_size - 1)

                response = qb.execute()
                data = response.data

                if not data:
                    break

                all_data.extend(data)

                if len(data) < batch_size:
                    break

                start += batch_size

            print(f"Successfully read {len(all_data)} rows from '{table_name}'.")
            return pd.DataFrame(all_data)

        except Exception as e:
            print(f"Error reading data from '{table_name}': {e}")
            return pd.DataFrame()

    def read_webshops_from_db(self, table_name="webshops"):
        """Reads webshops from the specified Supabase table and returns a list of Webshop instances."""
        data = self.read_data(table_name)
        if not data:
            return []

        webshops = []
        for item in data:
            try:
                webshop = Webshop(
                    id=int(item.get('id')) if item.get('id') is not None else 0,
                    name=item.get('name') if item.get('name') is not None else '',
                    base_url=item.get('base_url') if item.get('base_url') is not None else '',
                    search_url=item.get('search_url') if item.get('search_url') is not None else '',
                    company=item.get('company') if item.get('company') is not None else '',
                    product_container_selector=item.get('product_container_selector') if item.get('product_container_selector') is not None else '',
                    product_container_class=item.get('product_container_class') if item.get('product_container_class') is not None else '',
                    name_selector=item.get('name_selector') if item.get('name_selector') is not None else '',
                    name_class=item.get('name_class') if item.get('name_class') is not None else '',
                    sku_selector=item.get('sku_selector'),
                    sku_class=item.get('sku_class'),
                    sku_attr=item.get('sku_attr'),
                    link_selector=item.get('link_selector') if item.get('link_selector') is not None else '',
                    link_class=item.get('link_class') if item.get('link_class') is not None else '',
                    price_selector=item.get('price_selector') if item.get('price_selector') is not None else '',
                    price_class=item.get('price_class') if item.get('price_class') is not None else '',
                    sale_price_selector=item.get('sale_price_selector'),
                    sale_price_class=item.get('sale_price_class')
                )
                webshops.append(webshop)
            except (ValueError, TypeError, KeyError) as e:
                print(f"Error creating Webshop object from data: {item}. Skipping. Error: {e}")
        return webshops

    def process_matches_batch(self, df, batch=300):

        try: 
            df = df.astype(object).where(pd.notnull(df), None)

            total_processed = 0

            for i in range(0, len(df), batch):
                batch_df = df.iloc[i : i + batch].copy()
                self.process_matches(batch_df)
                total_processed += len(batch_df)

            self.client.rpc("sync_raw_clusters").execute()
            self.client.rpc("sync_own_clusters").execute()

            return {
                "success": True,
                "count": total_processed
            }
        
        except Exception as e:
            return {
                "success": False,
                "count": 0,
                "error": str(e)
        }


    #df- result of matches in DataFrame with batch
    def process_matches(self, df):

        # ÚJ CLUSTEREK
        new_clusters = df[df["is_new_cluster"] == True]

        if not new_clusters.empty:

            insert_payload = []

            for _, row in new_clusters.iterrows():
                insert_payload.append({
                    "name": row["cluster_name"],
                    "webshop_id": row["webshop_id"]
                })

            res = self.client.table("clusters").insert(insert_payload).execute()

            returned = res.data

            # (cluster_name, webshop_id) → id mapping
            mapping = {
                (r["name"], r["webshop_id"]): r["id"]
                for r in returned
            }

            # visszatöltjük DF-be
            for i in df.index:
                if df.at[i, "is_new_cluster"]:
                    key = (df.at[i, "cluster_name"], df.at[i, "webshop_id"])
                    df.at[i, "cluster_id"] = mapping[key]

        # MATCH TABLE INSERT

        df["product_id"] = df["product_id"].astype("Int64")
        df["cluster_id"] = df["cluster_id"].astype("Int64")

        match_rows = []

        for _, row in df.iterrows():
            match_rows.append({
                "cluster_id": int(row["cluster_id"]),
                "product_id": int(row["product_id"]),
                "product_type": row["product_type"],
                "score": float(row["score"]) if pd.notna(row["score"]) else None
            })

        self.client.table("product_cluster_links").insert(match_rows).execute()

    def get_products_by_keyword(self, keyword):

        # matching clusters
        clusters = (
            self.client
            .table("clusters")
            .select("id,name")
            .ilike("name", f"%{keyword}%")
            .execute()
            .data
        )

        if not clusters:
            return pd.DataFrame(), pd.DataFrame()

        cluster_ids = [c["id"] for c in clusters]

        # links
        links = (
            self.client
            .table("product_cluster_links")
            .select("cluster_id,product_id,product_type,score")
            .in_("cluster_id", cluster_ids)
            .execute()
            .data
        )

        if not links:
            return pd.DataFrame(), pd.DataFrame()

        links_df = pd.DataFrame(links)

        # split
        own_ids = links_df[links_df.product_type == "own"]["product_id"].tolist()
        raw_ids = links_df[links_df.product_type == "raw"]["product_id"].tolist()

        # own products
        own = (
            self.client
            .table("own_products")
            .select("*")
            .in_("id", own_ids)
            .execute()
            .data
        )

        # raw products
        raw = (
            self.client
            .table("raw_products")
            .select("*")
            .in_("id", raw_ids)
            .execute()
            .data
        )
        return pd.DataFrame(own), pd.DataFrame(raw)

    def delete_all_clusters(self):
        try:
            response = self.client.rpc("reset_clusters").execute()
            if response.data is not None:
                return "Cluster adatok törölve."

            return "A művelet lefutott, de nem érkezett vissza adat."

        except Exception as e:
            print("RPC ERROR:", e)
            return f"Hiba történt: {e}"

    def delete_all_raw_products(self):
        try:
            response = self.client.table("raw_products") \
                .delete() \
                .neq("id", 99) \
                .execute()

            deleted_count = len(response.data) if response.data else 0

            return f"{deleted_count} raw product törölve."

        except Exception as e:
            return f"Hiba történt: {e}"
