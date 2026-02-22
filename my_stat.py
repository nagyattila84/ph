from datamanager import SupaBaseDataManager

class Statistic:

    def __init__(self):
        self.dm = SupaBaseDataManager()

    def count_shops(self, filters=None):
        return self.dm.count_rows("webshops", filters)

    def count_clusters(self, filters=None):
        return self.dm.count_rows("clusters", filters)

    def count_own_products(self, filters=None):
        return self.dm.count_rows("own_products", filters)

    def count_raw_products(self, filters=None):
        return self.dm.count_rows("raw_products", filters)

