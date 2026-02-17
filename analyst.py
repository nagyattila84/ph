import pandas as pd

class PriceAnalyst:

    def __init__(self, dm):
        self.dm = dm

    def get_cluster_price_view(self, keyword=None):
        clusters = self.dm.get_clusters()
        own = self.dm.get_own_products(keyword)
        raw = self.dm.get_raw_products(keyword)
        links = self.dm.get_product_cluster_links()
        shops = self.dm.get_webshops()

        df = pd.concat([
            own.assign(source="own"),
            raw.assign(source="supplier")
        ])

        df = df.merge(links, on="product_id", how="left")
        df = df.merge(clusters[["id", "name"]], left_on="cluster_id", right_on="id", how="left")
        df = df.merge(shops, on="webshop_id", how="left")

        df.rename(columns={
            "name": "cluster_name",
            "price": "price",
            "shop_name": "shop"
        }, inplace=True)

        return df[[
            "cluster_id",
            "cluster_name",
            "product_id",
            "price",
            "shop",
            "source"
        ]]
