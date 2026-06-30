import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

st.set_page_config(page_title="PC Parts Comparison", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# WONDERFUL THEME — modern dark UI with gradient accents & glass cards
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp {
        background: radial-gradient(circle at 15% 0%, #1b2236 0%, #0b0e16 45%, #060810 100%);
        color: #eef1f8;
    }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #151a29 0%, #0d1019 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
    }
    section[data-testid="stSidebar"] h2 {
        background: linear-gradient(90deg, #7f9cf5, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: .02em;
        margin-top: .5rem;
        padding-bottom: .5rem;
        border-bottom: 1px solid rgba(255,255,255,0.08);
    }

    /* ---------- Title ---------- */
    h1 {
        background: linear-gradient(90deg, #8ab4ff 0%, #b794f6 50%, #f6a8c9 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        letter-spacing: -.02em;
        padding-bottom: 4px;
    }
    h3, h4 { color: #e7eaf6 !important; font-weight: 700 !important; }

    /* ---------- Metrics ---------- */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(127,156,245,0.12), rgba(167,139,250,0.06));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 16px;
        padding: 16px 18px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.25);
    }
    [data-testid="stMetricValue"] {
        background: linear-gradient(90deg, #8ab4ff, #b794f6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
    }
    [data-testid="stMetricLabel"] { color: #aab2c8 !important; font-weight: 600; }

    /* ---------- Bordered containers (filters card) ---------- */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: linear-gradient(160deg, rgba(255,255,255,0.035), rgba(255,255,255,0.01));
        border: 1px solid rgba(255,255,255,0.09) !important;
        border-radius: 18px !important;
        box-shadow: 0 8px 28px rgba(0,0,0,0.3);
        padding: 6px 4px;
    }

    /* ---------- Buttons ---------- */
    .stButton button, .stDownloadButton button {
        background: linear-gradient(90deg, #6f86f0, #a380f0);
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: 700;
        padding: 0.55rem 1rem;
        box-shadow: 0 4px 14px rgba(120,110,240,0.35);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    .stButton button:hover, .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 20px rgba(120,110,240,0.5);
        color: white;
    }

    /* ---------- File uploader ---------- */
    [data-testid="stFileUploaderDropzone"] {
        background: rgba(255,255,255,0.03);
        border: 1.5px dashed rgba(140,150,220,0.4) !important;
        border-radius: 14px;
    }

    /* ---------- Inputs ---------- */
    .stTextInput input, .stMultiSelect div[data-baseweb="select"] > div, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.045) !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.09) !important;
        color: #eef1f8 !important;
    }

    /* ---------- Centered horizontal nav (radio) ---------- */
    div[role="radiogroup"] {
        justify-content: center;
        gap: 6px;
        padding: 8px;
        background: linear-gradient(145deg, rgba(255,255,255,0.04), rgba(255,255,255,0.015));
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.08);
        margin-bottom: 22px;
    }
    div[role="radiogroup"] label {
        background: transparent;
        border-radius: 10px;
        padding: 6px 14px;
        transition: background .15s ease;
    }
    div[role="radiogroup"] label:hover { background: rgba(255,255,255,0.06); }

    /* ---------- Dataframes ---------- */
    [data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,0.08);
    }

    /* ---------- Misc ---------- */
    hr { border-color: rgba(255,255,255,0.08); }
    .stAlert { border-radius: 12px; }
