import pandapower as pp


def build_german_corridor_network() -> pp.pandapowerNet:
  """Constructs a 4-bus synthetic German transmission corridor (110 kV)

  connecting northern renewable generation clusters to southern load centers.
  """
  net = pp.create_empty_network()

  # 4 Buses
  b1 = pp.create_bus(net, vn_kv=110, name="North Offshore Hub")
  b2 = pp.create_bus(net, vn_kv=110, name="North Onshore Node")
  b3 = pp.create_bus(net, vn_kv=110, name="Central Corridor")
  b4 = pp.create_bus(net, vn_kv=110, name="South Industrial Demand")

  # External grid slack with strong voltage support
  pp.create_ext_grid(net, bus=b1, vm_pu=1.03)

  # Transmission lines
  pp.create_line_from_parameters(
      net,
      b1,
      b2,
      length_km=30,
      r_ohm_per_km=0.08,
      x_ohm_per_km=0.25,
      c_nf_per_km=10,
      max_i_ka=0.8,
      name="Line 1-2 (North Infeed)",
  )
  pp.create_line_from_parameters(
      net,
      b2,
      b3,
      length_km=50,
      r_ohm_per_km=0.09,
      x_ohm_per_km=0.28,
      c_nf_per_km=10,
      max_i_ka=0.65,
      name="Line 2-3 (Bottleneck)",
  )
  pp.create_line_from_parameters(
      net,
      b3,
      b4,
      length_km=50,
      r_ohm_per_km=0.09,
      x_ohm_per_km=0.28,
      c_nf_per_km=10,
      max_i_ka=0.8,
      name="Line 3-4 (South Transmission)",
  )

  # Generators & Load
  pp.create_sgen(
      net, bus=b2, p_mw=80.0, q_mvar=0.0, name="North Wind Generation"
  )
  pp.create_gen(
      net,
      bus=b4,
      p_mw=25.0,
      vm_pu=1.01,
      min_q_mvar=-30,
      max_q_mvar=50,
      name="South Flexible Unit",
  )
  pp.create_load(net, bus=b4, p_mw=90.0, q_mvar=10.0, name="South Load Center")

  return net
