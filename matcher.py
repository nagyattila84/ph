import re
import requests
import pandas as pd
from rapidfuzz import fuzz
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
                    "webshop_id": p["webshop_id"],
                    "product_name": p["name"],
                    "cluster_id": best_cluster["id"],
                    "cluster_name": best_cluster["name"],
                    "score": best_score,
                    "is_new_cluster": False
                })

          # HA NINCS TALÁLAT -> ÚJ CLUSTER
          ##kiveszük, ha wenshoponként kerül be, akkor nem szükséges!!
          else:

            results.append({
                "product_id": p["id"],
                "product_type": product_type,
                "webshop_id": p["webshop_id"],
                "cluster_id": None,
                "score": None,
                "is_new_cluster": True,
                "cluster_name": p["name"]
            })

        return pd.DataFrame(results)

#**********************
#    RAPID FUZZ
#**********************
class RapidClusterMatcher:

    def __init__(self, threshold=85):
        self.threshold = threshold


    # ---------------- NORMALIZÁLÁS ---------------- #

    def normalize(self, text):
        text = str(text).lower()
        text = re.sub(r"[^\w\s]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text


    def extract_numbers(self, text):
        return set(re.findall(r"\d+", str(text)))


    def prepare_df(self, df):

        df = df.copy()
        df["norm_name"] = df["name"].apply(self.normalize)
        df["nums"] = df["name"].apply(self.extract_numbers)

        return df


    # ---------------- SCORE ---------------- #

    def score(self, a, b):
        #return fuzz.token_sort_ratio(a, b)

        base = fuzz.token_set_ratio(a, b)
        alt  = fuzz.partial_ratio(a, b)
        score = (base * 0.7 + alt * 0.3)

        return score

    # ---------------- CLUSTER INDEX ---------------- #

    def build_index(self, clusters_df):

        clusters = clusters_df.to_dict("records")

        index = {"__all__": clusters}

        for c in clusters:
            for num in c["nums"]:
                index.setdefault(num, []).append(c)

        return index


    # ---------------- FIND BEST ---------------- #

    def find_best_match(self, product, index):

        best_cluster = None
        best_score = 0

        # jelöltek szám index alapján, de ne kizárólagos legyen
        candidate_clusters = index["__all__"]

        for c in candidate_clusters:

            base_score = fuzz.token_sort_ratio(
                product["norm_name"],
                c["norm_name"]
            )

            nums_p = product["nums"]
            nums_c = c["nums"]

            # ---------------- SOFT NUMBER LOGIC ---------------- #

            if nums_p and nums_c:

                overlap = nums_p & nums_c

                if overlap:
                    base_score += 5   # kis boost
                else:
                    base_score -= 10  # büntetés, de nem kizárás

            elif nums_p or nums_c:
                base_score -= 5       # enyhe büntetés

            final_score = max(0, min(base_score, 100))

            if final_score > best_score:
                best_score = final_score
                best_cluster = c

        if best_score >= self.threshold:
            return best_cluster, best_score

        return None, best_score


    # ---------------- MAIN MATCH ---------------- #

    def match_products(self, products_df, clusters_df, th=None):

        if th:
            self.threshold = th

        if clusters_df is None or clusters_df.empty:
            clusters_df = pd.DataFrame(columns=["id", "name"])

        products_df = self.prepare_df(products_df)
        clusters_df = self.prepare_df(clusters_df)

        index = self.build_index(clusters_df)

        results = []

        for _, p in products_df.iterrows():

            product_type = "own" if p["webshop_id"] == 0 else "raw"

            best_cluster, best_score = self.find_best_match(p, index)

            if best_cluster:

                results.append({
                    "product_id": p["id"],
                    "product_type": product_type,
                    "webshop_id": p["webshop_id"],
                    "product_name": p["name"],
                    "cluster_id": best_cluster["id"],
                    "cluster_name": best_cluster["name"],
                    "score": best_score,
                    "is_new_cluster": False
                })

            else:

                results.append({
                    "product_id": p["id"],
                    "product_type": product_type,
                    "webshop_id": p["webshop_id"],
                    "cluster_id": None,
                    "score": None,
                    "is_new_cluster": True,
                    "cluster_name": p["name"]
                })

        return pd.DataFrame(results)