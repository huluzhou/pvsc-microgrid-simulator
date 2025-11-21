import pandapower as pp

net = pp.create_empty_network()
bus = pp.create_bus(net, vn_kv=220.0)
pp.create_ext_grid(net, bus=bus)
pp.create_gen(net, bus=bus, p_mw=120.0, name="sgen1")
pp.create_load(net, bus=bus, p_mw=100.0, name="load1")
pp.runpp(net)

print("sgen1 power:", net.res_gen["p_mw"])
print("load1 power:", net.res_load["p_mw"])

net.ext_grid["in_service"] = False
# 当禁用外部电网时，需要将发电机设置为松弛节点
net.gen['slack'] = True
pp.runpp(net)
print("sgen1 power:", net.res_gen["p_mw"])
print("load1 power:", net.res_load["p_mw"])
