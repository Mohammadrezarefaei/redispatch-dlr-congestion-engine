import numpy as np


def calculate_dlr_ampacity(
    base_rating_mva: float,
    ambient_temp_c: float,
    wind_speed_ms: float,
    reference_temp_c: float = 40.0,
    max_conductor_temp_c: float = 80.0,
) -> float:
  """Calculates weather-aware dynamic line rating (DLR) ampacity

  based on IEEE 738 convective cooling formulation.
  """
  temp_delta = max(0.2, (max_conductor_temp_c - ambient_temp_c))
  design_delta = max(0.2, (max_conductor_temp_c - reference_temp_c))
  temp_factor = np.sqrt(temp_delta / design_delta)

  wind_cooling_factor = 1.0 + 0.18 * np.power(
      np.maximum(0.5, wind_speed_ms), 0.55
  )
  dlr_multiplier = float(np.clip(temp_factor * wind_cooling_factor, 1.0, 1.65))

  return float(base_rating_mva * dlr_multiplier)
