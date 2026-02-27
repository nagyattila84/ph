from datamanager import SupaBaseDataManager

class Statistic:

    def __init__(self, url, key):
        self.dm = SupaBaseDataManager(url, key)

    def count_table_rows(self, table, filters=None):
        return self.dm.count_rows(table, filters)

    def get_webshop_product_stats(self, view):
        return dm.get_view("webshop_product_stats")

