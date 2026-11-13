import uuid,csv,io
from sqlalchemy import select
from fastapi import HTTPException
from src.models import Report,CapacityReview
from src.services.runs import require_completed
from src.utils.time import now
from src.utils.serialization import serialize
def create(db,payload,user):
 require_completed(db,payload.run_id)
 review=db.scalar(select(CapacityReview).where(CapacityReview.run_id==payload.run_id).order_by(CapacityReview.created_at.desc()))
 if not review or review.decision!="accepted":raise HTTPException(409,"最新复核须为接受后才能归档")
 if db.scalar(select(Report).where(Report.run_id==payload.run_id)):raise HTTPException(409,"本次运行已归档")
 item=Report(id=str(uuid.uuid4()),published_by=user["email"],created_at=now(),**payload.model_dump());db.add(item);db.commit();return serialize(item)
def export(db,id):
 report=db.get(Report,id)
 if not report:raise HTTPException(404,"报告不存在")
 run=require_completed(db,report.run_id);result=run.result
 buf=io.StringIO()
 if result.get("mode")!="paired":
  columns=["replication","arrivals","mean_wait_minutes","p_wait","max_wait_minutes","busy_fraction"]
  writer=csv.DictWriter(buf,fieldnames=columns);writer.writeheader();writer.writerows(result["simulation"]["replications"])
  return "﻿"+buf.getvalue()
 config=result["config"];paired=result["paired"]
 config_rows=[("报告标题",report.title),("归档编号",report.id),("运行编号",run.id),("试验模式","配对试验"),("输入剖面",config["profile_name"]),("剖面时段",config["profile_period"]),("输入校验码",config["profile_checksum"]),("到达率λ(次/分钟)",config["arrival_rate"]),("单窗口服务率μ(次/分钟)",config["service_rate"]),("到达倍率",config["arrival_multiplier"]),("服务倍率",config["service_multiplier"]),("基准窗口数",config["baseline_windows"]),("候选窗口数",config["candidate_windows"]),("观测时域(分钟)",config["duration_minutes"]),("预热(分钟)",config["warmup_minutes"]),("重复次数",config["replications"]),("随机种子",config["seed"]),("基准理论稳态等待(分钟)",result["baseline"]["analytic"]["mean_wait_minutes"] if result["baseline"]["analytic"]["stable"] else "无有限稳态值"),("候选理论稳态等待(分钟)",result["candidate"]["analytic"]["mean_wait_minutes"] if result["candidate"]["analytic"]["stable"] else "无有限稳态值"),("差值口径",paired["difference_definition"]),("配对差值均值(分钟)",paired["mean_difference_minutes"]),("配对差值95%区间下界",paired["difference_ci95"][0]),("配对差值95%区间上界",paired["difference_ci95"][1]),("配对差值标准差(分钟)",paired["sd_difference_minutes"]),("区间方法",paired["ci_method"])]
 writer=csv.DictWriter(buf,fieldnames=["条目","值"]);writer.writeheader();writer.writerows([{"条目":key,"值":value} for key,value in config_rows])
 buf.write("\n")
 columns=["replication","arrivals","baseline_mean_wait_minutes","candidate_mean_wait_minutes","difference_minutes","baseline_p_wait","candidate_p_wait","baseline_busy_fraction","candidate_busy_fraction","baseline_max_wait_minutes","candidate_max_wait_minutes"]
 writer=csv.DictWriter(buf,fieldnames=columns);writer.writeheader();writer.writerows([{key:row[key] for key in columns} for row in paired["replications"]])
 return "﻿"+buf.getvalue()
