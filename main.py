import streamlit as st
import pandas as pd
import os
import glob
import plotly.express as px

# --- 1. ページ設定 ---
st.set_page_config(page_title="Waseda Pitcher Analytics", layout="wide")

# --- 2. パスワード設定 ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = None
    if st.session_state["password_correct"] == True: return True
    
    def password_entered():
        if st.session_state.get("password_input") == "wbc1901":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False
            
    st.title("⚾️ 早稲田大学野球部 投手分析システム")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    return False

if check_password():
    # --- デザインCSS (画像のようなスッキリした見た目) ---
    st.markdown("""
        <style>
        div[data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; }
        .stTabs [data-baseweb="tab-list"] { gap: 24px; }
        .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-size: 16px; }
        </style>
    """, unsafe_allow_html=True)

    # --- メインタブ ---
    tab1, tab2 = st.tabs(["📊 投球データ総合分析", "🎯 変化量・リリース分析"])

    # ---------------------------------------------------------
    # TAB 1: 投球・カウント分析
    # ---------------------------------------------------------
    with tab1:
        @st.cache_data
        def load_data_t1(folder_path):
            all_files = glob.glob(os.path.join(folder_path, "*.csv"))
            if not all_files: return None
            df_list = []
            for f in all_files:
                try:
                    tmp = pd.read_csv(f)
                    df_list.append(tmp)
                except: continue
            if not df_list: return None
            data = pd.concat(df_list, axis=0, ignore_index=True)
            data = data.dropna(subset=['TaggedPitchType', 'PitchCall', 'Pitcher'])
            if 'Date' in data.columns:
                data['Date'] = pd.to_datetime(data['Date']).dt.date
            if 'Runner' in data.columns:
                data['has_runner'] = data['Runner'].apply(lambda x: 0 if pd.isna(x) or str(x).strip().lower() in ['0', '0.0', 'none', '', 'nan'] else 1)
            else: data['has_runner'] = 0
            for col in ['RelSpeed', 'Balls', 'Strikes']:
                if col in data.columns: data[col] = pd.to_numeric(data[col], errors='coerce')
            return data

        df1 = load_data_t1("data")
        
        if df1 is not None:
            st.title("⚾ 投球データ総合分析")
            
            # --- フィルターエリア (メイン画面上部) ---
            f1_col1, f1_col2, f1_col3 = st.columns(3)
            with f1_col1:
                sel_p1 = st.selectbox("投手を選択", ["すべて"] + sorted(df1['Pitcher'].unique().tolist()), key="t1_p")
            with f1_col2:
                sel_d1 = st.selectbox("日付を選択", ["すべて"] + sorted(df1['Date'].unique().tolist(), reverse=True), key="t1_d")
            with f1_col3:
                sel_r1 = st.radio("ランナー状況", ["すべて", "通常", "クイック"], horizontal=True, key="t1_r")

            # フィルタ適用
            pdf1 = df1.copy()
            if sel_p1 != "すべて": pdf1 = pdf1[pdf1['Pitcher'] == sel_p1]
            if sel_d1 != "すべて": pdf1 = pdf1[pdf1['Date'] == sel_d1]
            if "通常" in sel_r1: pdf1 = pdf1[pdf1['has_runner'] == 0]
            elif "クイック" in sel_r1: pdf1 = pdf1[pdf1['has_runner'] == 1]

            if not pdf1.empty:
                # 指標計算
                strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
                pdf1['is_strike'] = pdf1['PitchCall'].isin(strike_calls).astype(int)
                pdf1['is_swing'] = pdf1['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlay']).astype(int)
                pdf1['is_whiff'] = (pdf1['PitchCall'] == 'StrikeSwinging').astype(int)

                # メトリクス (4列)
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("投球数", f"{len(pdf1)} 球")
                m2.metric("平均球速", f"{pdf1['RelSpeed'].mean():.1f} km/h")
                m3.metric("ストライク率", f"{(pdf1['is_strike'].mean()*100):.1f} %")
                swings = pdf1['is_swing'].sum()
                m4.metric("空振り/スイング率", f"{(pdf1['is_whiff'].sum()/swings*100 if swings>0 else 0):.1f} %")

                st.markdown("---")
                st.subheader("📊 球種別分析")
                
                # 集計
                sum1 = pdf1.groupby('TaggedPitchType').agg({
                    'RelSpeed': ['count', 'mean', 'max'],
                    'is_strike': 'mean', 'is_whiff': 'sum', 'is_swing': 'sum'
                })
                sum1.columns = ['投球数', '平均球速', '最速', 'ストライク率', '空振り', 'スイング']
                sum1['投球割合'] = (sum1['投球数'] / sum1['投球数'].sum() * 100)
                sum1['空振り/スイング'] = (sum1['空振り'] / sum1['スイング'] * 100).fillna(0)
                sum1['ストライク率'] = sum1['ストライク率'] * 100

                # レイアウト (表2:円1)
                c1, c2 = st.columns([2, 1])
                with c1:
                    display_df = sum1[['投球数', '投球割合', '平均球速', '最速', 'ストライク率', '空振り/スイング']].round(1)
                    st.dataframe(display_df.astype(str), use_container_width=True) # 文字列変換でLargeUtf8エラー回避
                with c2:
                    fig_pie = px.pie(sum1.reset_index(), values='投球数', names='TaggedPitchType')
                    fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)

                st.subheader("🗓 カウント別 投球割合")
                pdf1['Count'] = pdf1['Balls'].fillna(0).astype(int).astype(str) + "-" + pdf1['Strikes'].fillna(0).astype(int).astype(str)
                cnt_data = pdf1.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
                st.bar_chart(cnt_data.div(cnt_data.sum(axis=1), axis=0) * 100)
            else:
                st.warning("データがありません")

    # ---------------------------------------------------------
    # TAB 2: 変化量・リリース分析
    # ---------------------------------------------------------
    with tab2:
        @st.cache_data
        def load_data_t2():
            all_data = []
            if os.path.exists("data"):
                for f in os.listdir("data"):
                    if f.endswith(('.csv', '.xlsx')):
                        try:
                            tmp = pd.read_excel(os.path.join("data", f)) if f.endswith('.xlsx') else pd.read_csv(os.path.join("data", f))
                            tmp.columns = tmp.columns.str.strip()
                            col_map = {'Pitcher First Name': 'Player', 'Pitch Created At': 'Date', 'RelSpeed (KMH)': 'Velo', 'Pitch Type': 'PitchType', 'InducedVertBreak (CM)': 'IVB', 'HorzBreak (CM)': 'HB', 'PlateLocSide (CM)': 'LocX', 'PlateLocHeight (CM)': 'LocY'}
                            for old, new in col_map.items():
                                if old in tmp.columns:
                                    if new == 'Date': tmp[new] = pd.to_datetime(tmp[old], errors='coerce').dt.date
                                    else: tmp[new] = pd.to_numeric(tmp[old], errors='coerce') if new not in ['Player', 'PitchType'] else tmp[old]
                            all_data.append(tmp.dropna(subset=['Player', 'Date', 'Velo']))
                        except: continue
            return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

        df2 = load_data_t2()
        if not df2.empty:
            st.title("🎯 変化量・詳細分析")
            f2_col1, f2_col2 = st.columns(2)
            with f2_col1:
                sel_d2 = st.selectbox("日付を選択", sorted(df2['Date'].unique(), reverse=True), key="t2_d")
            with f2_col2:
                d_df2 = df2[df2['Date'] == sel_d2]
                sel_p2 = st.selectbox("投手を選択", sorted(d_df2['Player'].unique()), key="t2_p")
            
            p_df2 = d_df2[d_df2['Player'] == sel_p2].copy()

            col2_1, col2_2 = st.columns(2)
            with col2_1:
                fig_b = px.scatter(p_df2, x='HB', y='IVB', color='PitchType', range_x=[-80, 80], range_y=[-80, 80], title="変化量 (cm)")
                fig_b.add_hline(y=0, line_color="gray"); fig_b.add_vline(x=0, line_color="gray")
                st.plotly_chart(fig_b, use_container_width=True)
            with col2_2:
                fig_l = px.scatter(p_df2, x='LocX', y='LocY', color='PitchType', range_x=[-100, 100], range_y=[0, 200], title="投球位置")
                fig_l.add_shape(type="rect", x0=-25, y0=45, x1=25, y1=105, line=dict(color="RoyalBlue", width=2))
                st.plotly_chart(fig_l, use_container_width=True)
