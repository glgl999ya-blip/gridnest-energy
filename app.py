
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="GridNest Energy", page_icon="⚡", layout="wide")
st.title("⚡ GridNest Energy")
st.caption("Smart Residential Energy Management and Cost Optimisation Platform")

@st.cache_data
def load_sample():
    return pd.read_csv("sample_energy_data.csv", parse_dates=["timestamp"])

uploaded = st.sidebar.file_uploader("Upload energy CSV", type=["csv"])
if uploaded is not None:
    data = pd.read_csv(uploaded)
    data["timestamp"] = pd.to_datetime(data["timestamp"])
else:
    data = load_sample()

required = ["timestamp", "household_load_kw", "pv_kw", "flexible_load_kw"]
missing = [c for c in required if c not in data.columns]
if missing:
    st.error("CSV is missing required columns: " + ", ".join(missing))
    st.stop()

data = data.sort_values("timestamp").reset_index(drop=True)
dt_hours = 0.5

st.sidebar.header("TOU tariff settings")
off_peak = st.sidebar.number_input("Off-peak rate ($/kWh)", min_value=0.0, value=0.22, step=0.01)
shoulder = st.sidebar.number_input("Shoulder rate ($/kWh)", min_value=0.0, value=0.32, step=0.01)
peak = st.sidebar.number_input("Peak rate ($/kWh)", min_value=0.0, value=0.48, step=0.01)

def tariff_rate(ts):
    h = ts.hour + ts.minute/60
    if 22 <= h or h < 7:
        return off_peak
    if 14 <= h < 20:
        return peak
    return shoulder

data["tariff_rate"] = data["timestamp"].apply(tariff_rate)

st.sidebar.header("Flexible-load scheduling")
start_hour = st.sidebar.slider("Earliest start hour", 0, 23, 9)
end_hour = st.sidebar.slider("Latest completion hour", 1, 24, 23)
peak_weight = st.sidebar.slider("Peak-demand penalty weight", 0.0, 1.0, 0.15, 0.05)

base = data["household_load_kw"].to_numpy()
pv = data["pv_kw"].to_numpy()
flex_original = data["flexible_load_kw"].to_numpy()

active = np.where(flex_original > 0)[0]
if len(active) == 0:
    st.warning("No flexible load detected in flexible_load_kw.")
    st.stop()

duration = len(active)
shape = flex_original[active].copy()
n = len(data)

def grid_import(total_load, pv_profile):
    return np.maximum(total_load - pv_profile, 0)

def cost_of(import_kw, rates):
    return float(np.sum(import_kw * rates * dt_hours))

rates = data["tariff_rate"].to_numpy()

baseline_total = base + flex_original
baseline_import = grid_import(baseline_total, pv)
baseline_cost = cost_of(baseline_import, rates)
baseline_peak = float(baseline_import.max())

feasible = []
for s in range(0, n-duration+1):
    start_ts = data.loc[s, "timestamp"]
    end_ts = data.loc[s+duration-1, "timestamp"] + pd.Timedelta(minutes=30)
    sh = start_ts.hour + start_ts.minute/60
    eh = end_ts.hour + end_ts.minute/60
    if sh >= start_hour and eh <= end_hour:
        feasible.append(s)

best = None
for s in feasible:
    f = np.zeros(n)
    f[s:s+duration] = shape
    total = base + f
    imp = grid_import(total, pv)
    c = cost_of(imp, rates)
    p = float(imp.max())
    objective = c + peak_weight * p
    candidate = (objective, c, p, s, f, imp)
    if best is None or candidate[0] < best[0]:
        best = candidate

if best is None:
    st.error("No feasible schedule exists for the selected operating window.")
    st.stop()

_, opt_cost, opt_peak, opt_start, flex_opt, opt_import = best
opt_total = base + flex_opt

c1, c2, c3, c4 = st.columns(4)
c1.metric("Baseline daily cost", f"${baseline_cost:.2f}")
c2.metric("Optimised daily cost", f"${opt_cost:.2f}", f"{opt_cost-baseline_cost:+.2f}")
c3.metric("Baseline peak import", f"{baseline_peak:.2f} kW")
c4.metric("Optimised peak import", f"{opt_peak:.2f} kW", f"{opt_peak-baseline_peak:+.2f}")

st.subheader("1. Household load and PV scenario")
fig = go.Figure()
fig.add_trace(go.Scatter(x=data["timestamp"], y=base, name="Base household load"))
fig.add_trace(go.Scatter(x=data["timestamp"], y=pv, name="PV generation"))
fig.add_trace(go.Scatter(x=data["timestamp"], y=baseline_total, name="Baseline total load"))
fig.update_layout(xaxis_title="Time", yaxis_title="Power (kW)", legend_orientation="h")
st.plotly_chart(fig, use_container_width=True)

st.subheader("2. TOU tariff")
fig2 = px.step(data, x="timestamp", y="tariff_rate")
fig2.update_layout(xaxis_title="Time", yaxis_title="Tariff ($/kWh)")
st.plotly_chart(fig2, use_container_width=True)

st.subheader("3. Flexible-load scheduling result")
fig3 = go.Figure()
fig3.add_trace(go.Bar(x=data["timestamp"], y=flex_original, name="Baseline flexible load"))
fig3.add_trace(go.Bar(x=data["timestamp"], y=flex_opt, name="Optimised flexible load"))
fig3.update_layout(barmode="group", xaxis_title="Time", yaxis_title="Power (kW)")
st.plotly_chart(fig3, use_container_width=True)

st.success(
    f"Optimised flexible-load start time: {data.loc[opt_start, 'timestamp'].strftime('%H:%M')}. "
    f"Estimated cost change: ${opt_cost-baseline_cost:+.2f}; "
    f"peak import change: {opt_peak-baseline_peak:+.2f} kW."
)

st.subheader("4. Grid import comparison")
compare = pd.DataFrame({
    "timestamp": data["timestamp"],
    "Baseline grid import": baseline_import,
    "Optimised grid import": opt_import
})
fig4 = px.line(compare, x="timestamp", y=["Baseline grid import", "Optimised grid import"])
fig4.update_layout(xaxis_title="Time", yaxis_title="Grid import (kW)", legend_title="")
st.plotly_chart(fig4, use_container_width=True)

with st.expander("View processed data"):
    out = data.copy()
    out["baseline_grid_import_kw"] = baseline_import
    out["optimised_flexible_load_kw"] = flex_opt
    out["optimised_grid_import_kw"] = opt_import
    st.dataframe(out, use_container_width=True)
    st.download_button(
        "Download results CSV",
        out.to_csv(index=False).encode("utf-8"),
        "gridnest_results.csv",
        "text/csv"
    )

st.caption(
    "Prototype scope: monitoring, tariff analysis, scenario comparison and scheduling decision support. "
    "Automatic appliance control is outside the MVP."
)
