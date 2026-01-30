import pandas as pd
import streamlit as st
import os

# --- 1. ページ設定 ---
st.set_page_config(page_title="Pitch Analysis Dashboard", layout="wide")

# --- 2. パス設定 & データ読み込み ---
current_dir = os.path.dirname(__file__)
file_path = os.path.join(current_dir, "data", "1_29 SBP.csv")

@st.cache_data
def load_data(path):
    if not os.path.exists(path):
        return None
    try:
        data = pd.read_csv(path)
        data = data.dropna(subset=['TaggedPitchType', 'PitchCall', 'Pitcher'])
        
        if 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date']).dt.date

        data['RelSpeed'] = pd.to_numeric(data['RelSpeed'], errors='coerce')
        data['Balls'] = pd.to_numeric(data['Balls'], errors='coerce').fillna(0).astype(int)
        data['Strikes'] = pd.to_numeric(data['Strikes'], errors='coerce').fillna(0).astype(int)
        data['Runner'] = pd.to_numeric(data.get('Runner', 0), errors='coerce').fillna(0).astype(int)
        return data
    except Exception as e:
        st.error(f"読み込みエラー: {e}")
        return None

df = load_data(file_path)

# --- 3. アプリのメイン処理 ---
if df is not None:
    # 指標の計算用フラグ
    strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
    whiff_calls = ['StrikeSwinging']
    swing_calls = ['StrikeSwinging', 'FoulBall', 'InPlay']

    df['is_strike'] = df['PitchCall'].isin(strike_calls).astype(int)
    df['is_swing'] = df['PitchCall'].isin(swing_calls).astype(int)
    df['is_whiff'] = df['PitchCall'].isin(whiff_calls).astype(int)

    st.title("⚾ 投球データ分析ダッシュボード")

    # --- 4. サイドバー設定 ---
    st.sidebar.header("📊 フィルター設定")
    pitcher_list = sorted(df['Pitcher'].unique())
    selected_pitcher = st.sidebar.selectbox("投手を選択", ["すべて"] + pitcher_list)

    if 'Date' in df.columns:
        date_list = sorted(df['Date'].unique())
        selected_date = st.sidebar.selectbox("日付を選択", ["すべて"] + date_list)
    else:
        selected_date = "すべて"

    runner_option = st.sidebar.radio("ランナー状況", ["すべて", "通常 (0)", "クイック (1以上)"])
    
    # --- 5. フィルタリング適用 ---
    plot_df = df.copy()
    if selected_pitcher != "すべて":
        plot_df = plot_df[plot_df['Pitcher'] == selected_pitcher]
    if selected_date != "すべて":
        plot_df = plot_df[plot_df['Date'] == selected_date]
    if runner_option == "通常 (0)":
        plot_df = plot_df[plot_df['Runner'] == 0]
    elif runner_option == "クイック (1以上)":
        plot_df = plot_df[plot_df['Runner'] > 0]

    if plot_df.empty:
        st.warning("条件に一致するデータがありません。")
        st.stop()

    # --- 6. サマリーメトリクス ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("投球数", f"{len(plot_df)} 球")
    col2.metric("平均球速", f"{plot_df['RelSpeed'].mean():.1f} km/h")
    col3.metric("ストライク率", f"{(plot_df['is_strike'].mean() * 100):.1f} %")
    
    total_swings = plot_df['is_swing'].sum()
    whiff_rate = (plot_df['is_whiff'].sum() / total_swings * 100) if total_swings > 0 else 0
    col4.metric("空振り/スイング率", f"{whiff_rate:.1f} %")

    # --- 7. 球種別・スタッツ表 ---
    st.subheader(f"📊 球種別スタッツ")
    summary = plot_df.groupby('TaggedPitchType').agg({
        'RelSpeed': ['count', 'mean', 'max'],
        'is_strike': 'mean',
        'is_swing': 'mean',
        'is_whiff': 'sum'
    })
    summary.columns = ['投球数', '平均球速', '最速', 'ストライク率', 'スイング率', '空振り数']
    summary['投球割合'] = (summary['投球数'] / summary['投球数'].sum() * 100)
    swings_per_pitch = plot_df.groupby('TaggedPitchType')['is_swing'].sum()
    summary['空振り/スイング'] = (summary['空振り数'] / swings_per_pitch * 100).fillna(0)
    summary['ストライク率'] = summary['ストライク率'] * 100
    
    stat_table = summary[['投球数', '投球割合', '平均球速', '最速', 'ストライク率', '空振り/スイング']]
    st.table(stat_table.style.format({
        '投球割合': '{:.1f}%', '平均球速': '{:.1f}', '最速': '{:.1f}', 'ストライク率': '{:.1f}%', '空振り/スイング': '{:.1f}%'
    }))

    # --- 8. カウント別・球種割合グラフ (0件も表示するように修正) ---
    st.subheader("🗓 カウント別 投球割合")
    
    # 1. カウントの文字列を作成
    plot_df['Count'] = plot_df['Balls'].astype(str) + "-" + plot_df['Strikes'].astype(str)
    
    # 2. 表示したい全カウントのリストを定義
    all_counts = ["0-0", "1-0", "2-0", "3-0", "0-1", "1-1", "2-1", "3-1", "0-2", "1-2", "2-2", "3-2"]
    
    # 3. 集計
    count_data = plot_df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
    
    # 4. 不足しているカウントを0で埋めて、順番を固定する
    count_data = count_data.reindex(all_counts, fill_value=0)
    
    # 5. 各カウントの合計が0より大きい場合のみ割合を計算（0除算回避）
    row_sums = count_data.sum(axis=1)
    count_pct = count_data.div(row_sums.replace(0, 1), axis=0) * 100
    
    # 6. 合計が0の行はデータがないことを示すために0のままにする
    count_pct[row_sums == 0] = 0
    
    st.bar_chart(count_pct)

    # --- 9. 球種別・パフォーマンス可視化 ---
    st.subheader("🎯 球種別パフォーマンス比較 (%)")
    st.bar_chart(stat_table[['ストライク率', '空振り/スイング']])

else:
    st.error("データの読み込みに失敗しました。")
