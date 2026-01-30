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
        # 球種と判定が空の行を削除（CSV末尾の空行対策）
        data = data.dropna(subset=['TaggedPitchType', 'PitchCall'])
        
        # 型変換とクレンジング
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
    # 指標の計算
    strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']
    swing_calls = ['StrikeSwinging', 'FoulBall', 'InPlay']
    df['is_strike'] = df['PitchCall'].isin(strike_calls).astype(int)
    df['is_swing'] = df['PitchCall'].isin(swing_calls).astype(int)
    df['PitchGroup'] = df['TaggedPitchType'].apply(lambda x: 'Fastball' if 'Fastball' in str(x) else 'Offspeed')

    st.title("⚾ 投球詳細分析ダッシュボード")

    # --- 4. サイドバー設定 ---
    st.sidebar.header("表示フィルター")
    runner_option = st.sidebar.radio("ランナー状況", ["すべて", "通常 (Runner: 0)", "クイック (Runner: 1以上)"])
    
    # フィルタリング適用
    plot_df = df.copy()
    if runner_option == "通常 (Runner: 0)":
        plot_df = df[df['Runner'] == 0]
    elif runner_option == "クイック (Runner: 1以上)":
        plot_df = df[df['Runner'] > 0]

    # --- 5. サマリーメトリクス ---
    col1, col2, col3 = st.columns(3)
    col1.metric("平均球速", f"{plot_df['RelSpeed'].mean():.1f} km/h")
    col2.metric("ストライク率", f"{(plot_df['is_strike'].mean()*100):.1f} %")
    col3.metric("スイング率", f"{(plot_df['is_swing'].mean()*100):.1f} %")

    # --- 6. 球速一覧表（詳細） ---
    st.subheader("📋 投球一覧表")
    # 表示用のデータフレームを作成
    display_list = plot_df[['PitchNo', 'TaggedPitchType', 'RelSpeed', 'Balls', 'Strikes', 'PitchCall']].copy()
    display_list.columns = ['No', '球種', '球速(km/h)', 'B', 'S', '判定']
    
    st.dataframe(
        display_list.sort_values(by='No'),
        column_config={
            "球速(km/h)": st.column_config.NumberColumn(format="%.1f"),
            "No": st.column_config.NumberColumn(format="%d"),
        },
        hide_index=True,
        use_container_width=True
    )

    # --- 7. 球種別 球速サマリー表 ---
    st.subheader("🚀 球種別の球速統計")
    speed_summary = plot_df.groupby('TaggedPitchType')['RelSpeed'].agg(['count', 'mean', 'max', 'min']).reset_index()
    speed_summary.columns = ['球種', '投球数', '平均', '最速', '最遅']
    st.table(speed_summary.style.format({
        '平均': '{:.1f} km/h', '最速': '{:.1f} km/h', '最遅': '{:.1f} km/h'
    }))

    # --- 8. カウント別・球種割合グラフ ---
    st.subheader("📊 カウント別 投球割合")
    plot_df['Count'] = plot_df['Balls'].astype(str) + "-" + plot_df['Strikes'].astype(str)
    count_order = ["0-0", "1-0", "2-0", "3-0", "0-1", "1-1", "2-1", "3-1", "0-2", "1-2", "2-2", "3-2"]
    
    count_data = plot_df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)
    existing_order = [c for c in count_order if c in count_data.index]
    
    if existing_order:
        count_pct = count_data.reindex(existing_order).div(count_data.sum(axis=1), axis=0) * 100
        st.bar_chart(count_pct)
    else:
        st.info("データがありません")

    # --- 9. 球種別パフォーマンス指標 ---
    st.subheader("🎯 球種別 ストライク率・スイング率")
    performance = plot_df.groupby('TaggedPitchType').agg({
        'is_strike': 'mean',
        'is_swing': 'mean'
    }).rename(columns={'is_strike': 'ストライク率', 'is_swing': 'スイング率'}) * 100
    st.bar_chart(performance)

else:
    st.error("ファイルが見つかりません。GitHubの data フォルダを確認してください。")
