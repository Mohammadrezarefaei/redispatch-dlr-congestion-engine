import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pandapower as pp


# ==========================================
# 1. DLR (DYNAMIC LINE RATING) PHYSICS ENGINE
# ==========================================
def calculate_dlr_ampacity(base_rating_mva, ambient_temp_c, wind_speed_ms):
    """Calculates real-time thermal line capacity based on convective wind cooling

    and ambient temperature (simplified IEEE 738 standard approach).
    """
    reference_temp = 40.0  # Static rating design base temperature in Celsius
    temp_factor = np.sqrt(
        np.maximum(0.2, (80.0 - ambient_temp_c) / (80.0 - reference_temp))
    )
    wind_cooling_factor = 1.0 + 0.18 * np.power(
        np.maximum(0.5, wind_speed_ms), 0.55
    )
    dlr_multiplier = np.clip(temp_factor * wind_cooling_factor, 1.0, 1.65)
    return base_rating_mva * dlr_multiplier


# ==========================================
# 2. SYNTHETIC 4-BUS NORTH-SOUTH GRID SETUP
# ==========================================
def build_german_corridor_grid():
  net = pp.create_empty_network()

  # 4 Buses (North Wind Gen -> Central Hub -> South Industrial Demand)
  b1 = pp.create_bus(net, vn_kv=110, name="Bus 1 (North Offshore)")
  b2 = pp.create_bus(net, vn_kv=110, name="Bus 2 (North Onshore)")
  b3 = pp.create_bus(net, vn_kv=110, name="Bus 3 (Central Corridor)")
  b4 = pp.create_bus(net, vn_kv=110, name="Bus 4 (South Load Center)")

  # External Grid Slack at Bus 1
  pp.create_ext_grid(net, bus=b1, vm_pu=1.02)

  # Lines
  pp.create_line_from_parameters(
      net,
      b1,
      b2,
      length_km=45,
      r_ohm_per_km=0.12,
      x_ohm_per_km=0.38,
      c_nf_per_km=10,
      max_i_ka=0.6,
      name="Line 1-2 (North)",
  )
  pp.create_line_from_parameters(
      net,
      b2,
      b3,
      length_km=80,
      r_ohm_per_km=0.15,
      x_ohm_per_km=0.40,
      c_nf_per_km=10,
      max_i_ka=0.55,
      name="Line 2-3 (Bottleneck)",
  )
  pp.create_line_from_parameters(
      net,
      b3,
      b4,
      length_km=90,
      r_ohm_per_km=0.14,
      x_ohm_per_km=0.39,
      c_nf_per_km=10,
      max_i_ka=0.6,
      name="Line 3-4 (South)",
  )

  # Conventional flexible generator in the South (for upward redispatch)
  pp.create_gen(
      net, bus=b4, p_mw=30.0, min_p_mw=0, max_p_mw=120.0, name="South CCGT Plant"
  )

  # Renewable Infeed (North) & Heavy Demand (South)
  pp.create_sgen(net, bus=b2, p_mw=95.0, q_mvar=0, name="North Wind Cluster")
  pp.create_load(net, bus=b4, p_mw=110.0, q_mvar=20.0, name="South Load Center")

  return net


# ==========================================
# 3. REDISPATCH 2.0 TIME-SERIES SIMULATION
# ==========================================
dates = pd.date_range(start="2026-08-01 00:00:00", periods=24 * 7, freq="h")
np.random.seed(42)
hours = dates.hour.to_numpy()

wind_generation_mw = 40.0 + 65.0 * np.clip(
    np.sin(np.linspace(0, 6 * np.pi, len(dates))) + np.random.normal(0, 0.2, len(dates)),
    0,
    None,
)
south_load_mw = 75.0 + 35.0 * np.sin((hours - 6) * np.pi / 12) + np.random.normal(0, 3, len(dates))
ambient_temp_c = 18.0 + 8.0 * np.sin((hours - 9) * np.pi / 12)
wind_speed_ms = 4.0 + 4.5 * np.abs(np.sin(np.linspace(0, 4 * np.pi, len(dates))))

STATIC_BOTTLENECK_RATING_MVA = 75.0
curtailment_static_mw = []
curtailment_dlr_mw = []
redispatch_cost_static_eur = []
redispatch_cost_dlr_eur = []
dlr_capacity_mva = []

# Economic costs (€/MWh)
COST_DOWNWARD_REDISPATCH = 45.0  # Compensation for wind curtailment
COST_UPWARD_REDISPATCH = 115.0  # Expensive conventional redispatch ramp-up

net = build_german_corridor_grid()

