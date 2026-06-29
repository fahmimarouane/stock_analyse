# main.py
import streamlit as st
import pandas as pd
import re
import io
from datetime import datetime

# =========================
# PAGE CONFIGURATION
# =========================
st.set_page_config(
    page_title="PC Parts Comparison Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CUSTOM CSS — RESPONSIVE & PROFESSIONAL
# =========================
st.markdown("""
<style>
    /* Mobile-first responsive design */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            padding-top: 1rem !important;
        }
        [data-testid="stMetric"] {
            text-align: center;
            padding: 0.5rem !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.4rem !important;
        }
        h1, h2, h3 {
            font-size: 1.5rem !important;
        }
        .stDataFrame {
            width: 100% !important;
        }
        [data-testid="column"] {
            width: 100% !important;
            flex: none !important;
        }
    }

    /* Professional card styling */
    .metric-card {
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        padding: 1.2rem;
        border-radius: 12px;
        border-left: 4px solid #0066cc;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        transition: transform 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .stat-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        text-align: center;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #0066cc;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #666;
        margin-top: 0.25rem;
    }
    .deal-card {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin-bottom: 0.5rem;
    }
    .warning-card {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #ffc107;
        margin-bottom: 0.5rem;
    }
    .danger-card {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #dc3545;
        margin-bottom: 0.5rem;
    }
    .header-gradient {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1.5rem;
    }
    .header-gradient h1 {
        color: white !important;
        margin-bottom: 0.3rem !important;
    }
    .filter-section {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    /* Hide streamlit footer */
    footer {visibility: hidden;}
    /* Better dataframe on mobile */
    .stDataFrame [data-testid="stDataFrameResizable"] {
        min-height: 300px;
    }
</style>
""", unsafe_allow_html=True)

# =========================
# SESSION STATE
# =========================
if 'merged_df' not in st.session_state:
    st.session_state.merged_df = None
if 'df1' not in st.session_state:
    st.session_state.df1 = None
if 'df2' not in st.session_state:
    st.session_state.df2 = None
if 'site1' not in st.session_state:
    st.session_state.site1 = None
if 'site2' not in st.session_state:
    st.session_state.site2 = None

# =========================
# HELPER FUNCTIONS
# =========================
def clean_price(price_str):
    """Convert messy price strings like '1 234,56 MAD' to float 1234.56"""
    if pd.isna(price_str) or not isinstance(price_str, str):
        try:
            return float(price_str)
        except (ValueError, TypeError):
            return None
    cleaned = re.sub(r'[^\d,\.]', '', price_str)
    if ',' in cleaned and '.' in cleaned:
        cleaned = cleaned.replace(',', '')
    elif ',' in cleaned:
        cleaned = cleaned.replace(',', '.')
    try:
        return float(cleaned)
    except ValueError:
        return None

def process_data(df, site_name):
    """Standardize the dataframe for comparison"""
    if df is None or df.empty:
        return pd.DataFrame()
    cols = ["categorie", "site", "url_produit", "product_name", "reference", "price", "availability"]
    for col in cols:
        if col not in df.columns:
            df[col] = None
    df = df[cols].copy()
    df['reference'] = df['reference'].astype(str).str.strip()
    df = df[df['reference'].notna() & (df['reference'] != '') & (df['reference'] != 'nan')]
    df['price_num'] = df['price'].apply(clean_price)
    df['availability'] = df['availability'].astype(str).str.lower().apply(
        lambda x: 'In Stock' if 'instock' in x or 'disponible' in x else 'Out of Stock'
    )
    df['site'] = site_name
    return df

def merge_data(df1, df2, site1_name, site2_name):
    """Merge two dataframes based on reference"""
    df1_renamed = df1.rename(columns={
        'product_name': f'{site1_name}_name',
        'price_num': f'{site1_name}_price',
        'availability': f'{site1_name}_stock',
        'url_produit': f'{site1_name}_url',
    })[['reference', 'categorie', f'{site1_name}_name', f'{site1_name}_price', f'{site1_name}_stock', f'{site1_name}_url']]

    df2_renamed = df2.rename(columns={
        'product_name': f'{site2_name}_name',
        'price_num': f'{site2_name}_price',
        'availability': f'{site2_name}_stock',
        'url_produit': f'{site2_name}_url'
    })[['reference', f'{site2_name}_name', f'{site2_name}_price', f'{site2_name}_stock', f'{site2_name}_url']]

    merged = pd.merge(df1_renamed, df2_renamed, on='reference', how='outer', suffixes=('', '_drop'))
    if 'categorie_drop' in merged.columns:
        merged['categorie'] = merged['categorie'].fillna(merged['categorie_drop'])
        merged.drop(columns=['categorie_drop'], inplace=True)

    merged['price_diff'] = merged[f'{site1_name}_price'] - merged[f'{site2_name}_price']

    def pct_diff(row):
        p1, p2 = row[f'{site1_name}_price'], row[f'{site2_name}_price']
        if pd.isna(p1) or pd.isna(p2) or p2 == 0:
            return None
        return round(((p1 - p2) / p2) * 100, 2)

    merged['price_diff_pct'] = merged.apply(pct_diff, axis=1)

    def get_stock_status(row):
        s1 = row[f'{site1_name}_stock']
        s2 = row[f'{site2_name}_stock']
        if pd.isna(s1): return f"Only in {site2_name}"
        if pd.isna(s2): return f"Only in {site1_name}"
        if s1 == "In Stock" and s2 == "In Stock": return "Both In Stock"
        if s1 == "Out of Stock" and s2 == "Out of Stock": return "Both Out of Stock"
        if s1 == "In Stock": return f"Only {site1_name} In Stock"
        if s2 == "In Stock": return f"Only {site2_name} In Stock"
        return "Unknown"

    merged['stock_status'] = merged.apply(get_stock_status, axis=1)

    def best_store(row):
        p1, p2 = row[f'{site1_name}_price'], row[f'{site2_name}_price']
        if pd.isna(p1) and pd.isna(p2): return "N/A"
        if pd.isna(p1): return site2_name
        if pd.isna(p2): return site1_name
        if p1 < p2: return site1_name
        if p2 < p1: return site2_name
        return "Equal"

    merged['best_store'] = merged.apply(best_store, axis=1)
    return merged

def convert_df_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Comparison')
    return output.getvalue()

# =========================
# HEADER
# =========================
st.markdown("""
<div class="header-gradient">
    <h1>📊 PC Parts Comparison Pro</h1>
    <p style="margin:0; opacity:0.9;">Professional tool for comparing prices & stock across PC parts retailers</p>
</div>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR CONFIGURATION
# =========================
st.sidebar.markdown("## ⚙️ Configuration")

menu_option = st.sidebar.selectbox(
    "Comparison Mode",
    ["ZoneTech vs UltraPC", "ZoneTech vs NextLevelPC"],
    help="Choose which two stores you want to compare."
)

if menu_option == "ZoneTech vs UltraPC":
    site1, site2 = "ZoneTech", "UltraPC"
else:
    site1, site2 = "ZoneTech", "NextLevelPC"

st.session_state.site1 = site1
st.session_state.site2 = site2

# Display settings
st.sidebar.markdown("### 🎨 Display Settings")
show_percentage = st.sidebar.checkbox("Show % Differences", value=True)
dark_tables = st.sidebar.checkbox("Dark Table Theme", value=False)
currency = st.sidebar.selectbox("Currency", ["MAD", "EUR", "USD", "GBP"], index=0)

# Reset button
if st.sidebar.button("🔄 Reset Session", use_container_width=True):
    for key in ['merged_df', 'df1', 'df2']:
        st.session_state[key] = None
    st.rerun()

# =========================
# FILE UPLOAD (RESPONSIVE)
# =========================
st.markdown("### 📁 Upload Data Files")
st.markdown("Upload your Excel files from the scrapers to begin the comparison.")

col1, col2 = st.columns(2)
with col1:
    st.markdown(f"**🏢 {site1}**")
    file1 = st.file_uploader(f"Upload {site1} Excel", type=["xlsx"], key="file1", label_visibility="collapsed")
with col2:
    st.markdown(f"**🏢 {site2}**")
    file2 = st.file_uploader(f"Upload {site2} Excel", type=["xlsx"], key="file2", label_visibility="collapsed")

# =========================
# DATA PROCESSING
# =========================
if file1 and file2:
    with st.spinner("Processing data..."):
        try:
            df1_raw = pd.read_excel(file1)
            df2_raw = pd.read_excel(file2)

            df1 = process_data(df1_raw, site1)
            df2 = process_data(df2_raw, site2)

            if df1.empty or df2.empty:
                st.error("One of the files is empty or missing required columns (reference, price, availability).")
            else:
                st.session_state.df1 = df1
                st.session_state.df2 = df2
                merged_df = merge_data(df1, df2, site1, site2)
                st.session_state.merged_df = merged_df

        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.info("Ensure the files have columns: categorie, site, url_produit, product_name, reference, price, availability.")

# =========================
# MAIN DASHBOARD
# =========================
if st.session_state.merged_df is not None:
    merged_df = st.session_state.merged_df
    site1 = st.session_state.site1
    site2 = st.session_state.site2

    # ----- SIDEBAR FILTERS -----
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Filters")

    categories = sorted(merged_df['categorie'].dropna().unique().tolist())
    selected_cats = st.sidebar.multiselect("Categories", categories, default=categories)

    stock_statuses = merged_df['stock_status'].unique().tolist()
    selected_stock = st.sidebar.multiselect("Stock Status", stock_statuses, default=stock_statuses)

    # Price range filter
    all_prices = pd.concat([
        merged_df[f'{site1}_price'].dropna(),
        merged_df[f'{site2}_price'].dropna()
    ])
    if len(all_prices) > 0:
        min_p, max_p = float(all_prices.min()), float(all_prices.max())
        price_range = st.sidebar.slider(
            "Price Range",
            min_value=min_p, max_value=max_p,
            value=(min_p, max_p),
            format=f"%.0f {currency}"
        )
    else:
        price_range = (0, 0)

    # Search box
    search_term = st.sidebar.text_input("🔎 Search by Reference or Name", "")

    # Best store filter
    best_store_filter = st.sidebar.multiselect(
        "Best Store (Cheapest)",
        [site1, site2, "Equal", "N/A"],
        default=[site1, site2, "Equal", "N/A"]
    )

    # Apply filters
    filtered_df = merged_df[
        (merged_df['categorie'].isin(selected_cats)) &
        (merged_df['stock_status'].isin(selected_stock)) &
        (merged_df['best_store'].isin(best_store_filter))
    ].copy()

    # Price range filter
    def in_price_range(row):
        p1, p2 = row[f'{site1}_price'], row[f'{site2}_price']
        prices = [p for p in [p1, p2] if not pd.isna(p)]
        if not prices:
            return False
        return price_range[0] <= min(prices) <= price_range[1]

    filtered_df = filtered_df[filtered_df.apply(in_price_range, axis=1)]

    # Search filter
    if search_term:
        mask = (
            filtered_df['reference'].str.contains(search_term, case=False, na=False) |
            filtered_df[f'{site1}_name'].astype(str).str.contains(search_term, case=False, na=False) |
            filtered_df[f'{site2}_name'].astype(str).str.contains(search_term, case=False, na=False)
        )
        filtered_df = filtered_df[mask]

    # ----- TOP ACTION BAR -----
    col_exp1, col_exp2, col_exp3, col_exp4 = st.columns([1, 1, 1, 1])
    with col_exp1:
        st.download_button(
            "📥 Export Full Report (Excel)",
            data=convert_df_to_excel(filtered_df),
            file_name=f"comparison_{site1}_vs_{site2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    with col_exp2:
        st.download_button(
            "📄 Export CSV",
            data=filtered_df.to_csv(index=False).encode('utf-8'),
            file_name=f"comparison_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    with col_exp3:
        if st.button("📊 Show Charts", use_container_width=True):
            st.session_state.show_charts = not st.session_state.get('show_charts', False)
    with col_exp4:
        st.metric("Filtered Results", len(filtered_df))

    # ----- TABS -----
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Dashboard",
        "💰 Price Analysis",
        "📦 Stock Analysis",
        "🗂️ Exclusives",
        "🏆 Best Deals",
        "🔧 Data Quality"
    ])

    # ============== TAB 1: DASHBOARD ==============
    with tab1:
        st.markdown("### 📈 Executive Summary")

        # Metric cards row 1
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(f"Total {site1}", len(st.session_state.df1))
        m2.metric(f"Total {site2}", len(st.session_state.df2))
        common = merged_df.dropna(subset=[f'{site1}_name', f'{site2}_name'])
        m3.metric("Common Products", len(common))
        m4.metric("Categories", len(categories))

        # Metric cards row 2 — price insights
        st.markdown("---")
        n1, n2, n3, n4 = st.columns(4)

        both_prices = merged_df.dropna(subset=[f'{site1}_price', f'{site2}_price'])
        cheaper_1 = len(both_prices[both_prices['best_store'] == site1])
        cheaper_2 = len(both_prices[both_prices['best_store'] == site2])

        n1.metric(f"Cheaper at {site1}", cheaper_1)
        n2.metric(f"Cheaper at {site2}", cheaper_2)
        avg_diff = both_prices['price_diff'].mean() if len(both_prices) > 0 else 0
        n3.metric("Avg Price Diff", f"{avg_diff:.2f} {currency}")
        n4.metric("Total Savings Opp.", f"{both_prices['price_diff'].abs().sum():.0f} {currency}")

        st.markdown("---")

        # Charts row
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.markdown("#### 📦 Stock Distribution")
            stock_counts = filtered_df['stock_status'].value_counts().reset_index()
            stock_counts.columns = ['Status', 'Count']
            if not stock_counts.empty:
                st.bar_chart(stock_counts.set_index('Status'), use_container_width=True)
            else:
                st.info("No data to display.")

        with chart_col2:
            st.markdown(f"#### 🏆 Best Store (Cheapest)")
            best_counts = filtered_df['best_store'].value_counts().reset_index()
            best_counts.columns = ['Store', 'Count']
            if not best_counts.empty:
                st.bar_chart(best_counts.set_index('Store'), use_container_width=True)
            else:
                st.info("No data to display.")

        # Category breakdown
        st.markdown("---")
        st.markdown("#### 📊 Category Breakdown")
        cat_stats = filtered_df.groupby('categorie').agg(
            Total_Products=('reference', 'count'),
            Avg_Price_Site1=(f'{site1}_price', 'mean'),
            Avg_Price_Site2=(f'{site2}_price', 'mean'),
            In_Stock_Site1=(f'{site1}_stock', lambda x: (x == 'In Stock').sum()),
            In_Stock_Site2=(f'{site2}_stock', lambda x: (x == 'In Stock').sum()),
        ).round(2).reset_index()

        st.dataframe(
            cat_stats,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Avg_Price_Site1': st.column_config.NumberColumn(f"Avg {site1} ({currency})", format="%.2f"),
                'Avg_Price_Site2': st.column_config.NumberColumn(f"Avg {site2} ({currency})", format="%.2f"),
            }
        )

    # ============== TAB 2: PRICE ANALYSIS ==============
    with tab2:
        st.markdown(f"### 💰 Price Differences ({site1} vs {site2})")

        st.markdown(f"""
        <div class="metric-card">
            📘 <b>How to read:</b> Positive value → <b>{site1}</b> is more expensive. 
            Negative value → <b>{site2}</b> is more expensive.
        </div>
        """, unsafe_allow_html=True)

        price_diff_df = filtered_df.dropna(subset=[f'{site1}_price', f'{site2}_price']).copy()
        price_diff_df['Price Difference'] = price_diff_df['price_diff'].round(2)

        sort_options = ["Biggest Savings (abs)", f"Most Expensive at {site1}", f"Most Expensive at {site2}", "Highest % Diff"]
        sort_choice = st.selectbox("Sort by", sort_options)

        if sort_choice == "Biggest Savings (abs)":
            price_diff_df = price_diff_df.reindex(price_diff_df['price_diff'].abs().sort_values(ascending=False).index)
        elif sort_choice == f"Most Expensive at {site1}":
            price_diff_df = price_diff_df.sort_values('price_diff', ascending=False)
        elif sort_choice == f"Most Expensive at {site2}":
            price_diff_df = price_diff_df.sort_values('price_diff', ascending=True)
        else:
            price_diff_df = price_diff_df.reindex(price_diff_df['price_diff_pct'].abs().sort_values(ascending=False).index)

        display_cols = [
            'reference', 'categorie',
            f'{site1}_name', f'{site1}_price',
            f'{site2}_name', f'{site2}_price',
            'Price Difference', 'best_store'
        ]
        if show_percentage:
            display_cols.insert(-1, 'price_diff_pct')

        col_conf = {
            f'{site1}_price': st.column_config.NumberColumn(f"{site1} ({currency})", format="%.2f"),
            f'{site2}_price': st.column_config.NumberColumn(f"{site2} ({currency})", format="%.2f"),
            'Price Difference': st.column_config.NumberColumn(f"Diff ({currency})", format="%.2f"),
            'best_store': st.column_config.TextColumn("Best Store"),
        }
        if show_percentage:
            col_conf['price_diff_pct'] = st.column_config.NumberColumn("Diff %", format="%.2f%%")

        st.dataframe(
            price_diff_df[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config=col_conf
        )

        # Top 5 savings
        st.markdown("---")
        st.markdown("#### 🏅 Top 5 Savings Opportunities")
        top_savings = price_diff_df.reindex(price_diff_df['price_diff'].abs().sort_values(ascending=False).index).head(5)
        for _, row in top_savings.iterrows():
            savings = abs(row['price_diff'])
            winner = row['best_store']
            st.markdown(f"""
            <div class="deal-card">
                <b>{row['reference']}</b> — {row[f'{site1}_name'] or row[f'{site2}_name']}<br>
                💰 {site1}: <b>{row[f'{site1}_price']:.2f} {currency}</b> | 
                {site2}: <b>{row[f'{site2}_price']:.2f} {currency}</b><br>
                ✅ Buy at <b>{winner}</b> → Save <b>{savings:.2f} {currency}</b>
            </div>
            """, unsafe_allow_html=True)

    # ============== TAB 3: STOCK ANALYSIS ==============
    with tab3:
        st.markdown("### 📦 Stock Availability Analysis")

        stock_summary = filtered_df['stock_status'].value_counts().reset_index()
        stock_summary.columns = ['Status', 'Count']
        st.dataframe(stock_summary, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### ⚠️ Stock Discrepancies")

        def color_stock(val):
            color = 'green' if val == 'In Stock' else 'red'
            return f'color: {color}; font-weight: bold'

        display_cols_stock = [
            'reference', 'categorie', 'stock_status',
            f'{site1}_name', f'{site1}_stock',
            f'{site2}_name', f'{site2}_stock'
        ]

        stock_diff_df = filtered_df[
            filtered_df['stock_status'].isin([
                f"Only {site1} In Stock",
                f"Only {site2} In Stock",
                "Both Out of Stock"
            ])
        ]

        st.dataframe(
            stock_diff_df[display_cols_stock].style.map(color_stock, subset=[f'{site1}_stock', f'{site2}_stock']),
            use_container_width=True,
            hide_index=True
        )

    # ============== TAB 4: EXCLUSIVES ==============
    with tab4:
        st.markdown("### 🗂️ Exclusive Products")
        st.markdown("Products available in only one store.")

        col_ex1, col_ex2 = st.columns(2)

        with col_ex1:
            st.markdown(f"#### 🔵 Only in {site1}")
            ex1 = filtered_df[filtered_df[f'{site2}_name'].isna()][[
                'reference', 'categorie', f'{site1}_name', f'{site1}_price', f'{site1}_stock'
            ]]
            st.metric("Count", len(ex1))
            st.dataframe(ex1, use_container_width=True, hide_index=True)

        with col_ex2:
            st.markdown(f"#### 🟠 Only in {site2}")
            ex2 = filtered_df[filtered_df[f'{site1}_name'].isna()][[
                'reference', 'categorie', f'{site2}_name', f'{site2}_price', f'{site2}_stock'
            ]]
            st.metric("Count", len(ex2))
            st.dataframe(ex2, use_container_width=True, hide_index=True)

    # ============== TAB 5: BEST DEALS ==============
    with tab5:
        st.markdown("### 🏆 Best Deals Finder")
        st.markdown("Products where you can save the most by choosing the cheaper store.")

        deals_df = filtered_df.dropna(subset=[f'{site1}_price', f'{site2}_price']).copy()
        deals_df['savings'] = (deals_df[f'{site1}_price'] - deals_df[f'{site2}_price']).abs()
        deals_df = deals_df[deals_df['savings'] > 0].sort_values('savings', ascending=False)

        if len(deals_df) > 0:
            st.markdown(f"#### 🎯 Top 10 Deals")
            for i, (_, row) in enumerate(deals_df.head(10).iterrows(), 1):
                winner = row['best_store']
                loser = site2 if winner == site1 else site1
                st.markdown(f"""
                <div class="deal-card">
                    #{i} — <b>{row['reference']}</b><br>
                    {row[f'{site1}_name'] or row[f'{site2}_name']}<br>
                    💡 Buy at <b>{winner}</b> for <b>{row[f'{winner}_price']:.2f} {currency}</b>
                    (instead of {row[f'{loser}_price']:.2f} {currency} at {loser})<br>
                    💰 Save <b>{row['savings']:.2f} {currency}</b>
                    ({row['price_diff_pct']:.1f}%)
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No price differences found.")

    # ============== TAB 6: DATA QUALITY ==============
    with tab6:
        st.markdown("### 🔧 Data Quality Report")

        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Total Rows", len(merged_df))
        q2.metric("Missing Prices", merged_df[[f'{site1}_price', f'{site2}_price']].isna().sum().sum())
        q3.metric("Missing Names", merged_df[[f'{site1}_name', f'{site2}_name']].isna().sum().sum())
        q4.metric("Duplicate Refs", merged_df['reference'].duplicated().sum())

        st.markdown("---")
        st.markdown("#### 📋 Missing Price Report")
        missing_prices = merged_df[
            merged_df[f'{site1}_price'].isna() | merged_df[f'{site2}_price'].isna()
        ][['reference', 'categorie', f'{site1}_price', f'{site2}_price', 'stock_status']]
        st.dataframe(missing_prices, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🔁 Duplicate References")
        dups = merged_df[merged_df['reference'].duplicated(keep=False)].sort_values('reference')
        if len(dups) > 0:
            st.dataframe(dups, use_container_width=True, hide_index=True)
        else:
            st.success("✅ No duplicate references found.")

else:
    st.markdown("""
    <div class="metric-card" style="text-align:center;">
        <h3>👆 Upload both Excel files to begin</h3>
        <p>Required columns: <code>categorie, site, url_produit, product_name, reference, price, availability</code></p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### ✨ Features")
    feat1, feat2, feat3, feat4 = st.columns(4)
    feat1.markdown("📊 **Dashboard**\n\nExecutive summary with KPIs")
    feat2.markdown("💰 **Price Analysis**\n\nDetailed price differences & %")
    feat3.markdown("📦 **Stock Tracker**\n\nReal-time availability comparison")
    feat4.markdown("🏆 **Best Deals**\n\nTop savings opportunities")
