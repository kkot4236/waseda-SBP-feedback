import pandas as pd

import streamlit as st

import os

import matplotlib.pyplot as plt

import glob



# --- 1. ページ設定 ---

st.set_page_config(page_title="Pitch Analysis Dashboard", layout="wide")



# --- 2. データ読み込み関数 ---

@st.cache_data

def load_all_data_from_folder(folder_path):

    all_files = glob.glob(os.path.join(folder_path, "*.csv"))

    if not all_files:

        return None

    

    list_df = []

    for filename in all_files:

        try:

            temp_df = pd.read_csv(filename)

            list_df.append(temp_df)

        except Exception as e:

            st.warning(f"{os.path.basename(filename)} の読み込みに失敗しました: {e}")

    

    if not list_df:

        return None

        

    data = pd.concat(list_df, axis=0, ignore_index=True)

    data = data.dropna(subset=['TaggedPitchType', 'PitchCall', 'Pitcher'])

    

    if 'Date' in data.columns:

        data['Date'] = pd.to_datetime(data['Date']).dt.date



    # --- Runner列の判定（決定版） ---

    if 'Runner' in data.columns:

        # 文字列として処理し、前後の空白を削除。'0', 'None', 空文字以外はすべて 1(ランナーあり)

        data['has_runner'] = data['Runner'].apply(

            lambda x: 0 if pd.isna(x) or str(x).strip().lower() in ['0', '0.0', 'none', '', 'nan'] else 1

        )

    else:

        data['has_runner'] = 0



    data['RelSpeed'] = pd.to_numeric(data['RelSpeed'], errors='coerce')

    data['Balls'] = pd.to_numeric(data['Balls'], errors='coerce').fillna(0).astype(int)

    data['Strikes'] = pd.to_numeric(data['Strikes'], errors='coerce').fillna(0).astype(int)

    

    return data



current_dir = os.path.dirname(__file__)

data_folder = os.path.join(current_dir, "data")

df = load_all_data_from_folder(data_folder)



# --- 3. アプリのメイン処理 ---

if df is not None:

    PITCH_ORDER = ["Fastball", "Slider", "Cutter", "Curveball", "Splitter", "ChangeUp", "TwoSeamFastBall", "OneSeam"]



    strike_calls = ['StrikeCalled', 'StrikeSwinging', 'FoulBall', 'InPlay']

    whiff_calls = ['StrikeSwinging']

    swing_calls = ['StrikeSwinging', 'FoulBall', 'InPlay']



    df['is_strike'] = df['PitchCall'].isin(strike_calls).astype(int)

    df['is_swing'] = df['PitchCall'].isin(swing_calls).astype(int)

    df['is_whiff'] = df['PitchCall'].isin(whiff_calls).astype(int)



    st.title("⚾ 投球データ総合分析ダッシュボード")



    # --- 4. サイドバー設定 ---

    st.sidebar.header("📊 フィルター設定")

    pitcher_list = sorted(df['Pitcher'].unique())

    selected_pitcher = st.sidebar.selectbox("投手を選択", ["すべて"] + pitcher_list)



    if 'Date' in df.columns:

        date_list = sorted(df['Date'].unique(), reverse=True)

        selected_date = st.sidebar.selectbox("日付を選択", ["すべて"] + date_list)

    else:

        selected_date = "すべて"



    runner_option = st.sidebar.radio("ランナー状況", ["すべて", "通常 (ランナー無し)", "クイック (ランナー有り)"])

    

    # --- 5. フィルタリング適用 ---

    plot_df = df.copy()

    if selected_pitcher != "すべて":

        plot_df = plot_df[plot_df['Pitcher'] == selected_pitcher]

    if selected_date != "すべて":

        plot_df = plot_df[plot_df['Date'] == selected_date]

    

    if runner_option == "通常 (ランナー無し)":

        plot_df = plot_df[plot_df['has_runner'] == 0]

    elif runner_option == "クイック (ランナー有り)":

        plot_df = plot_df[plot_df['has_runner'] == 1]



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



    # --- 7. 球種別・分析 ---

    st.subheader(f"📊 球種別分析")

    

    summary = plot_df.groupby('TaggedPitchType').agg({

        'RelSpeed': ['count', 'mean', 'max'],

        'is_strike': 'mean',

        'is_swing': 'mean',

        'is_whiff': 'sum'

    })

    summary.columns = ['投球数', '平均球速', '最速', 'ストライク率', 'スイング率', '空振り数']

    

    existing_pitches = [p for p in PITCH_ORDER if p in summary.index]

    other_pitches = [p for p in summary.index if p not in PITCH_ORDER]

    summary = summary.reindex(existing_pitches + other_pitches)



    summary['投球割合'] = (summary['投球数'] / summary['投球数'].sum() * 100)

    swings_per_pitch = plot_df.groupby('TaggedPitchType')['is_swing'].sum()

    summary['空振り/スイング'] = (summary['空振り数'] / swings_per_pitch * 100).fillna(0)

    summary['ストライク率'] = summary['ストライク率'] * 100

    

    t_col1, t_col2 = st.columns([2, 1])

    with t_col1:

        stat_table = summary[['投球数', '投球割合', '平均球速', '最速', 'ストライク率', '空振り/スイング']]

        st.table(stat_table.style.format({

            '投球割合': '{:.1f}%', '平均球速': '{:.1f}', '最速': '{:.1f}', 'ストライク率': '{:.1f}%', '空振り/スイング': '{:.1f}%'

        }))



    with t_col2:

        fig, ax = plt.subplots()

        ax.pie(summary['投球数'], labels=summary.index, autopct='%1.1f%%', startangle=90, counterclock=False)

        ax.axis('equal')

        st.pyplot(fig)



    # --- 8. カウント別・球種割合グラフ ---

    st.subheader("🗓 カウント別 投球割合")

    plot_df['Count'] = plot_df['Balls'].astype(str) + "-" + plot_df['Strikes'].astype(str)

    all_counts = ["0-0", "1-0", "2-0", "3-0", "0-1", "1-1", "2-1", "3-1", "0-2", "1-2", "2-2", "3-2"]

    count_data = plot_df.groupby(['Count', 'TaggedPitchType']).size().unstack(fill_value=0)

    count_data = count_data.reindex(all_counts, fill_value=0)

    existing_cols = [p for p in PITCH_ORDER if p in count_data.columns]

    count_data = count_data[existing_cols + [c for c in count_data.columns if c not in PITCH_ORDER]]

    

    row_sums = count_data.sum(axis=1)

    count_pct = count_data.div(row_sums.replace(0, 1), axis=0) * 100

    count_pct[row_sums == 0] = 0

    st.bar_chart(count_pct)



else:

    st.error("dataフォルダ内にCSVファイルが見つかりません。")
