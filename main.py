import streamlit as st
import pandas as pd
import os
import glob
import matplotlib.pyplot as plt

# --- 1. ページ設定 ---
st.set_page_config(page_title="Waseda Pitcher Analytics", layout="wide")

# 球種の表示順序
CATEGORY_ORDER = ["Fastball", "Slider", "Cutter", "Curveball", "Splitter", "ChangeUp", "OneSeam", "TwoSeamFastball"]

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
            
    st.title("⚾️ 早稲田大学野球部 分析システム")
    st.text_input("パスワードを入力してください", type="password", on_change=password_entered, key="password_input")
    return False

if check_password():
    # テーブルデザインCSS
    st.markdown("""
        <style>
        .p-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; border: 1px solid #dee2e6; background-color: white; color: #333; }
        .p-table th { background-color: #f8f9fa; padding: 12px; border: 1px solid #dee2e6; font-weight: bold; text-align: center; color: #333 !important; }
        .p-table td { padding: 12px; border: 1px solid #dee2e6; text-align: center; font-weight: bold; color: #333 !important; }
        .p-table thead tr th:first-child { color: transparent !important; }
        </style>
    """, unsafe_allow_html=True)

    @st.cache_data
    def load_data(folder):
        files = glob.glob(os.path.join(folder, "*.csv"))
        if not files: return None
        df_list = []
        for f in files:
            try:
                tmp = pd.read_csv(f, dtype=str)
                tmp.columns = tmp.columns.str.strip()
                df_list.append(tmp)
            except: continue
        if not df_list: return None
        full_df = pd.concat(df_list, axis=0, ignore_index=True)
        
        name_col = next((c for c in ['Pitcher', 'Batter', 'Player'] if c in full_df.columns), None)
        full_df['PlayerName'] = full_df[name_col].fillna('Unknown').astype(str).str.strip() if name_col else 'Unknown'

        # 数値変換（Balls, Strikesを含む）
        num_cols = ['RelSpeed', 'InducedVertBreak', 'HorzBreak', 'PlateLocSide', 'PlateLocHeight', 'Balls', 'Strikes']
        for c in num_cols:
            if c in full_df.columns:
                full_df[c] = pd.to_numeric(full_df[c], errors='coerce')
        
        if 'Date' in full_df.columns:
            full_df['Date'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.date
        return full_df

    df_all = load_data("data")

    if df_all is not None:
        st.write("### 🔍 絞り込み条件")
        c1, c2, c3 = st.columns(3)
        with c1:
            plist = sorted([str(p) for p in df_all['PlayerName'].unique() if p not in ['nan', 'Unknown']])
            sel_p = st.selectbox("選手を選択", ["すべて"] + plist, key="global_p")
        with c2:
            dlist = sorted([d for d in df_all['Date'].unique() if pd.notna(d)], reverse=True)
            sel_d = st.selectbox("日付を選択", ["すべて"] + dlist, key="global_d")
        with c3:
            sel_r = st.radio("ランナー状況", ["すべて", "通常", "クイック"], horizontal=True)

        df = df_all.copy()
        if sel_p != "すべて": df = df[df['PlayerName'] == sel_p]
        if sel_d != "すべて": df = df[df['Date'] == sel_d]

        # カウント文字列の作成 (例: "0-0")
        if 'Balls' in df.columns and 'Strikes' in df.columns:
            df['Count'] = df['Balls'].fillna(0).astype(int).astype(str) + "-" + df['Strikes'].fillna(0).astype(int).astype(str)

        t1, t2 = st.tabs(["📊 総合分析", "🎯 変化量分析"])

        with t1:
            if not df.empty and 'PitchCall' in df.columns:
                df['is_strike'] = df['PitchCall'].fillna('').str.contains('Strike|Foul|InPlay', case=False).astype(int)
                df['is_swing'] = df['PitchCall'].fillna('').str.contains('StrikeSwinging|Foul|InPlay', case=False).astype(int)
                df['is_whiff'] = df['PitchCall'].fillna('').str.contains('StrikeSwinging', case=False).astype(int)
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("投球数", f"{len(df)} 球")
                m2.metric("平均球速", f"{df['RelSpeed'].mean():.1f} km/h" if 'RelSpeed' in df.columns else "N/A")
                m3.metric("ストライク率", f"{(df['is_strike'].mean()*100):.1f} %")
                sw = df['is_swing'].sum()
                m4.metric("空振り/スイング率", f"{(df['is_whiff'].sum()/sw*100):.1f} %" if sw > 0 else "0.0 %")

                if 'TaggedPitchType' in df.columns:
                    st.subheader("📊 球種別データ")
                    sum_df = df.groupby('TaggedPitchType').agg({
                        'PitchCall': 'count',
                        'RelSpeed': ['mean', 'max'],
                        'is_strike': 'mean',
                        'is_whiff': 'sum',
                        'is_swing': 'sum'
                    })
                    sum_df.columns = ['投球数', '平均球速', '最大球速', 'ストライク率', '空振り', 'スイング']
                    sum_df['ストライク率'] = (sum_df['ストライク率'] * 100).round(1)
                    sum_df['空振り/スイング'] = (sum_df['空振り'] / sum_df['スイング'] * 100).fillna(0).round(1)
                    
                    final_df = sum_df[['投球数', '平均球速', '最大球速', 'ストライク率', '空振り/スイング']].copy()
                    final_df['平均球速'] = final_df['平均球速'].round(1)
                    final_df['最大球速'] = final_df['最大球速'].round(1)
                    
                    order = [c for c in CATEGORY_ORDER if c in final_df.index] + [c for c in final_df.index if c not in CATEGORY_ORDER]
                    final_df = final_df.reindex(order)

                    col_l, col_r = st.columns([2, 1])
                    with col_l:
                        st.write(final_df.to_html(classes='p-table', index_names=False), unsafe_allow_html=True)
                    with col_r:
                        st.markdown("<h4 style='text-align: center;'>投球割合</h4>", unsafe_allow_html=True)
                        fig_pie, ax_pie = plt.subplots(figsize=(5,5))
                        ax_pie.pie(final_df['投球数'].fillna(0), labels=final_df.index, autopct='%1.1f%%', startangle=90, counterclock=False)
                        st.pyplot(fig_pie)

                    # --- カウント別投球割合グラフ ---
                    if 'Count' in df.columns:
                        st.markdown("---")
                        st.subheader("📈 カウント別投球割合")
                        
                        # カウントごとの球種を集計
                        count_pivot = df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
                        # 割合に変換
                        count_ratio = count_pivot.div(count_pivot.sum(axis=1), axis=0) * 100
                        
                        # グラフ描画
                        fig_bar, ax_bar = plt.subplots(figsize=(10, 6))
                        count_ratio.plot(kind='bar', stacked=True, ax=ax_bar)
                        ax_bar.set_ylabel("割合 (%)")
                        ax_bar.set_xlabel("カウント (Ball-Strike)")
                        ax_bar.legend(title="球種", bbox_to_anchor=(1.05, 1), loc='upper left')
                        plt.xticks(rotation=0)
                        st.pyplot(fig_bar)
            else:
                st.info("データがありません。")

        with t2:
            if not df.empty and 'HorzBreak' in df.columns:
                st.subheader("🎯 変化量マップ")
                fig_m, ax_m = plt.subplots()
                for pt in order:
                    if pt in df['TaggedPitchType'].unique():
                        sub = df[df['TaggedPitchType'] == pt]
                        ax_m.scatter(sub['HorzBreak'], sub['InducedVertBreak'], label=pt, alpha=0.6)
                ax_m.axhline(0, color='gray', lw=1); ax_m.axvline(0, color='gray', lw=1)
                ax_m.set_xlabel("Horizontal Break (cm)"); ax_m.set_ylabel("Vertical Break (cm)")
                ax_m.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                st.pyplot(fig_m)
