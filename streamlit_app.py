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
            st.rerun()
        else:
            st.error("Hibás felhasználónév vagy jelszó")

# ================= PAGES =================
def page_dashboard():
    dm = SupaBaseDataManager()
    stat = Statistic()

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

def page_search():
    dm = SupaBaseDataManager()
    pa = PriceAnalyst(dm)
    st.title("Ár összehasonlító")    
    keyword = st.text_input("Keresőszó")
    
    if keyword:
        #own_df, raw_df = dm.get_products_by_keyword(keyword)
        df = pa.get_cluster_price_view(keyword)
    
        st.subheader("Termékek")
        st.dataframe(df)

def page_visual3():
    st.title("Ár összehasonlító") 
    dm = SupaBaseDataManager()
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
    dm = SupaBaseDataManager()
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
    dm = SupaBaseDataManager()
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
    # Cím
    dm = SupaBaseDataManager()
    stat = Statistic()
    
    st.title("📊 Vezérlőpult")
    
    st.header("0. Saját árak feltöltése")
    st.write("Az own_product táblába manuálisan kerülnek a saját termék adatok.")
    st.header("1. Webshopok beállítás")
        
    col1, col2 = st.columns([1,3]])

    with col1:
        keyword = st.text_input("Keresőszó", width=200)


    with col2:
            
        st.write("Konkurens webáruházak kijelölése, az árak lekérdezéséhez.")

        shops = stat.shops_small()

        # hozzáadunk egy kijelölő oszlopot
        if "selected_shops" not in st.session_state:
            shops["Kijelöl"] = False
            st.session_state.selected_shops = shops

        shops = st.data_editor(
            st.session_state.selected_shops,
            column_config={
                "name": "Webáruház neve",
                "base_url": "Link",
                "company": "Cégnév"
            },
            use_container_width=True
        )

    # kiválasztott sorok
    st.write("Kijelölt sorok:")
    selected_rows = shops[shops["Kijelöl"]]
    st.write(selected_rows)
    
    if st.button("Árak letÖltése"):
        st.write("Árak letöltve....")


    

    st.header("2.Termék párosítás")
    st.header("3.Árak összehasonlítása")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.text_input("Bal oldal")
    
    with col2:
        st.text_input("Jobb oldal")

    
    # ---- Beviteli mezők ----
    
    nev = st.text_input("Add meg a neved:")
    
    kor = st.number_input(
        "Add meg az életkorod:",
        min_value=0,
        max_value=120,
        step=1
    )
    
    opcio = st.selectbox(
        "Válassz egy opciót:",
        ["A", "B", "C"]
    )
    
    # ---- Gomb ----
    
    if st.button("Mentés"):
        st.success("Adatok elmentve!")
    
        st.write("### Bevitt adatok:")
        st.write(f"Név: {nev}")
        st.write(f"Kor: {kor}")
        st.write(f"Opció: {opcio}")
    
    # ---- Oldalsáv (sidebar) ----
    
    st.sidebar.header("⚙ Beállítások")
    
    debug = st.sidebar.checkbox("Debug mód")
    
    if debug:
        st.sidebar.write("Debug aktív")
        st.sidebar.json({
            "nev": nev,
            "kor": kor,
            "opcio": opcio
        })

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

