"""On-device envelope profiler for MindsOS (Tier 1 — run this ON the Mac Mini).

Measures the honest, baseline-free deployment envelope:
  - hardware / OS / CPU-only confirmation
  - peak process RAM (RSS) and peak Python-object memory during a task
  - wall-clock to compose + run a task on this CPU
  - load-on-demand SELECTIVITY: how few capabilities a task instantiates
    out of the full registered catalog (the "loads only what it needs" claim)

It does NOT compare against a neural baseline — that is Tier 2 (FLOPs at
matched competence), which needs a shared task + a tuned baseline (see the
measurement protocol). Do not present these envelope numbers as a compute
WIN; present them as the envelope MindsOS runs in.
"""
from __future__ import annotations
import os, sys, time, platform, resource, tracemalloc, subprocess, statistics

def _sysctl(key):
    try:
        return subprocess.check_output(["sysctl","-n",key], text=True).strip()
    except Exception:
        return None

def hardware():
    info = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "logical_cpus": os.cpu_count(),
        "gpu_used": "no (pure CPU)",
    }
    if sys.platform == "darwin":
        info["cpu"] = _sysctl("machdep.cpu.brand_string") or platform.processor()
        mem = _sysctl("hw.memsize")
        info["ram_gb"] = round(int(mem)/1e9, 1) if mem else None
    else:
        info["cpu"] = platform.processor() or "unknown"
    return info

def peak_rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r/1024/1024 if sys.platform == "darwin" else r/1024  # mac=bytes, linux=KB

# ── the workload: real MindsOS if importable, else a stub so the harness is testable ──
def build_and_run(n_decoys=20, repeats=25):
    try:
        from mindsos_capacity import (Capacity, CapacityLayer, DataState, ShapeDescriptor,
            INPUT_GROUP_ALL_REQUIRED, CATEGORY_PERCEPTION, CATEGORY_COMPREHENSION, CATEGORY_DECISION)
        from mindsos_capacity.pipeline import find_pipeline
        from mindsos_capacity.runtime import invoke
        from mindsos_intelligence.pipeline_execution import execute_pipeline
    except Exception as e:
        return {"backend": f"STUB (MindsOS not importable here: {e.__class__.__name__})",
                "catalog": None, "used": None, "walltime_ms": None, "note":
                "Run this on the Mac Mini at the repo root to get real numbers."}

    IRI = lambda s: f"datastate:t.{s}"
    RAW,PARSED,NORMAL,COND,ACTION = map(IRI,("raw_signal","parsed_signal","normal_signal","condition","action"))
    CONDS = {"pressure_high":"vent","pressure_low":"seal","nominal":"hold"}
    ds = lambda s:(lambda n: DataState(name=n, shape=ShapeDescriptor.scalar("str",opaque_tag=n)))(f"t.{s}")
    cap = lambda name,cat,i,o,f: Capacity(name=name,category=cat,inputs=tuple(i),outputs=tuple(o),
                                          input_group=INPUT_GROUP_ALL_REQUIRED,implementation=f)
    cl = CapacityLayer(categories=(CATEGORY_PERCEPTION,CATEGORY_COMPREHENSION,CATEGORY_DECISION))
    for s in ("raw_signal","parsed_signal","normal_signal","condition","action"):
        cl.register_datastate(ds(s), allow_new_realm=True)
    cl.register_capacity(cap("parse",CATEGORY_PERCEPTION,[RAW],[PARSED], lambda **k:{PARSED:str(k[RAW]).strip().lower()}))
    cl.register_capacity(cap("normalize",CATEGORY_COMPREHENSION,[PARSED],[NORMAL], lambda **k:{NORMAL:k[PARSED].replace(" ","_")}))
    cl.register_capacity(cap("classify",CATEGORY_DECISION,[NORMAL],[COND], lambda **k:{COND:k[NORMAL]} if k[NORMAL] in CONDS else {COND:"nominal"}))
    cl.register_capacity(cap("recommend",CATEGORY_DECISION,[COND],[ACTION], lambda **k:{ACTION:CONDS.get(k[COND],"hold")}))
    used_caps = 4
    # decoys: unrelated capabilities in the catalog the task must NOT touch
    for j in range(n_decoys):
        a,b = IRI(f"decoy_in_{j}"), IRI(f"decoy_out_{j}")
        for s in (f"decoy_in_{j}",f"decoy_out_{j}"): cl.register_datastate(ds(s), allow_new_realm=True)
        cl.register_capacity(cap(f"decoy_{j}",CATEGORY_PERCEPTION,[a],[b], lambda **k:{}))
    catalog = used_caps + n_decoys

    class D:
        def __init__(s,cl): s.cl=cl
        def dispatch(s,ci,inp,*,cancel_token=None,task_id=None,step_id=None):
            return invoke(s.cl.get_declaration(ci),inp,task_id=task_id,step_id=step_id)
    disp = D(cl)
    times=[]
    for _ in range(repeats):
        t=time.perf_counter()
        pipe = find_pipeline(cl, start_datastate=RAW, target_datastate=ACTION)
        execute_pipeline(disp, pipe, {RAW:"Pressure High"}, task_id="prof")
        times.append((time.perf_counter()-t)*1000)
    return {"backend":"MindsOS (real)","catalog":catalog,"used":len(pipe.steps),
            "walltime_ms":round(statistics.median(times),3),"note":None}

def main():
    tracemalloc.start()
    hw = hardware()
    res = build_and_run()
    py_cur, py_peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    print("="*58); print("MindsOS on-device envelope"); print("="*58)
    for k,v in hw.items(): print(f"  {k:14s}: {v}")
    print("-"*58)
    print(f"  backend        : {res['backend']}")
    if res["catalog"] is not None:
        print(f"  catalog size   : {res['catalog']} capabilities registered")
        print(f"  task used      : {res['used']} capabilities  "
              f"(load-on-demand: {res['used']}/{res['catalog']} = "
              f"{100*res['used']/res['catalog']:.0f}% of catalog instantiated)")
        print(f"  compose+run    : {res['walltime_ms']} ms (median) on this CPU")
    print(f"  peak process RAM: {peak_rss_mb():.1f} MB (RSS)")
    print(f"  peak py-objects : {py_peak/1e6:.1f} MB")
    if res["note"]: print(f"  NOTE           : {res['note']}")
    print("="*58)
    print("Envelope only — NOT a compute win. The FLOPs-at-matched-competence")
    print("comparison vs a tuned baseline is Tier 2 (see the protocol).")

if __name__ == "__main__":
    main()
