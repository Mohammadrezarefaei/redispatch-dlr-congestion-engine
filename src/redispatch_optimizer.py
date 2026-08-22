import numpy as np
import pandas as pd
import pandapower as pp
from src.dlr_model import calculate_dlr_ampacity
from src.network_builder import build_german_corridor_network


def run_redispatch_simulation(
    timestamps: pd.DatetimeIndex,
    wind_infeed_mw: np.ndarray,
    south_load_mw: np.ndarray,
    ambient_temp_c: np.ndarray,
    wind_speed_ms: np.ndarray,
    static_limit_mva: float = 75.0,
    cost_downward_eur_mwh: float = 45.0,
    cost_upward_eur_mwh: float = 115.0,
) -> pd.DataFrame:
  """Executes time-series AC load flow and compares Redispatch 2.0

  congestion costs between static ratings and dynamic line ratings.
  """
  net = build_german_corridor_network()
  total_rate = cost_downward_eur_mwh + cost_upward_eur_mwh

  flows, dlr_limits, static_curtailment, dlr_curtailment = [], [], [], []

  for i in range(len(timestamps)):
    dlr_mva = calculate_dlr_ampacity(
        static_limit_mva, ambient_temp_c[i], wind_speed_ms[i]
    )
    dlr_limits.append(dlr_mva)

    net.sgen.at[0, "p_mw"] = wind_infeed_mw[i]
    net.load.at[0, "p_mw"] = south_load_mw[i]

    pp.runpp(net, algorithm="nr", init="dc", max_iteration=30)
    flow = abs(net.res_line.at[1, "p_from_mw"])
    flows.append(flow)

    static_curtailment.append(max(0.0, flow - static_limit_mva))
    dlr_curtailment.append(max(0.0, flow - dlr_mva))

  df = pd.DataFrame(
      {
          "timestamp": timestamps,
          "wind_infeed_mw": np.round(wind_infeed_mw, 2),
          "corridor_flow_mw": np.round(flows, 2),
          "static_limit_mva": static_limit_mva,
          "dlr_limit_mva": np.round(dlr_limits, 2),
          "curtailment_static_mw": np.round(static_curtailment, 2),
          "curtailment_dlr_mw": np.round(dlr_curtailment, 2),
          "cost_static_eur": np.round(
              np.array(static_curtailment) * total_rate, 2
          ),
          "cost_dlr_eur": np.round(np.array(dlr_curtailment) * total_rate, 2),
      }
  )

  return df
