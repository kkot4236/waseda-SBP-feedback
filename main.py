import pandas as pd
import streamlit as st

# ファイル読み込み
try:
    df = pd.read_csv('1_29 SBP.csv')

    # --- データ掃除 (ここがエラー回避のポイント) ---
    # 1. 球種(TaggedPitchType)が入っていない行（空行など）を完全に消す
    df = df.dropna(subset=['TaggedPitchType'])
    
    # 2. 球速を数値に変換（エラーになる文字があれば無視する）
    df['RelSpeed'] = pd.to_numeric(df['RelSpeed'], errors='coerce')
    
    # 3. カウントの欠損値を0で埋める
    df['Balls'] = df['Balls'].fillna(0).astype(int)
    df['Strikes'] = df['Strikes'].fillna(0).astype(int)
    
    # --- 指標の計算準備 ---
    # Fastballかそれ以外か
    df['PitchGroup'] = df['TaggedPitchType'].apply(lambda x: 'Fastball' if 'Fastball' in str(x) else 'Offspeed')

    # ストライク/スイング判定
    strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
    swing_calls = ['StrikeSwinging', 'FoulBall', 'InPlay']
    df['is_strike'] = df['PitchCall'].isin(strike_calls).astype(int)
    df['is_swing'] = df['PitchCall'].isin(swing_calls).astype(int)

    # --- アプリ画面の構築 ---
    st.title("⚾ 投球データ分析ダッシュボード")

    # サイドバーでランナー状況を選択
    runner_option = st.sidebar.radio("ランナー状況", ["すべて", "ランナーなし (0)", "クイック (1以上)"])
    
    plot_df = df.copy()
    if runner_option == "ランナーなし (0)":
        plot_df = df[df['Runner'] == 0]
    elif runner_option == "クイック (1以上)":
        plot_df = df[df['Runner'] > 0]

    # ① クイック/通常の比較メトリクス
    col1, col2, col3 = st.columns(3)
    avg_speed = plot_df['RelSpeed'].mean()
    strike_rate = plot_df['is_strike'].mean() * 100
    swing_rate = plot_df['is_swing'].mean() * 100

    col1.metric("平均球速", f"{avg_speed:.1f} km/h")
    col2.metric("ストライク率", f"{strike_rate:.1f} %")
    col3.metric("スイング率", f"{swing_rate:.1f} %")

    # ② カウント別投球割合グラフ
    st.subheader("📊 カウント別・球種割合")
    plot_df['Count'] = plot_df['Balls'].astype(str) + "-" + plot_df['Strikes'].astype(str)
    count_order = ["0-0", "1-0", "2-0", "3-0", "0-1", "1-1", "2-1", "3-1", "0-2", "1-2", "2-2", "3-2"]
    
    count_data = plot_df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
    existing_order = [c for c in count_order if c in count_data.index]
    if existing_order:
        count_data = count_data.reindex(existing_order)
        count_pct = count_data.div(count_data.sum(axis=1), axis=0) * 100
        st.bar_chart(count_pct)
    else:
        st.write("データがありません")

    # ③ 球種グループ別の詳細
    st.subheader("🎯 Fastball vs Offspeed 指標")
    group_summary = plot_df.groupby('PitchGroup').agg({
        'RelSpeed': 'mean',
        'is_strike': 'mean',
        'is_swing': 'mean'
    })
    group_summary[['is_strike', 'is_swing']] *= 100
    st.table(group_summary.style.format("{:.1f}"))

except Exception as e:
    st.error(f"エラーが発生しました: {e}")
    st.info("CSVファイル名が '1_29 SBP.csv' かどうか、またはファイルが壊れていないか確認してください。")
