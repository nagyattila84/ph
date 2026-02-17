import pandas as pd
from datamanager import SupaBaseDataManager

class PriceAnalyst:

    def __init__(self, dm):
        self.dm = dm

    def get_cluster_price_view(self, keyword=None):
        clusters = self.dm.get_clusters(keyword)
        own, raw = self.dm.get_products_by_keyword(keyword)
        links = self.dm.read_data("product_cluster_links")
        shops = self.dm.read_data("webshops")

        df = pd.concat([
            own.assign(source="own"),
            raw.assign(source="supplier")
        ])
        
        df = own.merge(
            links,
            left_on="id",
            right_on="product_id",
            how="left"
        )
    
        df = df.merge(
            raw,
            left_on="product_id",
            right_on="id",
            how="left",
            suffixes=("_own", "_raw")
        )
    
        df = df.merge(
            clusters[["id", "name"]],
            left_on="cluster_id",
            right_on="id",
            how="left"
        )
    
        df.rename(columns={"name": "cluster_name"}, inplace=True)
    
        if keyword:
            df = df[df["cluster_name"].str.contains(keyword, case=False, na=False)]
    
        return df
