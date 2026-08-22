import numpy as np
import pandas as pd
import pandapower as pp
from src.dlr_model import calculate_dlr_ampacity
from src.network_builder import build_german_corridor_network
from src.redispatch_optimizer import run_redispatch_simulation


def test_dlr_ampacity_increase_with_wind():
  static_rating = 75.0
  low_wind_dlr = calculate_dlr_ampacity(
      static_rating, ambient_temp_c=20.0, wind_speed_ms=1.0
  )
  high_wind_dlr = calculate_dlr_ampacity(
      static_rating, ambient_temp_c=20.0, wind_speed_ms=10.0
  )

  assert high_wind_dlr > low_wind_dlr
  assert low_wind_dlr >= static_rating
  assert high_wind_dlr <= static_rating * 1.65


def test_network_convergence():
  net = build_german_corridor_network()
  pp.runpp(net, algorithm="nr", init="dc")
  assert net.converged is True
  assert abs(net.res_bus.at[3, "vm_pu"] - 1.0) < 0.15


def test_redispatch_simulation_integrity():
  dates = pd.date_range("2026-08-01", periods=12, freq="h")
  wind = np.full(12, 85.0)
  load = np.full(12, 90.0)
  temp = np.full(12, 18.0)
  wind_spd = np.full(12, 6.0)

  df = run_redispatch_simulation(dates, wind, load, temp, wind_spd)

  assert len(df) == 12
  assert (df["cost_dlr_eur"] <= df["cost_static_eur"]).all()
