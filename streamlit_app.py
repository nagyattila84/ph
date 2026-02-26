import streamlit as st
from werkzeug.security import check_password_hash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from datamanager import SupaBaseDataManager
from analyst import PriceAnalyst
from my_stat import Statistic

users = st.secrets["users"]
stat = None
dm = None
st.set_page_config(page_title="PriceHunter", layout="centered")

# ============= SESSION INIT ===============
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "username" not in st.session_state:
    st.session_state["username"] = ""

# ================= LOGIN =================
def login_page():   
    st.title("Bejelentkezés")
    username = st.text_input("Felhasználónév")
    password = st.text_input("Jelszó", type="password")

    if st.button("Belépés"):
        ok = False
    
        if username in users:
            try:
                ok = check_password_hash(users[username], password)            
            except Exception as e:
                st.write(e)
    
        if ok:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.set_page_config(page_title="PriceHunter", layout="wide")
            st.rerun()
        else:
            st.error("Hibás felhasználónév vagy jelszó")

# ================= PAGES =================
def page_dashboard():
    dm = SupaBaseDataManager(st.secrets.supabase.url, st.secrets.supabase.key)
    stat = Statistic(st.secrets.supabase.url, st.secrets.supabase.key)


    st.header("📊 Dashboard")
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Webshopok", stat.count_shops())
    c2.metric("Clusterek", stat.count_clusters())
    c3.metric("Saját termékek", stat.count_own_products())
    c4.metric("Idegen termékek", stat.count_raw_products())

    df = pd.DataFrame({
        "type": ["Saját termék", "Idegen termék"],
        "count": [stat.count_own_products(), stat.count_raw_products()]
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

def page_visual3():
    dm = SupaBaseDataManager(st.secrets.supabase.url, st.secrets.supabase.key)    
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
    dm = SupaBaseDataManager(st.secrets.supabase.url, st.secrets.supabase.key)
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
    from scraper import Scraper
    sc = Scraper()
    dm = SupaBaseDataManager(st.secrets.supabase.url, st.secrets.supabase.key)
    stat = Statistic(st.secrets.supabase.url, st.secrets.supabase.key)
    
    st.sidebar.header("📊 Vezérlőpult")
      
    st.set_page_config(layout="wide")
    st.title("📊 Vezérlőpult")
    
    st.header("0. Saját árak feltöltése")
    st.write("Az own_product táblába manuálisan kerülnek a saját termék adatok.")

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
        expander = st.expander("Árak megtekintése")
        expander.table(st.session_state.scraped_prices)
    
        if st.button("💾 Árak mentése adatbázisba", type="primary"):
            
            with st.spinner("Mentés folyamatban..."):
                result = dm.save_raw_products_prices(st.session_state.scraped_prices)

            if result["success"]:
                st.success(f"✅ {result['count']} termék sikeresen mentve.")
            else:
                st.error(f"❌ Hiba történt mentés közben:\n{result['error']}")
            del st.session_state.scraped_prices

    st.header("2.Termék párosítás")
    threshold = st.slider("Minimum score?", 60, 100, 80)
    st.write("Termékek párosítás a", threshold, "pont felett")

    if st.button("🔗 Termékek párosítása", type="primary"):
            
            with st.spinner("Párosítás folyamatban..."):
                products = None
                clusters = None
                matched_df = match_products(products, clusters, threshold)

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

    st.header("3.Adatok törlése")
    delete_block("CLUSTER-ek törlése", dm.delete_all_clusters)
    

def delete_block(label, delete_function):

    col1, col2 = st.columns([2, 1])

    toggle = col1.toggle(f"⚠ {label}")
    button = col2.button("🗑 Törlés")

    if button:
        if toggle:
            count = delete_function()
            st.success(f"{count} rekord törölve.")
        else:
            st.error("Aktiváld a megerősítést!")       

def page_settings():
    st.header("⚙️ Beállítások")
    st.write("User:", st.session_state.username)
    
#============================================
#===============   MAIN APP   ===============
#============================================
if not st.session_state.logged_in:
    login_page()

else:  
    st.sidebar.image("PriceHunter-logo-fekvő.png", width=400, use_container_width=True)
    st.sidebar.write(f"Bejelentkezve: {st.session_state.username}")

    if st.sidebar.button("Kijelentkezés"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    page = st.sidebar.radio(
        "Menü",
        ["Dashboard", "Vezérlő", "Keresés", "Vizuál", "Beállítások"]
    )

    if page == "Dashboard":
        page_dashboard()

    elif page == "Vezérlő":
        page_controlpanel()

    elif page == "Keresés":
        page_search()

    elif page == "Vizuál":
        page_visual3()

    elif page == "Beállítások":
        page_settings()