for i in range(len(dates)):
  # Dynamic Line Rating computation
  dlr_mva = calculate_dlr_ampacity(
      STATIC_BOTTLENECK_RATING_MVA, ambient_temp_c[i], wind_speed_ms[i]
  )
  dlr_capacity_mva.append(dlr_mva)

  # Power flow with Static Limit
  net.sgen.at[0, "p_mw"] = wind_generation_mw[i]
  net.load.at[0, "p_mw"] = south_load_mw[i]
  pp.runpp(net)

  corridor_flow = net.res_line.at[1, "loading_percent"] * (
      STATIC_BOTTLENECK_RATING_MVA / 100.0
  )

  # Overload under Static limits
  overload_static = max(0.0, corridor_flow - STATIC_BOTTLENECK_RATING_MVA)
  curtailment_static_mw.append(overload_static)
  redispatch_cost_static_eur.append(
      overload_static * (COST_DOWNWARD_REDISPATCH + COST_UPWARD_REDISPATCH)
  )

  # Overload under Dynamic Line Rating limits
  overload_dlr = max(0.0, corridor_flow - dlr_mva)
  curtailment_dlr_mw.append(overload_dlr)
  redispatch_cost_dlr_eur.append(
      overload_dlr * (COST_DOWNWARD_REDISPATCH + COST_UPWARD_REDISPATCH)
  )

df_results = pd.DataFrame(
    {
        "timestamp": dates,
        "wind_gen_mw": wind_generation_mw,
        "south_load_mw": south_load_mw,
        "static_rating_mva": STATIC_BOTTLENECK_RATING_MVA,
        "dlr_capacity_mva": dlr_capacity_mva,
        "curtailment_static_mw": curtailment_static_mw,
        "curtailment_dlr_mw": curtailment_dlr_mw,
        "cost_static_eur": redispatch_cost_static_eur,
        "cost_dlr_eur": redispatch_cost_dlr_eur,
    }
)

total_static_cost = df_results["cost_static_eur"].sum()
total_dlr_cost = df_results["cost_dlr_eur"].sum()
cost_reduction_pct = (
    (total_static_cost - total_dlr_cost) / total_static_cost
) * 100

print("=" * 70)
print(" GERMAN CORRIDOR REDISPATCH 2.0 & DLR ENGINE RESULTS")
print("=" * 70)
print(f"Total Static Redispatch Cost (7 Days): €{total_static_cost:,.2f}")
print(f"Total DLR Optimized Redispatch Cost:   €{total_dlr_cost:,.2f}")
print(f"Financial Congestion Cost Savings:     {cost_reduction_pct:.2f}%")
print(
    f"Green Energy Saved from Curtailment:   {df_results['curtailment_static_mw'].sum() - df_results['curtailment_dlr_mw'].sum():,.2f} MWh"
)
print("=" * 70)

# ==========================================
# 4. VISUALIZATION & EXPORT
# ==========================================
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), sharex=True)

# Subplot 1: Dynamic Line Capacity vs Static Rating
ax1.plot(
    df_results["timestamp"],
    df_results["wind_gen_mw"],
    color="#0284c7",
    lw=1.8,
    label="North Wind Infeed (MW)",
)
ax1.plot(
    df_results["timestamp"],
    df_results["dlr_capacity_mva"],
    color="#16a34a",
    lw=2.2,
    label="Dynamic Line Rating (DLR MVA)",
)
ax1.axhline(
    STATIC_BOTTLENECK_RATING_MVA,
    color="#dc2626",
    ls="--",
    lw=1.8,
    label="Static Seasonal Rating (75 MVA)",
)
ax1.set_ylabel("Power / Capacity [MVA]", fontweight="bold")
ax1.set_title(
    "Corridor Bottleneck: Static Limits vs. Weather-Aware Dynamic Line Rating"
    " (DLR)",
    fontweight="bold",
    fontsize=12,
)
ax1.grid(True, linestyle=":", alpha=0.6)
ax1.legend(loc="upper right")

# Subplot 2: Redispatch Congestion Cost Comparison
ax2.bar(
    df_results["timestamp"],
    df_results["cost_static_eur"],
    width=0.035,
    color="#ef4444",
    alpha=0.65,
    label="Static Redispatch Cost (€)",
)
ax2.bar(
    df_results["timestamp"],
    df_results["cost_dlr_eur"],
    width=0.035,
    color="#10b981",
    alpha=0.85,
    label="DLR Redispatch Cost (€)",
)
ax2.set_ylabel("Redispatch Cost [€/h]", fontweight="bold")
ax2.set_xlabel("Timeline", fontweight="bold")
ax2.grid(True, linestyle=":", alpha=0.6)
ax2.legend(loc="upper right")

plt.tight_layout()
plt.savefig("redispatch_dlr_simulation_results.png", dpi=300)
plt.show()

df_results.to_csv("redispatch_dlr_simulation_2026.csv", index=False)
print("Simulation dataset exported as 'redispatch_dlr_simulation_2026.csv'")
