from __future__ import annotations

import argparse, csv, importlib, json, sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network.inference import NeuralHeuristicPredictor
from rs_cx.common import CXGlobalConfig, fuse_nonholonomic, nonholonomic_base_and_correction
from rs_cx4.common import ACCEPTED_CX3D_PARAMS
from rs_cx3.cx3_d_hpg import build_nonholonomic_field as build_cx3d_nonholonomic
from rs_cx6.common import accepted_bundle_nonholonomic
from scripts.evaluate_baselines import _load_nonholonomic_case, _make_rs_anchor, _path_length, _run_hybrid_method

CX6_MODULES = {'CX6-A':'rs_cx6.cx6_a_aic','CX6-B':'rs_cx6.cx6_b_crl','CX6-C':'rs_cx6.cx6_c_pmc','CX6-D':'rs_cx6.cx6_d_dce'}

def parse_args():
    p=argparse.ArgumentParser(description='Run P0-CX6 public parasol ablations.')
    p.add_argument('--parasol-root', type=Path, default=Path('data/benchmark/parasol_narrow/test'))
    p.add_argument('--hard-benchmark-root', type=Path, default=Path('data/benchmark/rs_root_hard_v2'))
    p.add_argument('--chosen-root', type=Path, default=Path('outputs/rs_p0cx6_main_trials_v1'))
    p.add_argument('--exp3-detail', type=Path, default=Path('outputs/paper/manual_v11b_exp3_full/logs/exp_results_detail.json'))
    p.add_argument('--exp4-detail', type=Path, default=Path('outputs/paper/manual_v11b_exp4_fair/logs/exp_results_detail.json'))
    p.add_argument('--ours-checkpoint', type=Path, default=Path('outputs/checkpoints/exp3_final_manual_v11b.pt'))
    p.add_argument('--device', type=str, default='cuda')
    p.add_argument('--variants', type=str, default='CX6-A,CX6-B,CX6-C,CX6-D')
    p.add_argument('--families', type=str, default='narrow_passage,maze,deadend_labyrinth')
    p.add_argument('--dev-per-family', type=int, default=2)
    p.add_argument('--fixed-cap-exp3', type=int, default=7000)
    p.add_argument('--fixed-cap-exp4', type=int, default=20000)
    p.add_argument('--out-root', type=Path, default=Path('outputs/rs_p0cx6_ablation_v1'))
    p.add_argument('--reports-root', type=Path, default=Path('reports'))
    return p.parse_args()

def _variants(raw): return [x.strip() for x in str(raw).split(',') if x.strip()]
def _families(raw): return {x.strip() for x in str(raw).split(',') if x.strip()}

def _hard_dev_files(root, families, per_family):
    buckets=defaultdict(list)
    for p in sorted((root/'dev').glob('sample_*.npz')):
        with np.load(p, allow_pickle=False) as z: scen=str(z['scenario'])
        if scen not in families: continue
        buckets[scen].append(p)
    out=[]
    for scen, files in sorted(buckets.items()): out.extend(files[:int(per_family)])
    return out

def _plain_residual_field(case, predictor, cfg):
    rs_base, corr3d, _ = nonholonomic_base_and_correction(case, predictor, cfg, residual_alpha=float(ACCEPTED_CX3D_PARAMS.residual_alpha))
    return fuse_nonholonomic(rs_base, corr3d, cfg.residual_floor_ratio)

def _load_parasol_cases(root): return [{'path':p,'case':_load_nonholonomic_case(p)} for p in sorted(root.glob('sample_*.npz'))]
def _load_frozen_rows(path,budget_name,allowed):
    rows=json.loads(path.read_text(encoding='utf-8')); out=[]
    for row in rows:
        method=str(row['method'])
        if method not in allowed: continue
        out.append({'budget':budget_name,'sample_name':str(row['case_id']),'method':method,'success':float(row['success']),'expansions':float(row['expansions']),'path_length':float(row['path_length']) if row['path_length'] is not None else float('nan'),'time_ms':float(row['runtime_ms'])})
    return out

