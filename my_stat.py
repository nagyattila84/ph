from datamanager import SupaBaseDataManager

class Statistic:
    dm = SupaBaseDataManager()

    def count_shops(filters=None):
        return dm.count_rows("webshops", filters)

    def count_clusters(filters=None):
        return dm.count_rows("clusters", filters)

    def count_own_products(filters=None):
        return dm.count_rows("own_product", filters)

    def count_raw_products(filters=None):
        return dm.count_rows("raw_product", filters)
