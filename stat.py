from datamanager import SupaBaseDataManager

class Statistic():

    def count_shops(self, filters=None):
        return self.count_rows("webshops", filters)

    def count_clusters(self, filters=None):
        return self.count_rows("clusters", filters)

    def count_own_products(self, filters=None):
        return self.count_rows("own_product", filters)

    def count_raw_products(self, filters=None):
        return self.count_rows("raw_product", filters)
