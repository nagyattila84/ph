import streamlit as st
from werkzeug.security import check_password_hash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datamanager import SupaBaseDataManager
from scraper import Scraper
from matcher import *
from analyst import PriceAnalyst
from my_stat import Statistic

users = st.secrets["users"]
dm = SupaBaseDataManager(st.secrets.supabase.url, st.secrets.supabase.key)
sc = Scraper()
pm = ProductMatcher()
rcm = RapidClusterMatcher()
stat = Statistic(st.secrets.supabase.url, st.secrets.supabase.key)

st.set_page_config(page_title="PriceHunter", layout="wide")

# ============= SESSION INIT ===============
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ================= LOGIN =================
def login_page():   
    
    c1, c2, c3 = st.columns(3)
    c2.image("Images/PriceHunter-logo-fekvő.png", width=300, use_container_width=False)

    c2.title("Bejelentkezés")
    username = c2.text_input("Felhasználónév", width=300)
    password = c2.text_input("Jelszó", type="password", width=300)

    if c2.button("Belépés"):
        ok = False
    
        if username in users:
            try:
                ok = check_password_hash(users[username], password)            
            except Exception as e:
                c2.write(e)
    
        if ok:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.rerun()
        else:
            c2.error("Hibás felhasználónév vagy jelszó")

# ============== PAGE ELEMENTS ==============

#saját elem: tábla neve expand boxban + elemek száma, legördítés után lapozható formában 
def ph_table(table_name, table_df):
    label_name = table_name + " Elemszám: " + str(len(table_df))
    expander = st.expander(label_name, icon=":material/table_eye:")
    expander.table(table_df)

def ph_matched_result_view(st, matched_df):
    total = len(matched_df)
    matched_count = len(matched_df[matched_df["is_new_cluster"] == False])
    new_cluster_count = len(matched_df[matched_df["is_new_cluster"] == True])

    col1, col2, col3 = st.columns(3)

    col1.metric("📦 Feldolgozott termék", total)
    col2.metric("🔗 Clusterhez kapcsolva", matched_count)
    col3.metric("🆕 Új cluster szükséges", new_cluster_count)

    if total > 0:
        match_ratio = round(matched_count / total * 100, 1)
        st.info(f"Match arány: {match_ratio}%")
    
    with st.expander("🔗 Kapcsolt termékek"):
        st.dataframe(
            matched_df[matched_df["is_new_cluster"] == False]
        )
    if st.button("🔗 Kapcsolt termékek MENTÉSE", type="primary"):
        result = dm.process_matches_batch(
            matched_df[matched_df["is_new_cluster"] == False]
        )
        if result["success"]:
            st.success(f"✅ {result['count']} termék sikeresen mentve.")
        else:
            st.error(f"Sikertelen mentés.")

    with st.expander("🆕 Új clusterre váró termékek"):
        st.dataframe(
            matched_df[matched_df["is_new_cluster"] == True]
        )
    if st.button("🆕 Clusterek MENTÉSE", type="primary"):
        result = dm.process_matches_batch(matched_df[matched_df["is_new_cluster"] == True])
        if result["success"]:
            st.success(f"✅ {result['count']} termék sikeresen mentve.")
        else:
            st.error(result["error"])