def _aggregate(rows,budget_name):
    method_summary=[]; family_summary=[]
    methods=sorted({str(r['method']) for r in rows if r['budget']==budget_name})
    for method in methods:
        grp=[r for r in rows if r['budget']==budget_name and r['method']==method]
        method_summary.append({'budget':budget_name,'method':method,'num_cases':len(grp),'success_rate':float(np.mean([r['success'] for r in grp])),'avg_expansions':float(np.mean([r['expansions'] for r in grp])),'avg_path_length':float(np.nanmean([r['path_length'] for r in grp])),'avg_time_ms':float(np.mean([r['time_ms'] for r in grp]))})
    fam_methods=defaultdict(list)
    for r in rows:
        if r['budget']==budget_name: fam_methods[(str(r['scenario']),str(r['method']))].append(r)
    for (scenario,method), grp in sorted(fam_methods.items()):
        family_summary.append({'budget':budget_name,'scenario':scenario,'method':method,'num_cases':len(grp),'success_rate':float(np.mean([r['success'] for r in grp])),'avg_expansions':float(np.mean([r['expansions'] for r in grp])),'avg_time_ms':float(np.mean([r['time_ms'] for r in grp]))})
    return method_summary,family_summary

def _method_lookup(summary_rows,budget_name,method):
    for row in summary_rows:
        if row['budget']==budget_name and row['method']==method: return row
    raise KeyError((budget_name,method))

