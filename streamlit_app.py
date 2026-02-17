import streamlit as st
from werkzeug.security import check_password_hash
from datamanager import SupaBaseDataManager
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

users = st.secrets["users"]

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
        ok = True
    
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
    st.header("📊 Dashboard")
    st.write("Ez az első oldal")

def page_search():
    dm = SupaBaseDataManager()
    st.title("Ár összehasonlító")    
    keyword = st.text_input("Keresőszó")
    
    if keyword:
        own_df, raw_df = dm.get_products_by_keyword(keyword)
    
        st.subheader("Saját termékek")
        st.dataframe(own_df)
    
        st.subheader("Beszállítók")
        st.dataframe(raw_df)

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
        df["id"].unique(),
        df["id"].unique()[:5]
    )
    df = df[df["id"].isin(products)]

    fig = go.Figure()

    for product in df["id"].unique():
        sub = df[df["id"] == product]
    
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

def page_settings():
    st.header("⚙️ Beállítások")
    st.write("User:", st.session_state.username)
    
#============================================
#===============   MAIN APP   ===============
#============================================
if not st.session_state.logged_in:
    login_page()

else:
    st.sidebar.write(f"Bejelentkezve: {st.session_state.username}")

    if st.sidebar.button("Kijelentkezés"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    page = st.sidebar.radio(
        "Menü",
        ["Dashboard", "Keresés", "Vizuál", "Beállítások"]
    )

    if page == "Dashboard":
        page_dashboard()

    elif page == "Keresés":
        page_search()

    elif page == "Vizuál":
        page_visual3()

    elif page == "Beállítások":
        page_settings()




































