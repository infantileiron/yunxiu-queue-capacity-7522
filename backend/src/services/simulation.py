import random,statistics,math
from src.services.scheduler import schedule
def _validate(arrival_rate,service_rate,windows,duration,warmup,replications):
 if arrival_rate<=0 or service_rate<=0 or windows<1 or duration<=0 or warmup<0 or replications<2:raise ValueError("无效仿真参数")
 if arrival_rate*(duration+warmup)>20000:raise ValueError("预期到达超过20000条，请缩短时域或降低负荷")
def _streams(arrival_rate,service_rate,duration,warmup,replications,seed):
 end=warmup+duration;streams=[]
 for rep in range(replications):
  rng=random.Random(seed+rep);arrivals=[];services=[];t=0
  while True:
   t+=rng.expovariate(arrival_rate)
   if t>=end:break
   if len(arrivals)>=50000:raise ValueError("单次仿真事件超过50000条")
   arrivals.append(t);services.append(rng.expovariate(service_rate))
  streams.append({"replication":rep+1,"arrivals":arrivals,"services":services})
 return streams
def _run(stream,windows,duration,warmup):
 end=warmup+duration
 events=schedule(stream["arrivals"],stream["services"],windows);observed=[e for e in events if e["arrival"]>=warmup]
 if not observed:raise ValueError("观测时域没有到达，请增大时域")
 waits=[e["wait"] for e in observed]
 busy=sum(max(0,min(e["end"],end)-max(e["start"],warmup)) for e in events)
 return {"replication":stream["replication"],"arrivals":len(observed),"mean_wait_minutes":statistics.mean(waits),"p_wait":sum(x>1e-9 for x in waits)/len(waits),"max_wait_minutes":max(waits),"busy_fraction":busy/(windows*duration)},observed[:80]
def _summary(results,replications):
 means=[r["mean_wait_minutes"] for r in results];mean=statistics.mean(means);se=statistics.stdev(means)/math.sqrt(replications)
 return {"mean_wait_minutes":mean,"mean_wait_ci95":[max(0,mean-1.96*se),mean+1.96*se],"p_wait":statistics.mean(r["p_wait"] for r in results),"busy_fraction":statistics.mean(r["busy_fraction"] for r in results)}
def simulate(arrival_rate,service_rate,windows,duration,warmup,replications,seed):
 _validate(arrival_rate,service_rate,windows,duration,warmup,replications)
 results=[];last_events=[]
 for stream in _streams(arrival_rate,service_rate,duration,warmup,replications,seed):
  result,events=_run(stream,windows,duration,warmup);results.append(result);last_events=events
 summary=_summary(results,replications)
 return {"mean_wait_minutes":summary["mean_wait_minutes"],"mean_wait_ci95":summary["mean_wait_ci95"],"p_wait":summary["p_wait"],"busy_fraction":summary["busy_fraction"],"replications":results,"timeline":last_events,"duration_minutes":duration,"warmup_minutes":warmup,"seed":seed,"ci_method":"重复试验均值的正态近似95%区间（1.96×重复均值标准误）"}
def simulate_paired(arrival_rate,service_rate,baseline_windows,candidate_windows,duration,warmup,replications,seed):
 if not isinstance(baseline_windows,int) or not isinstance(candidate_windows,int) or baseline_windows<1 or candidate_windows<1:raise ValueError("配对窗口数须为正整数")
 _validate(arrival_rate,service_rate,max(baseline_windows,candidate_windows),duration,warmup,replications)
 baseline_results=[];candidate_results=[];paired_results=[];baseline_timeline=[];candidate_timeline=[]
 for stream in _streams(arrival_rate,service_rate,duration,warmup,replications,seed):
  # 两侧使用完全相同的到达时刻与服务时长，逐次差值只体现窗口数。
  baseline,baseline_events=_run(stream,baseline_windows,duration,warmup)
  candidate,candidate_events=_run(stream,candidate_windows,duration,warmup)
  baseline_results.append(baseline);candidate_results.append(candidate);baseline_timeline=baseline_events;candidate_timeline=candidate_events
  paired_results.append({"replication":stream["replication"],"arrivals":baseline["arrivals"],"baseline_arrivals":baseline["arrivals"],"candidate_arrivals":candidate["arrivals"],"difference_minutes":baseline["mean_wait_minutes"]-candidate["mean_wait_minutes"],"baseline_mean_wait_minutes":baseline["mean_wait_minutes"],"candidate_mean_wait_minutes":candidate["mean_wait_minutes"],"baseline_p_wait":baseline["p_wait"],"candidate_p_wait":candidate["p_wait"],"baseline_busy_fraction":baseline["busy_fraction"],"candidate_busy_fraction":candidate["busy_fraction"],"baseline_max_wait_minutes":baseline["max_wait_minutes"],"candidate_max_wait_minutes":candidate["max_wait_minutes"]})
 differences=[r["difference_minutes"] for r in paired_results];mean=statistics.mean(differences);sd=statistics.stdev(differences);se=sd/math.sqrt(replications)
 baseline_simulation={**_summary(baseline_results,replications),"replications":baseline_results,"timeline":baseline_timeline,"duration_minutes":duration,"warmup_minutes":warmup,"seed":seed,"windows":baseline_windows}
 candidate_simulation={**_summary(candidate_results,replications),"replications":candidate_results,"timeline":candidate_timeline,"duration_minutes":duration,"warmup_minutes":warmup,"seed":seed,"windows":candidate_windows}
 return {"baseline":{"windows":baseline_windows,"simulation":baseline_simulation},"candidate":{"windows":candidate_windows,"simulation":candidate_simulation},"paired":{"replications":paired_results,"mean_difference_minutes":mean,"difference_ci95":[mean-1.96*se,mean+1.96*se],"sd_difference_minutes":sd,"mean_baseline_wait_minutes":statistics.mean(r["mean_wait_minutes"] for r in baseline_results),"mean_candidate_wait_minutes":statistics.mean(r["mean_wait_minutes"] for r in candidate_results),"difference_definition":"基准侧平均等待 − 候选侧平均等待；正值表示候选窗口等待更短，交换两侧后逐次差值反号","same_windows_zero":True,"swap_negates":True,"shared_streams":True,"ci_method":"配对差值均值的正态近似95%区间（1.96×配对差值标准误）；两侧共用同一批到达与服务，不按独立样本处理"},"duration_minutes":duration,"warmup_minutes":warmup,"seed":seed,"timeline":candidate_timeline}