def main():
    args=parse_args(); predictor=NeuralHeuristicPredictor(args.ours_checkpoint,device=args.device,gaussian_sigma=2.5); cfg=CXGlobalConfig(); args.out_root.mkdir(parents=True,exist_ok=True); args.reports_root.mkdir(parents=True,exist_ok=True)
    parasol_cases=_load_parasol_cases(args.parasol_root); print(f'[rs-p0cx6-ablation] preload parasol cases={len(parasol_cases)}')
    scenario_map={item['path'].name:str(item['case']['scenario']) for item in parasol_cases}
    exp3_frozen=_load_frozen_rows(args.exp3_detail,'exp3',{'Full','No-Residual','No-RS'}); exp4_frozen=_load_frozen_rows(args.exp4_detail,'exp4',{'Hybrid A* (RS)','Ours'}); print(f'[rs-p0cx6-ablation] loaded frozen rows exp3={len(exp3_frozen)} exp4={len(exp4_frozen)}')
    dev_files=_hard_dev_files(args.hard_benchmark_root,_families(args.families),args.dev_per_family); dev_cases=[]
    for p in dev_files:
        case=_load_nonholonomic_case(p); _, field=accepted_bundle_nonholonomic(case,predictor,cfg); cx3d=_run_hybrid_method(case,_make_rs_anchor(case,rs_field=field),max_expansions=7000); dev_cases.append({'path':p,'case':case,'cx3d':cx3d})
    for key in _variants(args.variants):
        chosen_path=args.chosen_root / key.lower().replace('-','_') / 'chosen.json'
        if not chosen_path.exists(): raise FileNotFoundError(chosen_path)
        chosen=json.loads(chosen_path.read_text(encoding='utf-8')); params=chosen['params']; print(f'[rs-p0cx6-ablation:{key}] chosen params={params}')
        mod=importlib.import_module(CX6_MODULES[key]); build_nonh=getattr(mod,'build_nonholonomic_field'); p_obj=type('P',(),params)(); memory=mod.build_dev_memory(dev_cases,predictor,cfg,p_obj) if hasattr(mod,'build_dev_memory') else None
        rows=[]
        for row in exp3_frozen + exp4_frozen: rows.append({**row,'scenario':scenario_map[row['sample_name']]})
        total=len(parasol_cases)
        for i,item in enumerate(parasol_cases,start=1):
            case=item['case']; sample_name=item['path'].name; plain_field=_plain_residual_field(case,predictor,cfg); _,cx3d_field=accepted_bundle_nonholonomic(case,predictor,cfg); cx6_field=build_nonh(case,predictor,cfg,p_obj,memory) if memory is not None else build_nonh(case,predictor,cfg,p_obj)
            for budget_name,budget in [('exp3',args.fixed_cap_exp3),('exp4',args.fixed_cap_exp4)]:
                plain=_run_hybrid_method(case,_make_rs_anchor(case,rs_field=plain_field),max_expansions=int(budget)); cx3d=_run_hybrid_method(case,_make_rs_anchor(case,rs_field=cx3d_field),max_expansions=int(budget)); cx6=_run_hybrid_method(case,_make_rs_anchor(case,rs_field=cx6_field),max_expansions=int(budget))
                for method,result in [('Plain-Residual',plain),('CX3-D',cx3d),(key,cx6)]: rows.append({'budget':budget_name,'sample_name':sample_name,'scenario':str(case['scenario']),'method':method,'success':float(result['success']),'expansions':float(result['expansions']),'path_length':float(_path_length(result['path'])) if result['path'] else float('nan'),'time_ms':float(result['runtime_ms'])})
            if i % 5 == 0 or i == total: print(f'[rs-p0cx6-ablation:{key}] parasol {i}/{total}')
        method_summary=[]; family_summary=[]
        for budget_name in ['exp3','exp4']:
            ms,fs=_aggregate(rows,budget_name); method_summary.extend(ms); family_summary.extend(fs)
        out_dir=args.out_root / key.lower().replace('-','_'); out_dir.mkdir(parents=True,exist_ok=True)
        with (out_dir/'case_rows.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
        with (out_dir/'method_summary.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(method_summary[0].keys())); w.writeheader(); w.writerows(method_summary)
        with (out_dir/'family_summary.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(family_summary[0].keys())); w.writeheader(); w.writerows(family_summary)
        exp3_cx=_method_lookup(method_summary,'exp3',key); exp3_plain=_method_lookup(method_summary,'exp3','Plain-Residual'); exp3_cx3d=_method_lookup(method_summary,'exp3','CX3-D'); exp3_full=_method_lookup(method_summary,'exp3','Full')
        exp4_cx=_method_lookup(method_summary,'exp4',key); exp4_plain=_method_lookup(method_summary,'exp4','Plain-Residual'); exp4_cx3d=_method_lookup(method_summary,'exp4','CX3-D'); exp4_ours=_method_lookup(method_summary,'exp4','Ours')
        report=[f'# {key} Ablation Report','',f'- chosen params: `{params}`','', '## EXP3', f"- {key} success=`{exp3_cx['success_rate']:.6f}` vs CX3-D=`{exp3_cx3d['success_rate']:.6f}` vs Plain=`{exp3_plain['success_rate']:.6f}` vs Full=`{exp3_full['success_rate']:.6f}`", f"- {key} expansions=`{exp3_cx['avg_expansions']:.3f}` vs CX3-D=`{exp3_cx3d['avg_expansions']:.3f}` vs Plain=`{exp3_plain['avg_expansions']:.3f}` vs Full=`{exp3_full['avg_expansions']:.3f}`", f"- {key} time_ms=`{exp3_cx['avg_time_ms']:.3f}` vs CX3-D=`{exp3_cx3d['avg_time_ms']:.3f}` vs Plain=`{exp3_plain['avg_time_ms']:.3f}`", '', '## EXP4', f"- {key} success=`{exp4_cx['success_rate']:.6f}` vs CX3-D=`{exp4_cx3d['success_rate']:.6f}` vs Plain=`{exp4_plain['success_rate']:.6f}` vs Ours=`{exp4_ours['success_rate']:.6f}`", f"- {key} expansions=`{exp4_cx['avg_expansions']:.3f}` vs CX3-D=`{exp4_cx3d['avg_expansions']:.3f}` vs Plain=`{exp4_plain['avg_expansions']:.3f}` vs Ours=`{exp4_ours['avg_expansions']:.3f}`", f"- {key} time_ms=`{exp4_cx['avg_time_ms']:.3f}` vs CX3-D=`{exp4_cx3d['avg_time_ms']:.3f}` vs Plain=`{exp4_plain['avg_time_ms']:.3f}`"]
        (args.reports_root / f'rs_p0cx6_{key.lower().replace("-","_")}_ablation_v1.md').write_text('\n'.join(report),encoding='utf-8')
        print(f'[rs-p0cx6-ablation] finished {key}')

if __name__ == '__main__':
    main()
