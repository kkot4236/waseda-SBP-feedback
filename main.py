import pandas as pd
import streamlit as st

# 1. データ読み込みと前処理
df = pd.read_csv('1_29 SBP.csv')
df = df.dropna(subset=['TaggedPitchType', 'PitchCall'])

# 球速を数値に変換（念のため）
df['RelSpeed'] = pd.to_numeric(df['RelSpeed'], errors='coerce')

# Fastballかそれ以外かのフラグ
df['PitchGroup'] = df['TaggedPitchType'].apply(lambda x: 'Fastball' if x == 'Fastball' else 'Offspeed')

# ストライク判定フラグ（CSV内のPitchCallの内容に合わせて調整してください）
strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
swing_calls = ['StrikeSwinging', 'FoulBall', 'InPlay']

df['is_strike'] = df['PitchCall'].isin(strike_calls).astype(int)
df['is_swing'] = df['PitchCall'].isin(swing_calls).astype(int)

# --- 分析セクション ---

# A. クイック(Runnerあり) vs 通常(Runnerなし) の比較
st.header("🏃‍♂️ クイック分析 (Runner有無)")

# Runner項目でグループ化 (0: なし, 1以上: あり)
df['RunnerStatus'] = df['Runner'].apply(lambda x: 'クイック (1以上)' if x > 0 else '通常 (0)')

quick_summary = df.groupby('RunnerStatus').agg({
    'RelSpeed': 'mean',
    'is_strike': 'mean'
})
quick_summary['is_strike'] *= 100 # %表記

col1, col2 = st.columns(2)
col1.metric("平均球速 (全体)", f"{df['RelSpeed'].mean():.1f} km/h")
col2.metric("全体ストライク率", f"{(df['is_strike'].mean()*100):.1f} %")

st.subheader("クイック/通常の比較")
st.dataframe(quick_summary.style.format({"RelSpeed": "{:.1f} km/h", "is_strike": "{:.1f}%"}))

---

# B. 球種別・グループ別指標
st.header("⚾️ 球種別・グループ別パフォーマンス")

# PitchGroup (Fastball/Offspeed) ごとの集計
group_summary = df.groupby(['RunnerStatus', 'PitchGroup']).agg({
    'is_strike': 'mean',
    'is_swing': 'mean',
    'RelSpeed': 'mean'
})
group_summary[['is_strike', 'is_swing']] *= 100

st.subheader("Fastball vs Offspeed (ランナー状況別)")
st.dataframe(group_summary.style.format("{:.1f}"))

# 球種ごとの詳細
st.subheader("球種ごとの詳細（ストライク率・スイング率）")
pitch_detail = df.groupby('TaggedPitchType').agg({
    'is_strike': 'mean',
    'is_swing': 'mean',
    'PitchNo': 'count'
}).rename(columns={'PitchNo': '投球数'})
pitch_detail[['is_strike', 'is_swing']] *= 100

st.bar_chart(pitch_detail[['is_strike', 'is_swing']])
st.table(pitch_detail.style.format({"is_strike": "{:.1f}%", "is_swing": "{:.1f}%"}))