import re
import requests
from bs4 import BeautifulSoup
import pandas as pd
from difflib import SequenceMatcher
from datetime import datetime

#csoportosítás optimalizált!
class ProductMatcher:

    def __init__(self, threshold=80):
        self.threshold = threshold
        self.next_cluster_id = 1

    # Text normalizálás
    def normalize(self, text):
        text = text.lower()
        text = re.sub(r'[^a-z0-9 ]', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def extract_numbers(self, text):
        return set(re.findall(r'\d+', str(text)))

    # ---------------- PREPARE ---------------- #
    def prepare_df(self, df):

        df = df.copy()

        df["norm_name"] = df["name"].apply(self.normalize)
        df["nums"] = df["name"].apply(self.extract_numbers)

        return df

    # Token sort ratio
    def token_sort_ratio(self, p, c):

        a_tokens = sorted(p.split())
        b_tokens = sorted(c.split())

        a_sorted = " ".join(a_tokens)
        b_sorted = " ".join(b_tokens)

        return SequenceMatcher(None, a_sorted, b_sorted).ratio() * 100

    # Szám egyezés
    def number_overlap(self, a, b):

        nums_a = set(re.findall(r'\d+', a))
        nums_b = set(re.findall(r'\d+', b))

        return len(nums_a & nums_b)

    # Végső score
    def score(self, name_p, name_c):

        base = self.token_sort_ratio(name_p, name_c)

        # szám boost
        if self.number_overlap(name_p, name_c) > 0:
            base += 5

        return min(base, 100)

    # ---------------- MATCH SINGLE ---------------- #
    def find_best_match(self, product, clusters):

        best_cluster = None
        best_score = 0

        for c in clusters:

            # FAST PREFILTER → szám egyezés
            if product["nums"] and c["nums"]:
                if not product["nums"] & c["nums"]:
                    continue

            score = self.token_sort_ratio(product["norm_name"], c["norm_name"])

            if score > best_score:
                best_score = score
                best_cluster = c

        if best_score >= self.threshold:
            return best_cluster, round(best_score, 2)

        return None, best_score

    # Tömeges párosítás
    def match_products(self, products_df, clusters_df, th = None):
        if th:
            self.threshold = th
        product_type = None

        if clusters_df is None or clusters_df.empty:
            clusters_df = pd.DataFrame(columns=["id", "name"])

        if not clusters_df.empty:
            self.next_cluster_id = clusters_df["id"].max() + 1

        products_df = self.prepare_df(products_df)
        clusters_df = self.prepare_df(clusters_df)

        results = []
        created_clusters = 0

        for _, p in products_df.iterrows():

          best_score = 0
          best_cluster = None

          if p["webshop_id"] == 0:
              product_type = "own"
          else:
              product_type = "raw"

          for _, c in clusters_df.iterrows():

              s = self.score(p["norm_name"], c["norm_name"])

              if s > best_score:
                  best_score = s
                  best_cluster = c

          # HA VAN TALÁLAT
          if best_cluster is not None and best_score >= self.threshold:

              results.append({
                    "product_id": p["id"],
                    "product_type": product_type,
                    "cluster_id": best_cluster["id"],
                    "score": best_score,
                    "is_new_cluster": False
                })

          # HA NINCS TALÁLAT -> ÚJ CLUSTER
          ##kiveszük, ha wenshoponként kerül be, akkor nem szükséges!!
          else:

            results.append({
                "product_id": p["id"],
                "product_type": product_type,
                "cluster_id": None,
                "score": None,
                "is_new_cluster": True,
                "cluster_name": p["name"]
            })

        return pd.DataFrame(results)