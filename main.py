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
    # --- タブの作成 ---
    tab1, tab2 = st.tabs(["📊 投球・カウント分析", "🎯 変化量・リリース分析"])

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
            
            # データクレンジング
            data = data.dropna(subset=['TaggedPitchType', 'PitchCall', 'Pitcher'])
            data['Pitcher'] = data['Pitcher'].astype(str).str.strip() # 空白除去
            
            if 'Date' in data.columns:
                data['Date'] = pd.to_datetime(data['Date']).dt.date
            
            # 数値変換
            for col in ['RelSpeed', 'Balls', 'Strikes']:
                if col in data.columns: 
                    data[col] = pd.to_numeric(data[col], errors='coerce')
            
            return data

        df1 = load_data_t1("data")
        
        if df1 is not None:
            st.title("⚾ 投球データ総合分析")
            
            # --- フィルターエリア ---
            f1_col1, f1_col2, f1_col3 = st.columns(3)
            with f1_col1:
                p_list = sorted(df1['Pitcher'].unique().tolist())
                sel_p1 = st.selectbox("投手を選択", ["すべて"] + p_list, key="t1_p_sel")
            with f1_col2:
                d_list = sorted(df1['Date'].unique().tolist(), reverse=True)
                sel_d1 = st.selectbox("日付を選択", ["すべて"] + d_list, key="t1_d_sel")
            with f1_col3:
                sel_r1 = st.radio("ランナー状況", ["すべて", "通常", "クイック"], horizontal=True, key="t1_r_sel")

            # フィルタ適用 (確実に一致させるため strip を使用)
            pdf1 = df1.copy()
            if sel_p1 != "すべて":
                pdf1 = pdf1[pdf1['Pitcher'] == sel_p1]
            if sel_d1 != "すべて":
                pdf1 = pdf1[pdf1['Date'] == sel_d1]
            
            if "通常" in sel_r1:
                if 'has_runner' in pdf1.columns: pdf1 = pdf1[pdf1['has_runner'] == 0]
            elif "クイック" in sel_r1:
                if 'has_runner' in pdf1.columns: pdf1 = pdf1[pdf1['has_runner'] == 1]

            if not pdf1.empty:
                # 指標計算
                strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
                pdf1['is_strike'] = pdf1['PitchCall'].isin(strike_calls).astype(int)
                pdf1['is_swing'] = pdf1['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlay']).astype(int)
                pdf1['is_whiff'] = (pdf1['PitchCall'] == 'StrikeSwinging').astype(int)

                # メトリクス
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("投球数", f"{len(pdf1)} 球")
                m2.metric("平均球速", f"{pdf1['RelSpeed'].mean():.1f} km/h")
                m3.metric("ストライク率", f"{(pdf1['is_strike'].mean()*100):.1f} %")
                swings = pdf1['is_swing'].sum()
                m4.metric("空振り/スイング率", f"{(pdf1['is_whiff'].sum()/swings*100 if swings>0 else 0):.1f} %")

                st.markdown("---")
                
                # 集計
                sum1 = pdf1.groupby('TaggedPitchType').agg({
                    'RelSpeed': ['count', 'mean', 'max'],
                    'is_strike': 'mean',
                    'is_whiff': 'sum',
                    'is_swing': 'sum'
                })
                sum1.columns = ['投球数', '平均球速', '最速', 'ストライク率', '空振り', 'スイング']
                sum1['投球割合'] = (sum1['投球数'] / sum1['投球数'].sum() * 100)
                sum1['空振り/スイング'] = (sum1['空振り'] / sum1['スイング'] * 100).fillna(0)
                sum1['ストライク率'] = sum1['ストライク率'] * 100

                c1, c2 = st.columns([2, 1])
                with c1:
                    # エラー対策: 数値を文字列に変換しつつフォーマット
                    display_df = sum1[['投球数', '投球割合', '平均球速', '最速', 'ストライク率', '空振り/スイング']].copy()
                    for col in display_df.columns:
                        display_df[col] = display_df[col].map('{:.1f}'.format)
                    st.dataframe(display_df, use_container_width=True)
                with c2:
                    # 円グラフのデータソースを明示
                    fig_pie = px.pie(sum1.reset_index(), values='投球数', names='TaggedPitchType')
                    fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("選択された条件に該当するデータがありません。")

    # ---------------------------------------------------------
    # TAB 2: 変化量・リリース分析
    # ---------------------------------------------------------
    with tab2:
        # タブ2も同様にフィルタリング処理を強化
        df2 = load_data_t1("data") # 同じデータソースを使用
        if df2 is not None:
            st.title("🎯 変化量・詳細分析")
            f2_1, f2_2 = st.columns(2)
            with f2_1:
                sel_d2 = st.selectbox("日付を選択", sorted(df2['Date'].unique(), reverse=True), key="t2_d_sel")
            with f2_2:
                d_df2 = df2[df2['Date'] == sel_d2]
                sel_p2 = st.selectbox("投手を選択", sorted(d_df2['Pitcher'].unique()), key="t2_p_sel")
            
            p_df2 = d_df2[d_df2['Pitcher'] == sel_p2].copy()
            
            if not p_df2.empty and 'InducedVertBreak' in p_df2.columns:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    fig_b = px.scatter(p_df2, x='HorzBreak', y='InducedVertBreak', color='TaggedPitchType', range_x=[-80, 80], range_y=[-80, 80])
                    fig_b.add_hline(y=0, line_color="gray"); fig_b.add_vline(x=0, line_color="gray")
                    st.plotly_chart(fig_b, use_container_width=True)
                with col2_2:
                    fig_l = px.scatter(p_df2, x='PlateLocSide', y='PlateLocHeight', color='TaggedPitchType', range_x=[-100, 100], range_y=[0, 200])
                    fig_l.add_shape(type="rect", x0=-25, y0=45, x1=25, y1=105, line=dict(color="RoyalBlue", width=2))
                    st.plotly_chart(fig_l, use_container_width=True)