</style>
""", unsafe_allow_html=True)

if 'merged_df' not in st.session_state: st.session_state.merged_df = None
if 'df1' not in st.session_state: st.session_state.df1 = None
if 'df2' not in st.session_state: st.session_state.df2 = None

def clean_price(price_str):
    if pd.isna(price_str) or not isinstance(price_str, str):
        try: return float(price_str)
        except: return None
    cleaned = re.sub(r'[^\d,\.]', '', price_str)
    if ',' in cleaned and '.' in cleaned: cleaned = cleaned.replace(',', '')
    elif ',' in cleaned: cleaned = cleaned.replace(',', '.')
    try: return float(cleaned)
    except: return None

def process_data(df, site_name):
    if df is None or df.empty: return pd.DataFrame()
    cols = ["categorie", "site", "url_produit", "product_name", "reference", "price", "availability"]
    for col in cols:
        if col not in df.columns: df[col] = None
    df = df[cols].copy()
    df['reference'] = df['reference'].astype(str).str.strip()
    df = df[df['reference'].notna() & (df['reference'] != '') & (df['reference'] != 'nan')]

    df['url_produit'] = df['url_produit'].astype(str).str.strip()
    df.loc[df['url_produit'].isin(['nan', 'None', '']), 'url_produit'] = None

    df['price_num'] = df['price'].apply(clean_price)
    df['availability'] = df['availability'].astype(str).str.lower().apply(
        lambda x: 'In Stock' if 'instock' in x or 'disponible' in x else 'Out of Stock'
    )
    df['site'] = site_name
    return df

def merge_data(df1, df2, site1_name, site2_name):
    df1_renamed = df1.rename(columns={
        'product_name': f'{site1_name}_name', 'price_num': f'{site1_name}_price',
        'availability': f'{site1_name}_stock', 'url_produit': f'{site1_name}_url'
    })[['reference', 'categorie', f'{site1_name}_name', f'{site1_name}_price', f'{site1_name}_stock', f'{site1_name}_url']]

    df2_renamed = df2.rename(columns={
        'product_name': f'{site2_name}_name', 'price_num': f'{site2_name}_price',
        'availability': f'{site2_name}_stock', 'url_produit': f'{site2_name}_url'
    })[['reference', f'{site2_name}_name', f'{site2_name}_price', f'{site2_name}_stock', f'{site2_name}_url']]

    merged = pd.merge(df1_renamed, df2_renamed, on='reference', how='outer', suffixes=('', '_drop'))
    if 'categorie_drop' in merged.columns:
        merged['categorie'] = merged['categorie'].fillna(merged['categorie_drop'])
        merged.drop(columns=['categorie_drop'], inplace=True)

    merged['price_diff'] = merged[f'{site1_name}_price'] - merged[f'{site2_name}_price']

    def get_stock_status(row):
        s1, s2 = row[f'{site1_name}_stock'], row[f'{site2_name}_stock']
        if pd.isna(s1): return f"Only in {site2_name}"
        if pd.isna(s2): return f"Only in {site1_name}"
        if s1 == "In Stock" and s2 == "In Stock": return "Both In Stock"
        if s1 == "Out of Stock" and s2 == "Out of Stock": return "Both Out of Stock"
        if s1 == "In Stock": return f"Only {site1_name} In Stock"
        if s2 == "In Stock": return f"Only {site2_name} In Stock"
        return "Unknown"
    merged['stock_status'] = merged.apply(get_stock_status, axis=1)
    return merged

def to_excel(df):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w: df.to_excel(w, index=False, sheet_name='Comparison')
    return out.getvalue()

st.title("📊 PC Parts Comparison")
st.caption("Compare prices & stock availability across PC component retailers — fast, clean, and visual.")

# --- SIDEBAR ORGANIZATION ---
st.sidebar.markdown("## ⚙️ Configuration")

menu_option = st.sidebar.selectbox("Comparison Mode", ["ZoneTech vs UltraPC", "ZoneTech vs NextLevelPC"])
site1, site2 = ("ZoneTech", "UltraPC") if menu_option == "ZoneTech vs UltraPC" else ("ZoneTech", "NextLevelPC")

if st.sidebar.button("🔄 Change Data / Reload", use_container_width=True):
    st.session_state.merged_df = None
    st.session_state.df1 = None
    st.session_state.df2 = None
    st.rerun()

c1, c2 = st.columns(2)
with c1: file1 = st.file_uploader(f"{site1} Excel", type=["xlsx"], key="f1")
with c2: file2 = st.file_uploader(f"{site2} Excel", type=["xlsx"], key="f2")

if file1 and file2:
    try:
        df1 = process_data(pd.read_excel(file1), site1)
        df2 = process_data(pd.read_excel(file2), site2)
        if df1.empty or df2.empty:
            st.error("Missing required columns.")
        else:
            st.session_state.df1, st.session_state.df2 = df1, df2
            st.session_state.merged_df = merge_data(df1, df2, site1, site2)
    except Exception as e:
        st.error(f"Error: {e}")

if st.session_state.merged_df is not None:
    df = st.session_state.merged_df

    # --- FILTERS ON MAIN PAGE ---
    with st.container(border=True):
        st.markdown("#### 🔍 Filters & Search")
        fc1, fc2, fc3, fc4 = st.columns([1.5, 1.2, 1.2, 1.2])

        with fc1:
            cats = sorted(df['categorie'].dropna().unique().tolist())
            sel_cats = st.multiselect("Categories", cats, default=cats)

        with fc2:
            stocks = df['stock_status'].unique().tolist()
            sel_stocks = st.multiselect("Stock Status", stocks, default=stocks)

        with fc3:
            search = st.text_input("Search by Ref or Name", "")

        with fc4:
            prices = pd.concat([df[f'{site1}_price'].dropna(), df[f'{site2}_price'].dropna()])
            min_p, max_p = (float(prices.min()), float(prices.max())) if not prices.empty else (0.0, 0.0)
            pr = st.slider("Price Range (MAD)", min_p, max_p, (min_p, max_p))

    # Apply Filters
    f_df = df[(df['categorie'].isin(sel_cats)) & (df['stock_status'].isin(sel_stocks))].copy()
    f_df = f_df[f_df.apply(lambda r: pr[0] <= min([p for p in [r[f'{site1}_price'], r[f'{site2}_price']] if not pd.isna(p)] or [0]) <= pr[1], axis=1)]
    if search:
        f_df = f_df[f_df['reference'].str.contains(search, case=False, na=False) |
                    f_df[f'{site1}_name'].astype(str).str.contains(search, case=False, na=False) |
                    f_df[f'{site2}_name'].astype(str).str.contains(search, case=False, na=False)]

    # Combine product names into ONE column right after 'categorie'
    f_df['Product Name'] = f_df[f'{site1}_name'].fillna(f_df[f'{site2}_name'])

    # Ensure URLs are valid strings for links
    f_df[f'{site1}_url'] = f_df[f'{site1}_url'].fillna("").astype(str)
    f_df[f'{site2}_url'] = f_df[f'{site2}_url'].fillna("").astype(str)

    # --- EXPORT BUTTONS ---
    b1, b2 = st.columns(2)
    with b1: st.download_button("📥 Excel", to_excel(f_df), f"comp_{datetime.now():%Y%m%d}.xlsx", use_container_width=True)
    with b2: st.download_button("📄 CSV", f_df.to_csv(index=False).encode(), f"comp_{datetime.now():%Y%m%d}.csv", use_container_width=True)

    # --- HORIZONTAL CENTERED MENU ---
    st.markdown("")  # Spacer
    view_options = ["📈 Summary", "💰 Prices", "📦 Stock"]
    selected_view = st.radio("Navigation", view_options, horizontal=True, label_visibility="collapsed")

    # --- SUMMARY VIEW ---
    if selected_view == "📈 Summary":
        st.markdown("### 📈 Summary Metrics")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"Total {site1}", len(st.session_state.df1))
        m2.metric(f"Total {site2}", len(st.session_state.df2))
        m3.metric("Common", len(df.dropna(subset=[f'{site1}_name', f'{site2}_name'])))
        m4.metric("Categories", len(cats))

    # --- PRICES VIEW ---
    elif selected_view == "💰 Prices":
        st.markdown("### 💰 Price Comparison")
        p_df = f_df.dropna(subset=[f'{site1}_price', f'{site2}_price']).copy()
        p_df['Diff (MAD)'] = p_df['price_diff'].round(2)

        display_cols_p = ['reference', 'categorie', 'Product Name', f'{site1}_price', f'{site2}_price', 'Diff (MAD)', f'{site1}_url', f'{site2}_url']

        st.dataframe(
            p_df[display_cols_p].sort_values('Diff (MAD)', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                f'{site1}_price': st.column_config.NumberColumn(f"{site1} Price", format="%.2f MAD"),
                f'{site2}_price': st.column_config.NumberColumn(f"{site2} Price", format="%.2f MAD"),
                f'{site1}_url': st.column_config.LinkColumn(f"🔗 {site1}", display_text=f"Open {site1}"),
                f'{site2}_url': st.column_config.LinkColumn(f"🔗 {site2}", display_text=f"Open {site2}")
            }
        )

    # --- STOCK VIEW ---
    elif selected_view == "📦 Stock":
        st.markdown("### 📦 Stock Availability")
        s_df = f_df[f_df['stock_status'].isin([f"Only {site1} In Stock", f"Only {site2} In Stock", "Both Out of Stock", "Both In Stock"])]

        display_cols_s = ['reference', 'categorie', 'Product Name', 'stock_status', f'{site1}_stock', f'{site2}_stock', f'{site1}_url', f'{site2}_url']

        def style_stock(val):
            if val == 'In Stock': return 'color: #3ddc84; font-weight: bold'
            if val == 'Out of Stock': return 'color: #ff6b81; font-weight: bold'
            return 'color: gray'  # For NaN/missing values

        st.dataframe(
            s_df[display_cols_s].style.map(style_stock, subset=[f'{site1}_stock', f'{site2}_stock']),
            use_container_width=True,
            hide_index=True,
            column_config={
                f'{site1}_url': st.column_config.LinkColumn(f"🔗 {site1}", display_text=f"Open {site1}"),
                f'{site2}_url': st.column_config.LinkColumn(f"🔗 {site2}", display_text=f"Open {site2}")
            }
        )
else:
    st.info("Upload files to begin.")
