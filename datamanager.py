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


    # UPSERT - adatbázis ellenőrzi, van-e ilyen webshop_id+sku+scraped_date
    #    ha NINCS ->beilleszti
    #    ha VAN -> felülírja, de nem duplikálja 
    def save_raw_products_prices(self, df):

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

    #csak 1000 rekordig működik
    def read_data(
        self,
        table_name: str,
        query: dict = None,
        columns: list = None,
        order_by: str = None,
        descending: bool = False
        ):
        # Reads data from a specified Supabase table (extended)

        if not self.client:
            print("SupaBase client not initialized. Cannot read data.")
            return None

        try:
            # oszlopok
            select_cols = "*"
            if columns:
                select_cols = ",".join(columns)

            qb = self.client.table(table_name).select(select_cols)

            # where (régi query param megmarad!)
            if query:
                qb = qb.match(query)

            # order by (új)
            if order_by:
                qb = qb.order(order_by, desc=descending)

            response = qb.execute()

            print(f"Successfully read data from table '{table_name}'.")
            return pd.DataFrame(response.data)

        except Exception as e:
            print(f"Error reading data from Supabase table '{table_name}': {e}")
            return None

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

        df = df.astype(object).where(pd.notnull(df), None)

        for i in range(0, len(df), batch):
            batch_df = df.iloc[i : i + batch].copy()
            self.process_matches(batch_df)

        print("All batches processed.")

        self.client.rpc("sync_raw_clusters").execute()
        self.client.rpc("sync_own_clusters").execute()

        print("Clusters synced.")

    #df- result of matches in DataFrame with batch
    def process_matches(self, df):

        # ÚJ CLUSTEREK
        new_clusters = df[df["is_new_cluster"] == True]

        if not new_clusters.empty:

            insert_payload = []

            for _, row in new_clusters.iterrows():
                insert_payload.append({
                    "name": row["cluster_name"]
                })

            res = self.client.table("clusters").insert(insert_payload).execute()

            returned = res.data

            # cluster_name → id mapping
            mapping = {
                r["name"]: r["id"]
                for r in returned
            }

            # visszatöltjük DF-be
            for i in df.index:
                if df.at[i, "is_new_cluster"]:
                    df.at[i, "cluster_id"] = mapping[df.at[i, "cluster_name"]]

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

        print(f"Saved {len(match_rows)} matches.")

    def get_clusters(self, keyword):
        kw = keyword.lower()

        response = (
            self.client
            .table("clusters")
            .select("*")
            .ilike("name", f"%{kw}%")
            .execute()
        )

        return pd.DataFrame(response.data)

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

