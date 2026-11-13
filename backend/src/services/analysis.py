from src.services.erlang import erlang_c
from src.services.simulation import simulate,simulate_paired
def _assumptions(paired):
 items=["所有率均为每分钟；μ是每个窗口的服务率。理论要求泊松到达、独立指数服务、同质窗口、无限等候空间及稳态。","观测按时段估计均值；聚合高峰与平峰不保证泊松稳态。CV偏离1提示指数假设可能不符。","仿真从空系统开始，先warmup后统计观测期到达，服务可延续到观察结束之后。warmup只能缓解初态影响，不能保证已收敛。","rho≥1没有有限稳态均值；有限期仿真仍会给出暂态等待，不能用于证明稳定。","95%区间量化固定模型下重复仿真误差，不含输入率估计误差。"]
 if paired:items.insert(2,"配对试验两侧共用同一批到达时刻与服务时长，每次重复只改变窗口数。区间按逐次配对差值计算，不是两侧各自区间的比较；相同窗口数的差值恒为0，交换两侧后逐次差值反号。")
 return items
def _config(profile,scenario,arrival,service,paired):
 return {"mode":"paired" if paired else "single","profile_id":profile.id,"profile_name":profile.name,"profile_period":profile.period,"profile_checksum":profile.statistics.get("checksum",""),"arrival_rate":arrival,"service_rate":service,"arrival_multiplier":scenario.arrival_multiplier,"service_multiplier":scenario.service_multiplier,"baseline_windows":scenario.windows,"candidate_windows":scenario.candidate_windows if paired else None,"duration_minutes":scenario.duration_minutes,"warmup_minutes":scenario.warmup_minutes,"replications":scenario.replications,"seed":scenario.seed,"scenario_id":scenario.id}
def analyze(profile,scenario):
 arrival=profile.arrival_rate*scenario.arrival_multiplier;service=profile.service_rate*scenario.service_multiplier
 candidate_windows=getattr(scenario,"candidate_windows",None)
 paired=candidate_windows is not None
 if not paired:
  analytic=erlang_c(arrival,service,scenario.windows);simulation=simulate(arrival,service,scenario.windows,scenario.duration_minutes,scenario.warmup_minutes,scenario.replications,scenario.seed)
  return {"mode":"single","analytic":analytic,"simulation":simulation,"comparison":[erlang_c(arrival,service,c) for c in sorted({2,3,4,scenario.windows})],"profile_statistics":profile.statistics,"config":_config(profile,scenario,arrival,service,False),"assumptions":_assumptions(False)}
 baseline_analytic=erlang_c(arrival,service,scenario.windows)
 candidate_analytic=erlang_c(arrival,service,candidate_windows)
 trial=simulate_paired(arrival,service,scenario.windows,candidate_windows,scenario.duration_minutes,scenario.warmup_minutes,scenario.replications,scenario.seed)
 windows=sorted({2,3,4,scenario.windows,candidate_windows})
 return {"mode":"paired","baseline":{"windows":scenario.windows,"analytic":baseline_analytic,"simulation":trial["baseline"]["simulation"]},"candidate":{"windows":candidate_windows,"analytic":candidate_analytic,"simulation":trial["candidate"]["simulation"]},"paired":trial["paired"],"comparison":[erlang_c(arrival,service,c) for c in windows],"profile_statistics":profile.statistics,"config":_config(profile,scenario,arrival,service,True),"assumptions":_assumptions(True)}
