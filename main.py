import pandas as pd
import streamlit as st
import os

# 1. ファイルパスの設定
# GitHub上の構造に合わせて 'data' フォルダの中を指定
file_path = os.path.join('data', '1_29 SBP.csv')

# ファイルの存在確認（エラー時のメッセージを分かりやすく）
if not os.path.exists(file_path):
    st.error(f"❌ ファイルが見つかりません: {file_path}")
    st.info("GitHubのレポジトリ内に 'data' フォルダがあり、その中に '1_29 SBP.csv' があるか確認してください。")
    st.stop()

# 2. データの読み込み
@st.cache_data # 読み込みを高速化
def load_and_clean_data(path):
    data = pd.read_csv(path)
    # 球種(TaggedPitchType)と判定(PitchCall)が空の行を削除
    data = data.dropna(subset=['TaggedPitchType', 'PitchCall'])
    
    # 数値変換（エラーがある場合はNaNに）
    data['RelSpeed'] = pd.to_numeric(data['RelSpeed'], errors='coerce')
    data['Balls'] = pd.to_numeric(data['Balls'], errors='coerce').fillna(0).astype(int)
    data['Strikes'] = pd.to_numeric(data['Strikes'], errors='coerce').fillna(0).astype(int)
    
    # Runner項目があるか確認し、数値を整える
    if 'Runner' in data.columns:
        data['Runner'] = pd.to_numeric(data['Runner'], errors='coerce').fillna(0).astype(int)
        
    return data

df = load_and_clean_data(file_path)

# 3. 指標の計算
# ストライク判定（Trackmanの一般的なコール）
strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
swing_calls = ['StrikeSwinging', 'FoulBall', 'InPlay']

df['is_strike'] = df['PitchCall'].isin(strike_calls).astype(int)
df['is_swing'] = df['PitchCall'].isin(swing_calls).astype(int)

# Fastballとそれ以外を分ける
df['PitchGroup'] = df['TaggedPitchType'].apply(lambda x: 'Fastball' if 'Fastball' in str(x) else 'Offspeed')

# --- 画面表示 ---
st.title("⚾ 投球詳細分析ダッシュボード")

# サイドバー：ランナー状況でフィルタリング
st.sidebar.header("フィルタリング")
if 'Runner' in df.columns:
    runner_option = st.sidebar.radio("ランナー状況 (クイック分析)", ["すべて", "通常 (Runner: 0)", "クイック (Runner: 1以上)"])
    if runner_option == "通常 (Runner: 0)":
        plot_df = df[df['Runner'] == 0]
    elif runner_option == "クイック (Runner: 1以上)":
        plot_df = df[df['Runner'] > 0]
    else:
        plot_df = df
else:
    plot_df = df

# A. 主要指標のサマリー
st.subheader("📌 パフォーマンス指標")
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("平均球速", f"{plot_df['RelSpeed'].mean():.1f} km/h")
with m2:
    st.metric("ストライク率", f"{(plot_df['is_strike'].mean()*100):.1f} %")
with m3:
    st.metric("スイング率", f"{(plot_df['is_swing'].mean()*100):.1f} %")

# B. カウント別・球種割合
st.subheader("📊 カウント別 投球割合")
plot_df['Count'] = plot_df['Balls'].astype(str) + "-" + plot_df['Strikes'].astype(str)
count_order = ["0-0", "1-0", "2-0", "3-0", "0-1", "1-1", "2-1", "3-1", "0-2", "1-2", "2-2", "3-2"]

count_data = plot_df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
existing_order = [c for c in count_order if c in count_data.index]

if existing_order:
    count_data = count_data.reindex(existing_order)
    count_pct = count_data.div(count_data.sum(axis=1), axis=0) * 100
    st.bar_chart(count_pct)
else:
    st.info("現在の条件に合うデータがありません。")

# C. Fastball vs Offspeed の比較
st.subheader("🆚 Fastball vs それ以外")
group_summary = plot_df.groupby('PitchGroup').agg({
    'RelSpeed': 'mean',
    'is_strike': 'mean',
    'is_swing': 'mean'
})
group_summary[['is_strike', 'is_swing']] *= 100
st.table(group_summary.style.format("{:.1f}"))

# D. 全球種詳細
with st.expander("球種ごとの詳細データ"):
    detail = plot_df.groupby('TaggedPitchType').agg({
        'RelSpeed': 'mean',
        'is_strike': 'mean',
        'is_swing': 'mean',
        'PitchNo': 'count'
    }).rename(columns={'PitchNo': '投球数'})
    detail[['is_strike', 'is_swing']] *= 100
    st.dataframe(detail.style.format({"RelSpeed": "{:.1f}", "is_strike": "{:.1f}%", "is_swing": "{:.1f}%"}))
