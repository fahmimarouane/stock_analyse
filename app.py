import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

st.set_page_config(page_title="PC Parts Comparison", page_icon="📊", layout="wide")

# Minimal Dark Theme & Sidebar Styling
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    .stSidebar { background-color: #161b22; border-right: 1px solid #30363d; }
    [data-testid="stMetricValue"] { color: #58a6ff; }
    .stSidebar h2 { color: #58a6ff; font-size: 1.2rem; margin-top: 1rem; border-bottom: 1px solid #30363d; padding-bottom: 0.5rem; }
    .stSidebar h3 { color: #c9d1d9; font-size: 1rem; margin-top: 1.5rem; }
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
    
    # --- FILTERS SECTION ---
    st.sidebar.markdown("## 🔍 Filters")
    
    st.sidebar.markdown("#### Categories")
    cats = sorted(df['categorie'].dropna().unique().tolist())
    sel_cats = st.sidebar.multiselect("Select Categories", cats, default=cats, label_visibility="collapsed")
    
    st.sidebar.markdown("#### Stock Status")
    stocks = df['stock_status'].unique().tolist()
    sel_stocks = st.sidebar.multiselect("Select Status", stocks, default=stocks, label_visibility="collapsed")
    
    st.sidebar.markdown("#### Price Range (MAD)")
    prices = pd.concat([df[f'{site1}_price'].dropna(), df[f'{site2}_price'].dropna()])
    min_p, max_p = (float(prices.min()), float(prices.max())) if not prices.empty else (0.0, 0.0)
    pr = st.sidebar.slider("Price Range", min_p, max_p, (min_p, max_p), label_visibility="collapsed")
    
    st.sidebar.markdown("#### Search")
    search = st.sidebar.text_input("Search by Ref or Name", "", label_visibility="collapsed")
    
    # Apply Filters
    f_df = df[(df['categorie'].isin(sel_cats)) & (df['stock_status'].isin(sel_stocks))].copy()
    f_df = f_df[f_df.apply(lambda r: pr[0] <= min([p for p in [r[f'{site1}_price'], r[f'{site2}_price']] if not pd.isna(p)] or [0]) <= pr[1], axis=1)]
    if search:
        f_df = f_df[f_df['reference'].str.contains(search, case=False, na=False) | 
                    f_df[f'{site1}_name'].astype(str).str.contains(search, case=False, na=False) | 
                    f_df[f'{site2}_name'].astype(str).str.contains(search, case=False, na=False)]

    # Ensure URLs are valid strings for links
    f_df[f'{site1}_url'] = f_df[f'{site1}_url'].fillna("").astype(str)
    f_df[f'{site2}_url'] = f_df[f'{site2}_url'].fillna("").astype(str)

    b1, b2 = st.columns(2)
    with b1: st.download_button("📥 Excel", to_excel(f_df), f"comp_{datetime.now():%Y%m%d}.xlsx", use_container_width=True)
    with b2: st.download_button("📄 CSV", f_df.to_csv(index=False).encode(), f"comp_{datetime.now():%Y%m%d}.csv", use_container_width=True)

    t1, t2, t3 = st.tabs(["📈 Summary", "💰 Prices", "📦 Stock"])
    
    with t1:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"Total {site1}", len(st.session_state.df1))
        m2.metric(f"Total {site2}", len(st.session_state.df2))
        m3.metric("Common", len(df.dropna(subset=[f'{site1}_name', f'{site2}_name'])))
        m4.metric("Categories", len(cats))
        
    with t2:
        p_df = f_df.dropna(subset=[f'{site1}_price', f'{site2}_price']).copy()
        p_df['Diff (MAD)'] = p_df['price_diff'].round(2)
        st.dataframe(
            p_df[['reference', 'categorie', f'{site1}_name', f'{site1}_price', f'{site2}_name', f'{site2}_price', 'Diff (MAD)', f'{site1}_url', f'{site2}_url']].sort_values('Diff (MAD)', ascending=False),
            use_container_width=True, 
            hide_index=True,
            column_config={
                f'{site1}_price': st.column_config.NumberColumn(format="%.2f MAD"),
                f'{site2}_price': st.column_config.NumberColumn(format="%.2f MAD"),
                f'{site1}_url': st.column_config.LinkColumn(f"🔗 {site1}", display_text=f"Open {site1}"),
                f'{site2}_url': st.column_config.LinkColumn(f"🔗 {site2}", display_text=f"Open {site2}")
            }
        )
                        
    with t3:
        s_df = f_df[f_df['stock_status'].isin([f"Only {site1} In Stock", f"Only {site2} In Stock", "Both Out of Stock", "Both In Stock"])]
        st.dataframe(
            s_df[['reference', 'categorie', 'stock_status', f'{site1}_name', f'{site1}_stock', f'{site2}_name', f'{site2}_stock', f'{site1}_url', f'{site2}_url']]
              .style.map(lambda x: 'color: #ff4b4b' if x=='Out of Stock' else 'color: #21ba45', subset=[f'{site1}_stock', f'{site2}_stock']),
            use_container_width=True, 
            hide_index=True,
            column_config={
                f'{site1}_url': st.column_config.LinkColumn(f"🔗 {site1}", display_text=f"Open {site1}"),
                f'{site2}_url': st.column_config.LinkColumn(f"🔗 {site2}", display_text=f"Open {site2}")
            }
        )
else:
    st.info("Upload files to begin.")
