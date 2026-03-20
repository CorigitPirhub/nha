from __future__ import annotations

import json
from pathlib import Path

from rs_cx34.cx34_a_msr import CX34AMSRParams


CURRENT_RS_MAINLINE_NAME = 'RS + CX34-A / Subtype-Specific Macro Rescue'
CURRENT_RS_MAINLINE_SCOPE = 'public/full-support + hard-test'
CURRENT_RS_MAINLINE_CANONICAL_DEVICE = 'cpu'
CURRENT_RS_MAINLINE_HARD_TEST_CONSUMED = True
CURRENT_RS_MAINLINE_HARD_EVAL_DEVICE = 'cuda'

CANONICAL_OUTPUT_ROOT = Path('outputs/rs_p0cx34_a_pilot_v1')
CANONICAL_CHOSEN_JSON = CANONICAL_OUTPUT_ROOT / 'chosen.json'
CANONICAL_SUMMARY_REPORT = Path('reports/rs_p0cx34_round1_summary.md')
CANONICAL_RECHECK_REPORT = Path('reports/rs_p0cx34_recheck_audit_v1.md')
CANONICAL_SUPPORT_AUDIT = Path('reports/rs_p0cx34_standard_audit_v1.md')
CANONICAL_HARD_EVAL_ROOT = Path('outputs/rs_p0cx34_a_hard_eval_cuda_v1')
CANONICAL_HARD_EVAL_REPORT = Path('reports/rs_p0cx34_a_hard_eval_v1.md')


def load_current_mainline_params(chosen_json: Path = CANONICAL_CHOSEN_JSON) -> CX34AMSRParams:
    data = json.loads(Path(chosen_json).read_text(encoding='utf-8'))
    return CX34AMSRParams(**data['params'])


__all__ = [
    'CANONICAL_CHOSEN_JSON',
    'CANONICAL_HARD_EVAL_REPORT',
    'CANONICAL_HARD_EVAL_ROOT',
    'CANONICAL_OUTPUT_ROOT',
    'CANONICAL_RECHECK_REPORT',
    'CANONICAL_SUMMARY_REPORT',
    'CANONICAL_SUPPORT_AUDIT',
    'CURRENT_RS_MAINLINE_CANONICAL_DEVICE',
    'CURRENT_RS_MAINLINE_HARD_EVAL_DEVICE',
    'CURRENT_RS_MAINLINE_HARD_TEST_CONSUMED',
    'CURRENT_RS_MAINLINE_NAME',
    'CURRENT_RS_MAINLINE_SCOPE',
    'load_current_mainline_params',
]
