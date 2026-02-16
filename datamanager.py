import os
import pandas as pd
from supabase import create_client, Client


# @title
class SupaBaseDataManager:
  def __init__(self):
      SUPABASE_URL='https://rteebdpadwkwxvbvnmje.supabase.co'
      SUPABASE_KEY='sb_publishable_6VpTeoncxJQtnmzUds32qw_CUITQ6_2'
      try:
          self.client = create_client(SUPABASE_URL, SUPABASE_KEY)
          print("Successfully connected to Supabase.")
      except Exception as e:
          print(f"Error connecting to Supabase: {e}")
          self.client = None

  def insert_products_from_df(self, df: pd.DataFrame):
          #Upload scraped products from DataFrame into Supabase.

          if df.empty:
              print("⚠️ DataFrame is empty – nothing to upload.")
              return

          now = datetime.utcnow().isoformat()

          records = []

          for _, row in df.iterrows():
              records.append({
                  "webshop_id": row.get("webshop_id"),
                  "sku": row.get("sku"),
                  "name": row.get("name"),
                  "url": row.get("url"),
                  "price": row.get("price"),
                  "sale_price": row.get("price"),
                  "scraped_date": now
              })

          # batch insert
          result = self.client.table("raw_products").insert(records).execute()

          print(f"✅ Uploaded {len(records)} products.")
          return result

  def read_all(self, table_name: str, batch_size=500):

    all_rows = []
    offset = 0

    while True:

        response = (
            self.client
            .table(table_name)
            .select("*")
            .range(offset, offset + batch_size - 1)
            .execute()
        )

        data = response.data

        if not data:
            break

        all_rows.extend(data)

        offset += batch_size

    return pd.DataFrame(all_rows)

  #csak 1000 rekordig működik
  def read_data(self, table_name: str, query: dict = None):
      #Reads data from a specified Supabase table.
      if not self.client:
          print("SupaBase client not initialized. Cannot read data.")
          return None
      try:
          if query:
              response = self.client.table(table_name).select("*").match(query).execute()
          else:
              response = self.client.table(table_name).select("*").execute()
          print(f"Successfully read data from table '{table_name}'.")
          return response.data
      except Exception as e:
          print(f"Error reading data from Supabase table '{table_name}': {e}")
          return None

  def write_data(self, table_name: str, data: list):
      """Writes data to a specified Supabase table."""
      if not self.client:
          print("SupaBase client not initialized. Cannot write data.")
          return None
      try:
          response = self.client.table(table_name).insert(data).execute()
          print(f"Successfully wrote data to table '{table_name}'.")
          return response.data
      except Exception as e:
          print(f"Error writing data to Supabase table '{table_name}': {e}")
          return None

  def read_products_from_db(self, table_name="raw_products", query: dict = None):
      """Reads products from the specified Supabase table and returns a list of Product instances."""
      data = self.read_data(table_name, query)
      if not data:
          return []

      products = []
      for item in data:
          try:
              # Ensure all fields expected by Product dataclass are handled, with type conversion
              product = Product(
                  id=int(item.get('id')) if item.get('id') is not None else 0, # Assuming ID cannot be None, default to 0 or handle as Optional
                  webshop_id=int(item.get('webshop_id')) if item.get('webshop_id') is not None else 0,
                  sku=item.get('sku') if item.get('sku') is not None else '',
                  name=item.get('name') if item.get('name') is not None else '',
                  url=item.get('url') if item.get('url') is not None else '',
                  price=int(item.get('price')) if item.get('price') is not None else 0,
                  sale_price=int(item.get('sale_price')) if item.get('sale_price') is not None else 0,
                  scraped_date=item.get('scraped_date') if item.get('scraped_date') is not None else ''
              )
              products.append(product)
          except (ValueError, TypeError, KeyError) as e:
              print(f"Error creating Product object from data: {item}. Skipping. Error: {e}")
      return products

  def read_webshops_from_db(self, table_name="webshops") -> list[Webshop]:
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

  def read_own_products_from_db(self, table_name="own_products") -> list[OwnProduct]:
      """Reads own products from the specified Supabase table and returns a list of OwnProduct instances."""
      data = self.read_data(table_name)
      if not data:
          return []

      own_products = []
      for item in data:
          try:
              own_product = OwnProduct(
                  id=int(item.get('id')) if item.get('id') is not None else 0,
                  webshop_id=int(item.get('webshop_id')) if item.get('webshop_id') is not None else 0,
                  sku=item.get('sku') if item.get('sku') is not None else '',
                  name=item.get('name') if item.get('name') is not None else '',
                  url=item.get('url'), # URL can be None
                  price=int(item.get('price')) if item.get('price') is not None else 0,
                  price2=int(item.get('price2')) if item.get('price2') is not None else 0,
                  price3=int(item.get('price3')) if item.get('price3') is not None else 0,
                  price4=int(item.get('price4')) if item.get('price4') is not None else 0,
                  price5=int(item.get('price5')) if item.get('price5') is not None else 0,
                  price6=int(item.get('price6')) if item.get('price6') is not None else 0,
                  purchase_price=int(item.get('purchase_price')) if item.get('purchase_price') is not None else 0,
                  scraped_date=item.get('scraped_date') if item.get('scraped_date') is not None else ''
              )
              own_products.append(own_product)
          except (ValueError, TypeError, KeyError) as e:
              print(f"Error creating OwnProduct object from data: {item}. Skipping. Error: {e}")
      return own_products

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

  def load_clusters_by_keyword(self, keyword):

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