# ================= PAGES =================
def page_dashboard():
    
    st.header("📊 Dashboard")
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Webshopok", stat.count_table_rows("webshops"))
    c2.metric("Clusterek", stat.count_table_rows("clusters"))
    c3.metric("Saját termékek", stat.count_table_rows("own_products"))
    c4.metric("Idegen termékek", stat.count_table_rows("raw_products"))

    df = pd.DataFrame({
        "type": ["Saját termék", "Idegen termék"],
        "count": [stat.count_table_rows("own_products"), stat.count_table_rows("raw_products")]
    })

    fig = px.pie(df, names="type", values="count", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    st.bar_chart(dm.get_view("webshop_product_stats"), x="name", y="product_count", x_label="Webáruház", y_label="Termék", sort="-product_count")

def page_search():
    dm = SupaBaseDataManager(st.secrets.supabase.url, st.secrets.supabase.key)
    pa = PriceAnalyst(dm)
    st.title("Ár összehasonlító")    
    keyword = st.text_input("Keresőszó")
    
    if keyword:
        #own_df, raw_df = dm.get_products_by_keyword(keyword)
        df = pa.get_cluster_price_view(keyword)
    
        st.subheader("Termékek")
        st.dataframe(df)

def page_price_setter():
    st.title("💵 ÁRAK ELEMZÉSE")

    tab1, tab2, tab3 = st.tabs(["Táblázat", "Grafikon", "blabla"])

    with tab1:
        page_visual3()
    
    with tab2:
        page_visual()

    with tab3:
        page_visual2()

def page_visual3():  
    st.title("Ár összehasonlító") 
    own_df, raw_df = dm.get_products_by_keyword("pgv")
    df = raw_df.copy()

    # Min / Max termékenként
    df["min_price"] = df.groupby("cluster_id")["price"].transform("min")
    df["max_price"] = df.groupby("cluster_id")["price"].transform("max")
    
    # Normalizált pozíció (0–1)
    df["norm"] = (df["price"] - df["min_price"]) / (
        df["max_price"] - df["min_price"]
    ).fillna(0)

    #Termékek limitálása
    products = st.multiselect(
        "Termékek",
        df["cluster_id"].unique(),
        df["cluster_id"].unique()[:5]
    )
    df = df[df["cluster_id"].isin(products)]

    fig = go.Figure()

    for product in df["cluster_id"].unique():
        sub = df[df["cluster_id"] == product]
    
        # Számegyenes (min → max)
        fig.add_trace(go.Scatter(
            x=[0, 1],
            y=[product, product],
            mode="lines",
            line=dict(width=2),
            showlegend=False
        ))
    
        # Pontok (webshop árak)
        fig.add_trace(go.Scatter(
            x=sub["norm"],
            y=[product]*len(sub),
            mode="markers",
            marker=dict(size=10),
            text=sub["webshop_id"],
            customdata=sub["price"],
            hovertemplate="%{text}<br>%{customdata} Ft",
            showlegend=False
        ))
    
    fig.update_layout(
        height=600,
        xaxis=dict(
            range=[-0.05, 1.05],
            tickvals=[0, 1],
            ticktext=["Min", "Max"]
        ),
        yaxis_title="",
        xaxis_title="Ár pozíció terméken belül"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def page_visual():
    dm = SupaBaseDataManager(st.secrets.supabase.url, st.secrets.supabase.key)
    st.title("Ár összehasonlító")   
 
    own_df, raw_df = dm.get_products_by_keyword("hunter")
    fig = px.strip(
        own_df,
        x="price",
        y="sku",
        color="webshop_id",
        orientation="h",
        hover_data=["name", "price4"]
    )
    
    fig.update_traces(jitter=0.3, marker=dict(size=10))
    
    fig.update_layout(
        height=600,
        showlegend=True,
        xaxis_title="Ár",
        yaxis_title=""
    )
    
    st.plotly_chart(fig, use_container_width=True)

def page_visual2():
    
    df = dm.read_data(
        table = "raw_products"
    )

    fig = go.Figure()
    st.title("Ár összehasonlító")   
 
    own_df, raw_df = dm.get_products_by_keyword("hunter")
    
    for product in raw_df["id"].unique():
        sub = raw_df[raw_df["id"] == product]
    
        fig.add_trace(go.Scatter(
            x=[sub.price.min(), sub.price.max()],
            y=[product, product],
            mode="lines",
            line=dict(width=2),
            showlegend=False
        ))
    
        fig.add_trace(go.Scatter(
            x=sub.price,
            y=[product]*len(sub),
            mode="markers",
            text=sub.webshop_id,
            hovertemplate="%{text}<br>%{x} Ft"
        ))
    
    st.plotly_chart(fig, use_container_width=True)

def page_controlpanel():
    
    st.title("📊 Vezérlőpult")

    #*****************
    # SAJÁT ÁRAK 
    #*****************
    st.space("medium")
    st.header("0. Saját termékadatok feltöltés")
    st.write("Az own_product táblába manuálisan kerülnek a saját termék adatok.")
    st.write("fejleszteni... kapcsolás a letöltött termékadatokhoz, cikkszám szerint.")

    #*****************
    # ÁRAK LETÖLTÉSE
    #*****************
    st.space("medium")
    st.header("1. Árak letöltése")
    st.write("Webáruházak kijelölése:")
            
    shops = dm.read_data("webshops", order_by="id", descending=False)    
   
    # hozzáadunk egy kijelölő oszlopot
    if "selector_shops" not in st.session_state:
        shops.insert(0, "selected", False)
        st.session_state.selector_shops = shops

    shops = st.data_editor(
        st.session_state.selector_shops,
        column_config={
            "selected": "Kiválasztva",
            "name": "Webáruház neve",
            "base_url": "Link",
            "company": "Cégnév"
        },
        use_container_width=False
    )

    with st.form("price_form"):

        keyword = st.text_input("Keresőszó")

        submitted = st.form_submit_button("🔍 Árak letöltése")

    if submitted and keyword:

        selected_shops = shops[shops["selected"]]

        with st.spinner("Árak letöltése folyamatban..."):
            price = sc.get_price_from_multi_webshop_df(selected_shops, keyword)
            downloaded_count = len(price)
        st.session_state.scraped_prices = price
        st.success(f"✅ {downloaded_count} termék sikeresen letöltve.")

    if "scraped_prices" in st.session_state:
        ph_table("Árak megtekintése", st.session_state.scraped_prices)
    
        if st.button("💾 Árak mentése adatbázisba", type="primary"):
            
            with st.spinner("Mentés folyamatban..."):
                result = dm.save_raw_products_prices(st.session_state.scraped_prices)

            if result["success"]:
                st.success(f"✅ {result['count']} termék sikeresen mentve.")
            else:
                st.error(f"❌ Hiba történt mentés közben:\n{result['error']}")
            del st.session_state.scraped_prices

    #*****************
    # SAJÁT TERMÉKEK PÁROSÍTÁSA
    #*****************
    st.space("medium")
    st.header("2.Saját termék párosítás")
    if st.button("Saját termékek betöltése"):
        st.session_state["own_products_without_cluster"] = dm.read_data(
            table_name="own_products",
            is_null=["cluster_id"]
        )
        ph_table("Saját termékek (cluster nélkül)", st.session_state["own_products_without_cluster"])

    if "own_products_without_cluster" in st.session_state:    
        if st.button("Saját termékek clusterezése"):
            clusters = dm.read_data("clusters")
            with st.spinner("Párosítás folyamatban..."):            

                matched_df = rcm.match_products(st.session_state["own_products_without_cluster"], clusters)
                dm.process_matches_batch(matched_df)
                st.header("SIKERES PÁROSÍTÁS")

                total = len(matched_df)
                matched_count = len(matched_df[matched_df["is_new_cluster"] == False])
                new_cluster_count = len(matched_df[matched_df["is_new_cluster"] == True])

                st.write("💎 Szép dashboard megjelenítés")
                col1, col2, col3 = st.columns(3)

                col1.metric("📦 Feldolgozott termék", total)
                col2.metric("🔗 Clusterhez kapcsolva", matched_count)
                col3.metric("🆕 Új cluster szükséges", new_cluster_count)

                st.write("🚀 Extra: százalékos arány")
                if total > 0:
                    match_ratio = round(matched_count / total * 100, 1)
                    st.info(f"Match arány: {match_ratio}%")
                
                st.write("🎯 Ha külön akarod listázni")
                with st.expander("🔗 Kapcsolt termékek"):
                    st.dataframe(
                        matched_df[matched_df["is_new_cluster"] == False]
                    )

                with st.expander("🆕 Új clusterre váró termékek"):
                    st.dataframe(
                        matched_df[matched_df["is_new_cluster"] == True]
                    )

    #*****************
    # IDEGEN TERMÉKEK PÁROSÍTÁSA
    #*****************        
    st.space("medium")
    st.header("3.Idegen termékek párosítása")

    threshold = st.slider("Minimum score?", 60, 100, 80)
    st.write("Letöltött termékek párosítása", threshold, "pont felett")

    webshops_df = dm.read_data(
        table_name="webshops",
        columns=["id", "name"],
        order_by="id"
    )

    # id -> name mapping
    webshop_dict = dict(zip(webshops_df["name"], webshops_df["id"]))

    selected_names = st.pills(
        "Webshop kiválasztása",
        options=list(webshop_dict.keys()),
        selection_mode="multi"
    )

    if selected_names:
            
        # kiválasztott webshop id-k
        selected_ids = [webshop_dict[name] for name in selected_names]
        st.markdown(f"Your selected options: {selected_ids}.")

        clusters = dm.read_data("clusters")
        
        
        products_without_cluster = dm.read_data(
            table_name="raw_products",
            in_filters = {"webshop_id": selected_ids},
            is_null = ["cluster_id"],
            order_by="id"
        )

    ph_table("Clusterek megtekintése", clusters)
    
    ph_table("Idegen termékek megjelenítése", products_without_cluster)

    if st.button("🔗 Termékek párosítása PM", type="primary"):
            
        with st.spinner("Párosítás folyamatban..."):            

            st.session_state["pm_matched_df"] = pm.match_products(products_without_cluster, clusters, threshold)
            st.session_state["rcm_matched_df"] = pm.match_products(products_without_cluster, clusters, threshold)
            
    if "pm_matched_df" in st.session_state:
      
        st.header("SIKERES PÁROSÍTÁS")
        
        st.header("PriceMatcher eredménye")

        ph_matched_result_view(st, st.session_state["pm_matched_df"])

    if "rcm_matched_df" in st.session_state:

        st.header("RapidClusterMatcher eredménye")

        #ph_matched_result_view(st, st.session_state["rcm_matched_df"])  
    
    st.space("medium")
    st.header("3. Adatok törlése")

    # session_state init
    if "delete_cluster_result" not in st.session_state:
        st.session_state.delete_cluster_result = None

    if "delete_raw_result" not in st.session_state:
        st.session_state.delete_raw_result = None


    # -------- CLUSTERS TÖRLÉS --------

    if st.button("CLUSTER-ek törlése", type="primary", key="del_clusters"):

        result = dm.delete_all_clusters()
        st.session_state.delete_cluster_result = result
        st.rerun()

    if st.session_state.delete_cluster_result:
        st.success(st.session_state.delete_cluster_result)


    # -------- RAW PRODUCTS TÖRLÉS --------

    if st.button("Letöltött termékek törlése", type="primary", key="del_products"):

        result = dm.delete_all_raw_products()
        st.session_state.delete_raw_result = result
        st.rerun()

    if st.session_state.delete_raw_result:
        st.success(st.session_state.delete_raw_result)

def page_data_explorer():

    st.title("📊 Adat Explorer")

    tab1, tab2, tab3 = st.tabs(
        ["🏠 Saját termékek", "🌍 Nyers termékek", "🧩 Clusterek"]
    )

    # =========================================================
    # 🏠 SAJÁT TERMÉKEK
    # =========================================================
    with tab1:

        st.subheader("Saját termékek")

        with st.expander("🔎 Szűrők", expanded=True):

            col1, col2, col3 = st.columns([1, 2, 1])

            with col1:
                cluster_filter = st.radio(
                    "Cluster állapot",
                    ["Összes", "Clusterelt", "Nem clusterelt"]
                )

            with col2:
                search_text = st.text_input("Keresés név alapján")

            with col3:
                limit = st.selectbox("Sor limit", [50, 100, 500, 1000], index=1)

        # ---- Query összeállítás ----
        query = {}
        is_null = []
        not_null = []

        if cluster_filter == "Nem clusterelt":
            is_null = ["cluster_id"]

        if cluster_filter == "Clusterelt":
            not_null = ["cluster_id"]

        own_df = dm.read_data(
            table_name="own_products",
            query=query,
            is_null=is_null,
            not_null=not_null,
            order_by="id",
        )

        if search_text:
            own_df = own_df[
                own_df["name"].str.contains(search_text, case=False, na=False)
            ]

        own_df = own_df.head(limit)

        # ---- Metrics ----
        total = len(own_df)
        clustered = len(own_df[own_df["cluster_id"].notna()]) if "cluster_id" in own_df else 0
        unclustered = len(own_df[own_df["cluster_id"].isna()]) if "cluster_id" in own_df else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Összes", total)
        col2.metric("Clusterelt", clustered)
        col3.metric("Nem clusterelt", unclustered)

        st.dataframe(own_df, use_container_width=True)


    # =========================================================
    # 🌍 NYERS TERMÉKEK
    # =========================================================
    with tab2:

        st.subheader("Nyers termékek")

        # Webshop lista
        webshops_df = dm.read_data(
            table_name="webshops",
            columns=["id", "name"],
            neq_filters={"id": 0},
            order_by="id"
        )

        webshop_dict = dict(zip(webshops_df["name"], webshops_df["id"]))

        with st.expander("🔎 Szűrők", expanded=True):

            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])

            with col1:
                cluster_filter = st.radio(
                    "Cluster állapot",
                    ["Összes", "Clusterelt", "Nem clusterelt"]
                )

            with col2:
                selected_webshops = st.multiselect(
                    "Webshop",
                    options=list(webshop_dict.keys())
                )

            with col3:
                search_text = st.text_input("Keresés név alapján")

            with col4:
                limit = st.selectbox("Sor limit", [50, 100, 500, 1000], index=1)

        in_filters = {}
        is_null = []
        not_null = []

        if selected_webshops:
            selected_ids = [webshop_dict[name] for name in selected_webshops]
            in_filters = {"webshop_id": selected_ids}

        if cluster_filter == "Nem clusterelt":
            is_null = ["cluster_id"]

        if cluster_filter == "Clusterelt":
            not_null = ["cluster_id"]

        raw_df = dm.read_data(
            table_name="raw_products",
            in_filters=in_filters,
            is_null=is_null,
            not_null=not_null,
            order_by="id",
        )

        if search_text and not raw_df.empty:
            raw_df = raw_df[
                raw_df["name"].str.contains(search_text, case=False, na=False)
            ]

        raw_df = raw_df.head(limit)

        total = len(raw_df)
        clustered = len(raw_df[raw_df["cluster_id"].notna()]) if "cluster_id" in raw_df else 0
        unclustered = len(raw_df[raw_df["cluster_id"].isna()]) if "cluster_id" in raw_df else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Összes", total)
        col2.metric("Clusterelt", clustered)
        col3.metric("Nem clusterelt", unclustered)

        st.dataframe(raw_df, use_container_width=True)


    # =========================================================
    # 🧩 CLUSTEREK
    # =========================================================
    with tab3:

        st.subheader("Clusterek")

        with st.expander("🔎 Szűrők", expanded=True):

            col1, col2 = st.columns([2, 1])

            with col1:
                search_text = st.text_input("Cluster név keresés")

            with col2:
                limit = st.selectbox("Sor limit", [50, 100, 500, 1000], index=1)

        clusters_df = dm.read_data(
            table_name="clusters",
            order_by="id"
        )

        if search_text:
            clusters_df = clusters_df[
                clusters_df["name"].str.contains(search_text, case=False, na=False)
            ]

        clusters_df = clusters_df.head(limit)

        st.metric("Összes cluster", len(clusters_df))

        st.dataframe(clusters_df, use_container_width=True)

def page_settings():
    st.header("⚙️ Beállítások")
    st.write("User:", st.session_state.username)
    
#============================================
#===============   MAIN APP   ===============
#============================================
if not st.session_state.logged_in:
    login_page()

else:  
    st.sidebar.image("Images/PriceHunter-logo-fekvő.png", width=400, use_container_width=True)
    st.sidebar.write(f"Bejelentkezve: {st.session_state.username}")

    if st.sidebar.button("Kijelentkezés"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    page = st.sidebar.radio(
        "Menü",
        ["Dashboard", "Vezérlőpult", "Adatok", "Keresés", "Árak elemzése", "Beállítások"]
    )

    if page == "Dashboard":
        page_dashboard()

    elif page == "Vezérlőpult":
        page_controlpanel()

    elif page == "Adatok":
        page_data_explorer()

    elif page == "Keresés":
        page_search()

    elif page == "Árak elemzése":
        page_price_setter()

    elif page == "Beállítások":
        page_settings()


