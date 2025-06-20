# -*- coding: utf-8 -*-
"""automated_dashboard.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1tHZEWW2ho5U3wMRQ69PeTG4KDgNj7--0
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import plotly.graph_objects as go

# ====== LOAD DATA ======
# Baca data aktual
actual_data = pd.read_csv("usd_idr_actual.csv", index_col=0, comment="#")

# Baca data prediksi terbaru (H+1 dan seterusnya)
forecast_latest = pd.read_csv("usd_idr_pred_latest.csv", index_col=0, comment="#")

# Coba baca data prediksi kemarin (H+1 dari kemarin = hari ini)
try:
    forecast_yesterday = pd.read_csv("usd_idr_pred_yesterday.csv", index_col=0, comment="#")
    forecast_yesterday.index = pd.to_datetime(forecast_yesterday.index)
    forecast_yesterday = forecast_yesterday[forecast_yesterday.columns.intersection(['predicted_usd_idr'])]
except Exception as e:
    forecast_yesterday = pd.DataFrame()
    print("⚠️ Gagal membaca prediksi kemarin:", e)

# Fallback: Jika forecast_yesterday kosong, ambil dari backup
if forecast_yesterday.empty:
    try:
        # Ambil tanggal aktual terakhir dan tentukan tanggal kemarin
        last_actual_date = actual_data['date'].max()
        yesterday_date = last_actual_date - pd.Timedelta(days=1)
        backup_path = f"usd_idr_pred_backup/{yesterday_date.strftime('%Y-%m-%d')}.csv"

        # Baca file backup prediksi kemarin
        backup_df = pd.read_csv(backup_path, index_col=0, comment="#")
        backup_df.index = pd.to_datetime(backup_df.index)

        # Ambil baris prediksi yang ditujukan untuk hari ini (last_actual_date)
        if last_actual_date in backup_df.index:
            forecast_yesterday = backup_df.loc[[last_actual_date]].reset_index()
            forecast_yesterday = forecast_yesterday.rename(columns={"index": "date"})
        else:
            st.warning(f"📌 Backup ditemukan ({backup_path}), tapi tidak memuat prediksi untuk {last_actual_date.date()}")
    except Exception as e:
        st.warning("📌 Gagal membaca backup prediksi dari kemarin.")
        st.exception(e)


# ====== FORMAT ULANG ======
actual_data = actual_data.reset_index().rename(columns={"index": "date"})
forecast_latest = forecast_latest.reset_index().rename(columns={"index": "date"})
forecast_yesterday = forecast_yesterday.reset_index().rename(columns={"index": "date"})

actual_data["date"] = pd.to_datetime(actual_data["date"])
forecast_latest["date"] = pd.to_datetime(forecast_latest["date"])
forecast_yesterday["date"] = pd.to_datetime(forecast_yesterday["date"])

actual_data = actual_data.rename(columns={"usd_idr": "value"})
actual_data["type"] = "actual"

forecast_data = forecast_latest.rename(columns={"predicted_usd_idr": "value"})
forecast_data["type"] = "forecast"

# Filter hanya hari kerja
forecast_data = forecast_data[forecast_data['date'].dt.weekday < 5]
forecast_yesterday = forecast_yesterday[forecast_yesterday['date'].dt.weekday < 5]

# ====== Gabungkan untuk visualisasi utama (tanpa forecast_yesterday) ======
data = pd.concat([actual_data, forecast_data], ignore_index=True)

# ====== SET PAGE ======
st.set_page_config(page_title="Prediksi USD/IDR", layout="wide")
st.title("📈 Dashboard Prediksi Nilai Tukar USD/IDR")
st.caption("Prediksi nilai tukar untuk 7 hari ke depan berdasarkan data 30 hari terakhir")

# ====== GRAFIK UTAMA ======
last_actual_date = actual_data['date'].max()
visual_data = data[data['date'] >= last_actual_date - pd.Timedelta(days=30)]

fig = px.line(
    visual_data,
    x='date',
    y='value',
    color='type',
    line_dash='type',
    labels={'value': 'Nilai Tukar (Rp)', 'date': 'Tanggal'},
    title='Nilai Tukar USD/IDR - Aktual dan Prediksi (30 Hari + Forecast)'
)

# Format tooltip dan garis utama
fig.update_traces(
    mode="lines+markers",
    hovertemplate='Tanggal: %{x|%d %b %Y}<br>Nilai: Rp %{y:,.2f}'
)

# 🎨 Ubah warna actual dan forecast
fig.for_each_trace(
    lambda trace: trace.update(
        line=dict(color='#1f77b4') if trace.name == 'actual' else
             dict(color='#ff7f0e') if trace.name == 'forecast' else trace.line
    )
)

# ====== Garis Penghubung Aktual -> Forecast ======
last_actual_point = actual_data.sort_values("date").iloc[-1]
try:
    first_forecast_point = forecast_data[forecast_data["date"] >= last_actual_point["date"]].sort_values("date").iloc[0]
    fig.add_trace(go.Scatter(
        x=[last_actual_point["date"], first_forecast_point["date"]],
        y=[last_actual_point["value"], first_forecast_point["value"]],
        mode="lines",
        line=dict(color="#ff7f0e", dash="dot"),
        name="",
        showlegend=False
    ))
except IndexError:
    st.warning("⚠ Prediksi tidak tersedia untuk tanggal setelah data aktual terakhir.")

# ====== TAMPILKAN ======
st.plotly_chart(fig, use_container_width=True)

# ====== INFO PREDIKSI KEMARIN ======
try:
    # Kita ambil tanggal aktual "kemarin"
    yesterday_date = actual_data['date'].max().date() - pd.Timedelta(days=1)

    # Ambil prediksi H+1 yang dibuat kemarin (artinya untuk tanggal 'yesterday_date')
    pred_yest_val_series = forecast_yesterday[
        forecast_yesterday['date'].dt.date == yesterday_date
    ]['predicted_usd_idr']

    if not pred_yest_val_series.empty:
        pred_yest_val = pred_yest_val_series.values[0]

        # Ambil nilai aktual untuk tanggal yang sama (yesterday_date)
        actual_val = actual_data[
            actual_data['date'].dt.date == yesterday_date
        ]['value'].values[0]

        error = actual_val - pred_yest_val
        delta_str = f"selisih {error:+,.2f} dari data aktual"
        st.metric(f"Prediksi untuk {yesterday_date}", f"Rp {pred_yest_val:,.2f}", delta=delta_str)
    else:
        st.warning(f"📌 Tidak ada prediksi dari kemarin untuk tanggal {yesterday_date}.")
except Exception as e:
    st.warning("📌 Gagal membandingkan prediksi kemarin dengan data aktual.")
    st.exception(e)


# ====== NOTIFIKASI LIBUR (Weekend Saja) ======
today = datetime.today()
if today.weekday() >= 5:
    st.warning("📅 Hari ini perdagangan libur (weekend)")

# ====== TREN NAIK/TURUN ======
last_7_actual = actual_data.sort_values("date").tail(7)["value"].mean()
next_7_forecast = forecast_data.sort_values("date").head(7)["value"].mean()

st.caption(f"📊 Rata-rata 7 hari terakhir: Rp {last_7_actual:,.2f} | Rata-rata forecast: Rp {next_7_forecast:,.2f}")

if next_7_forecast > last_7_actual:
    st.info("📈 Tren USD/IDR diperkirakan akan naik")
elif next_7_forecast < last_7_actual:
    st.info("📉 Tren USD/IDR diperkirakan akan turun")
else:
    st.info("📊 Nilai tukar diperkirakan stabil")

# ====== SLIDER UNTUK RENTANG TANGGAL ======
min_date = data['date'].min().date()
max_date = data['date'].max().date()

date_range = st.slider("Pilih rentang tanggal", min_value=min_date, max_value=max_date, value=(min_date, max_date))
filtered = data[(data['date'].dt.date >= date_range[0]) & (data['date'].dt.date <= date_range[1])]

fig2 = px.line(
    filtered,
    x='date',
    y='value',
    color='type',
    line_dash='type',
    title="Rentang Waktu yang Dipilih"
)
st.plotly_chart(fig2, use_container_width=True)