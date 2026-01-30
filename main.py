import pandas as pd
import streamlit as st
import os

# --- 設定 ---
st.set_page_config(page_title="Pitch Analysis", layout="wide")

# ファイルパスを確実に取得
# app.pyが存在するディレクトリからの相対パスで指定
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "data", "1_29 SBP.csv")

st.title("⚾ 投球データ分析")

# --- ファイル読み込み ---
if not os.path.exists(file_path):
    st.error(f"ファイルが見つかりません。現在のパス: {file_path}")
    st.info("GitHub上に 'data' フォルダがあり、その中に '1_29 SBP.csv' があるか確認してください。")
    st.stop()

try:
    # データの読み込み
    df = pd.read_csv(file_path)
    
    # データ掃除（空行対策）
    df = df.dropna(subset=['TaggedPitchType', 'PitchCall'])
    
    # 指標の計算
    df['RelSpeed'] = pd.to_numeric(df['RelSpeed'], errors='coerce')
    df['is_strike'] = df['PitchCall'].isin(['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']).astype(int)
    df['is_swing'] = df['PitchCall'].isin(['StrikeSwinging', 'FoulBall', 'InPlay']).astype(int)
    
    # ランナー・カウントの処理
    df['Runner'] = pd.to_numeric(df.get('Runner', 0), errors='coerce').fillna(0).astype(int)
    df['Balls'] = pd.to_numeric(df['Balls'], errors='coerce').fillna(0).astype(int)
    df['Strikes'] = pd.to_numeric(df['Strikes'], errors='coerce').fillna(0).astype(int)

    # --- フィルタリング ---
    runner_option = st.sidebar.radio("ランナー状況", ["すべて", "通常 (0)", "クイック (1以上)"])
    plot_df = df.copy()
    if runner_option == "通常 (0)":
        plot_df = df[df['Runner'] == 0]
    elif runner_option == "クイック (1以上)":
        plot_df = df[df['Runner'] > 0]

    # --- 表示 ---
    col1, col2, col3 = st.columns(3)
    col1.metric("平均球速", f"{plot_df['RelSpeed'].mean():.1f} km/h")
    col2.metric("ストライク率", f"{(plot_df['is_strike'].mean()*100):.1f} %")
    col3.metric("スイング率", f"{(plot_df['is_swing'].mean()*100):.1f} %")

    st.subheader("📊 カウント別・球種割合 (%)")
    plot_df['Count'] = plot_df['Balls'].astype(str) + "-" + plot_df['Strikes'].astype(str)
    count_data = plot_df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
    
    # 割合計算と表示
    if not count_data.empty:
        st.bar_chart(count_data.div(count_data.sum(axis=1), axis=0) * 100)

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
