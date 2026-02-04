import streamlit as st
import pandas as pd
import os
import glob
import matplotlib.pyplot as plt

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
    # --- タブ ---
    tab1, tab2 = st.tabs(["📊 総合分析", "🎯 変化量分析"])

    @st.cache_data
    def load_data(folder):
        files = glob.glob(os.path.join(folder, "*.csv"))
        if not files: return None
        df_list = []
        for f in files:
            try:
                tmp = pd.read_csv(f)
                # 列名の空白削除
                tmp.columns = tmp.columns.str.strip()
                df_list.append(tmp)
            except: continue
        if not df_list: return None
        full_df = pd.concat(df_list, axis=0, ignore_index=True)
        # 投手名のクリーニング
        if 'Pitcher' in full_df.columns:
            full_df['Pitcher'] = full_df['Pitcher'].astype(str).str.strip()
        # 日付のクリーニング
        if 'Date' in full_df.columns:
            full_df['Date'] = pd.to_datetime(full_df['Date'], errors='coerce').dt.date
        # 数値変換
        for c in ['RelSpeed', 'Balls', 'Strikes', 'InducedVertBreak', 'HorzBreak', 'PlateLocSide', 'PlateLocHeight']:
            if c in full_df.columns:
                full_df[c] = pd.to_numeric(full_df[c], errors='coerce')
        return full_df

    df_all = load_data("data")

    if df_all is not None:
        # --- TAB 1 ---
        with tab1:
            st.title("⚾ 投球データ総合分析")
            
            # フィルター
            f_col1, f_col2, f_col3 = st.columns(3)
            with f_col1:
                plist = sorted([p for p in df_all['Pitcher'].unique() if p != 'nan'])
                sel_p = st.selectbox("投手を選択", ["すべて"] + plist, key="sel_p1")
            with f_col2:
                dlist = sorted([d for d in df_all['Date'].unique() if pd.notna(d)], reverse=True)
                sel_d = st.selectbox("日付を選択", ["すべて"] + dlist, key="sel_d1")
            with f_col3:
                sel_r = st.radio("ランナー状況", ["すべて", "通常", "クイック"], horizontal=True)

            # フィルタリング
            df = df_all.copy()
            if sel_p != "すべて":
                df = df[df['Pitcher'] == sel_p]
            if sel_d != "すべて":
                df = df[df['Date'] == sel_d]
            
            if not df.empty:
                # 指標計算
                df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']).astype(int)
                df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlay']).astype(int)
                df['is_whiff'] = (df['PitchCall'] == 'StrikeSwinging').astype(int)

                # メトリクス
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("投球数", f"{len(df)} 球")
                m2.metric("平均球速", f"{df['RelSpeed'].mean():.1f} km/h")
                m3.metric("ストライク率", f"{(df['is_strike'].mean()*100):.1f} %")
                sw = df['is_swing'].sum()
                m4.metric("空振り/スイング率", f"{(df['is_whiff'].sum()/sw*100 if sw>0 else 0):.1f} %")

                st.subheader("📊 球種別分析")
                sum_df = df.groupby('TaggedPitchType').agg({
                    'RelSpeed': ['count', 'mean', 'max'],
                    'is_strike': 'mean'
                })
                sum_df.columns = ['数', '平均', '最速', 'ストライク%']
                sum_df['割合%'] = (sum_df['数'] / sum_df['数'].sum() * 100)
                sum_df['ストライク%'] = sum_df['ストライク%'] * 100

                c1, c2 = st.columns([2, 1])
                with c1:
                    # エラー回避: HTMLで表を出力
                    st.write(sum_df.round(1).to_html(classes='table', border=0), unsafe_allow_html=True)
                with c2:
                    # Matplotlibで確実に円グラフを表示
                    fig, ax = plt.subplots(figsize=(4,4))
                    ax.pie(sum_df['数'], labels=sum_df.index, autopct='%1.1f%%', startangle=90)
                    st.pyplot(fig)
            else:
                st.info("データがありません")

        # --- TAB 2 ---
        with tab2:
            st.title("🎯 変化量・位置分析")
            if sel_p == "すべて":
                st.warning("左側の『投手を選択』から、特定の投手を選んでください。")
            else:
                p_df = df.copy() # TAB1のフィルタを引き継ぐ
                if not p_df.empty:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        st.write("**変化量 (cm)**")
                        fig_b, ax_b = plt.subplots()
                        for ptype in p_df['TaggedPitchType'].unique():
                            sub = p_df[p_df['TaggedPitchType'] == ptype]
                            ax_b.scatter(sub['HorzBreak'], sub['InducedVertBreak'], label=ptype, alpha=0.6)
                        ax_b.axhline(0, color='gray', lw=1); ax_b.axvline(0, color='gray', lw=1)
                        ax_b.set_xlim(-60, 60); ax_b.set_ylim(-60, 60)
                        ax_b.legend()
                        st.pyplot(fig_b)
                    with col2_2:
                        st.write("**投球位置 (捕手視点)**")
                        fig_l, ax_l = plt.subplots()
                        for ptype in p_df['TaggedPitchType'].unique():
                            sub = p_df[p_df['TaggedPitchType'] == ptype]
                            ax_l.scatter(sub['PlateLocSide'], sub['PlateLocHeight'], label=ptype, alpha=0.6)
                        # ストライクゾーン枠
                        rect = plt.Rectangle((-0.8, 1.5), 1.6, 2.0, fill=False, color="blue", lw=2)
                        ax_l.add_patch(rect)
                        ax_l.set_xlim(-2, 2); ax_l.set_ylim(0, 5)
                        st.pyplot(fig_l)
