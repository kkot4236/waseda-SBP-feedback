import pandas as pd
import streamlit as st
import os

# ページの初期設定（最初に行う必要があります）
st.set_page_config(page_title="Baseball Analytics", layout="wide")

# 1. パスの指定
# GitHubのレポジトリのルートにある 'data' フォルダの中のファイルを指定
BASE_DIR = os.path.dirname(__file__) # app.pyがある場所を取得
FILE_PATH = os.path.join(BASE_DIR, 'data', '1_29 SBP.csv')

st.title("⚾ 投球データ分析ダッシュボード")

# 2. ファイルの存在チェックと読み込み
if os.path.exists(FILE_PATH):
    try:
        df = pd.read_csv(FILE_PATH)
        # 空の行（CSV後半のデータがない部分）を削除
        df = df.dropna(subset=['TaggedPitchType', 'PitchCall'])
        
        # 数値データのクレンジング
        df['RelSpeed'] = pd.to_numeric(df['RelSpeed'], errors='coerce')
        df['Balls'] = pd.to_numeric(df['Balls'], errors='coerce').fillna(0).astype(int)
        df['Strikes'] = pd.to_numeric(df['Strikes'], errors='coerce').fillna(0).astype(int)
        df['Runner'] = pd.to_numeric(df.get('Runner', 0), errors='coerce').fillna(0).astype(int)

        # 指標作成
        strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
        swing_calls = ['StrikeSwinging', 'FoulBall', 'InPlay']
        df['is_strike'] = df['PitchCall'].isin(strike_calls).astype(int)
        df['is_swing'] = df['PitchCall'].isin(swing_calls).astype(int)
        df['PitchGroup'] = df['TaggedPitchType'].apply(lambda x: 'Fastball' if 'Fastball' in str(x) else 'Offspeed')

        # --- 表示部分 ---
        # ランナーフィルター
        runner_option = st.sidebar.radio("ランナー状況", ["すべて", "通常 (0)", "クイック (1以上)"])
        plot_df = df.copy()
        if runner_option == "通常 (0)":
            plot_df = df[df['Runner'] == 0]
        elif runner_option == "クイック (1以上)":
            plot_df = df[df['Runner'] > 0]

        # 指標
        c1, c2, c3 = st.columns(3)
        c1.metric("平均球速", f"{plot_df['RelSpeed'].mean():.1f} km/h")
        c2.metric("ストライク率", f"{(plot_df['is_strike'].mean()*100):.1f} %")
        c3.metric("スイング率", f"{(plot_df['is_swing'].mean()*100):.1f} %")

        # カウント別グラフ
        st.subheader("📊 カウント別・球種割合")
        plot_df['Count'] = plot_df['Balls'].astype(str) + "-" + plot_df['Strikes'].astype(str)
        count_order = ["0-0", "1-0", "2-0", "3-0", "0-1", "1-1", "2-1", "3-1", "0-2", "1-2", "2-2", "3-2"]
        count_data = plot_df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
        existing_order = [c for c in count_order if c in count_data.index]
        
        if existing_order:
            st.bar_chart(count_data.reindex(existing_order).div(count_data.sum(axis=1), axis=0) * 100)

    except Exception as e:
        st.error(f"データの読み込み中にエラーが発生しました: {e}")
else:
    st.error(f"❌ ファイルが見つかりません。")
    st.write(f"期待している場所: `{FILE_PATH}`")
    st.write("GitHub上に 'data' というフォルダがあり、その中に正しくファイルがあるか確認してください。")
