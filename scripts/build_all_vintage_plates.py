#!/usr/bin/env python3
"""
scripts/build_all_vintage_plates.py

Master Engraving Folio Builder for Plates XXII through XXXII.
Generates 11 bespoke, publication-grade vintage cybernetics plates in the exact
style of social_cognition_pragmatics.jpg:
- Pure monochrome black ink (#181410) only; strictly ZERO colored fonts or lines.
- Authentic weathered parchment background with tattered crinkled edges extending to borders.
- Genuine historical scientific/mechanical engravings seamlessly integrated.
- Crisp classical Roman serif typography (Georgia, Georgia Bold, Consolas).
- Precise architectural diagrams directly reflecting ToMi codebase and README.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont
import numpy as np

INK = (24, 20, 16)
INK_MID = (55, 45, 35)
INK_MUTED = (85, 72, 60)

FONT_TITLE = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 26)
FONT_SUBTITLE = ImageFont.truetype('C:\\Windows\\Fonts\\georgia.ttf', 14)
FONT_HEAD = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 15)
FONT_BODY = ImageFont.truetype('C:\\Windows\\Fonts\\georgia.ttf', 13)
FONT_BODY_B = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 13)
FONT_SMALL = ImageFont.truetype('C:\\Windows\\Fonts\\georgia.ttf', 11)
FONT_SMALL_B = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 11)
FONT_CODE = ImageFont.truetype('C:\\Windows\\Fonts\\consolab.ttf', 12)

PARCHMENT_BASE = 'scratch/perfect_parchment.jpg'

def get_base_canvas():
    return Image.open(PARCHMENT_BASE).convert('RGB')

def draw_header(draw, title, subtitle):
    tw = draw.textlength(title, font=FONT_TITLE)
    sw = draw.textlength(subtitle, font=FONT_SUBTITLE)
    draw.text(((1376 - tw) / 2, 40), title, fill=INK, font=FONT_TITLE)
    draw.text(((1376 - sw) / 2, 73), subtitle, fill=INK_MUTED, font=FONT_SUBTITLE)
    draw.line([1376 / 2 - 340, 95, 1376 / 2 + 340, 95], fill=INK, width=1)

def paste_engraving(canvas, crop_path, dest_box, paper_lum=215.0, feather=25):
    dx, dy, dw, dh = dest_box
    src = Image.open(crop_path).convert('RGB')
    src = src.resize((dw, dh), Image.Resampling.LANCZOS)
    src_arr = np.array(src, dtype=np.float32)
    
    lum = 0.299 * src_arr[:, :, 0] + 0.587 * src_arr[:, :, 1] + 0.114 * src_arr[:, :, 2]
    darken = np.clip(lum / paper_lum, 0.0, 1.0)
    
    mask = np.ones((dh, dw), dtype=np.float32)
    for i in range(feather):
        f = (i + 1) / feather
        mask[i, :] = np.minimum(mask[i, :], f)
        mask[dh - 1 - i, :] = np.minimum(mask[dh - 1 - i, :], f)
        mask[:, i] = np.minimum(mask[:, i], f)
        mask[:, dw - 1 - i] = np.minimum(mask[:, dw - 1 - i], f)
        
    attenuation = 1.0 - (1.0 - darken) * mask
    
    canvas_arr = np.array(canvas, dtype=np.float32)
    canvas_arr[dy:dy+dh, dx:dx+dw] = canvas_arr[dy:dy+dh, dx:dx+dw] * attenuation[:, :, None]
    return Image.fromarray(np.clip(canvas_arr, 0, 255).astype(np.uint8))

def draw_flow_arrow(draw, x1, y1, x2, y2, label=None, label_side='right'):
    draw.line([x1, y1, x2, y2], fill=INK, width=2)
    ang = math.atan2(y2 - y1, x2 - x1)
    al = 8
    aw = 5
    p1 = (x2 - al * math.cos(ang) + aw * math.sin(ang), y2 - al * math.sin(ang) - aw * math.cos(ang))
    p2 = (x2 - al * math.cos(ang) - aw * math.sin(ang), y2 - al * math.sin(ang) + aw * math.cos(ang))
    draw.polygon([(x2, y2), p1, p2], fill=INK)
    if label:
        if label_side == 'right':
            lx = x2 + 10
            ly = (y1 + y2) / 2 - 6
            draw.text((lx, ly), label, fill=INK, font=FONT_SMALL)
        elif label_side == 'top':
            lx = (x1 + x2) / 2
            ly = (y1 + y2) / 2 - 13
            lw = draw.textlength(label, font=FONT_SMALL)
            draw.text((lx - lw / 2, ly), label, fill=INK, font=FONT_SMALL)
        else:
            lx = (x1 + x2) / 2
            ly = (y1 + y2) / 2 + 3
            lw = draw.textlength(label, font=FONT_SMALL)
            draw.text((lx - lw / 2, ly), label, fill=INK, font=FONT_SMALL)

# =============================================================================
# PLATE XXII: PLANNER WORLD-MODEL & PRE-MORTEM CONTRACT
# =============================================================================
def build_plate_xxii():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/tight_optical.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXII: ToMi PLANNER WORLD-MODEL & PRE-MORTEM CONTRACT',
                'COUNTERFACTUAL CATASTROPHE SIMULATION & DEPENDENCY INTERLOCK GOVERNOR')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'HIGH-CONSEQUENCE DIRECTIVE INPUT', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Dispatched to isolated Planner profile before any command execution', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'World-model layer preventing irreversible execution disasters', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Subterranean Optical Vault & Stereoscopic Beam Splitter Apparatus', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    
    # Stage 1: World-Model Counterfactual Simulation
    draw.rectangle([rx, 115, rx + rw, 270], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + rw - 3, 267], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 124), 'WORLD-MODEL COUNTERFACTUAL SIMULATION (planner.py)', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 146, rx + rw - 20, 146], fill=INK_MUTED, width=1)
    s1_lines = [
        ('Core Simulation Contract:', FONT_BODY_B),
        ('  • Nominal Forward Rollout: Generates ordered steps with strict state preconditions', FONT_BODY),
        ('  • Pre-Mortem Premise: "Assume this plan failed catastrophically. What was the root cause?"', FONT_BODY_B),
        ('  • Reversibility Audit: Flags permanent file mutations, table drops, or network broadcasts', FONT_BODY),
        ('  • Epistemic Grounding: Replaces speculative language with verified knowledge base facts', FONT_BODY)
    ]
    cy = 152
    for txt, fnt in s1_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 17
        
    # Stage 2: Three Invariant Trip Clutches
    draw.rectangle([rx, 310, rx + rw, 465], outline=INK, width=2)
    draw.rectangle([rx + 3, 313, rx + rw - 3, 462], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 318), 'THE THREE INVARIANT TRIP CLUTCHES', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 340, rx + rw - 20, 340], fill=INK_MUTED, width=1)
    s2_lines = [
        ('1. Dependency Interlock Clutch:', FONT_BODY_B),
        ('   Uncovers hidden DAG dependencies, missing packages, and implicit prerequisites.', FONT_BODY),
        ('2. Irreversibility Brake Clutch:', FONT_BODY_B),
        ('   Enforces compulsory pre-flight backup snapshot before destructive filesystem or DB changes.', FONT_BODY),
        ('3. Epistemic Assumption Clutch:', FONT_BODY_B),
        ('   Rejects plan steps predicated on assertions with confidence c < 0.90 without probing.', FONT_BODY)
    ]
    cy = 346
    for txt, fnt in s2_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 17
        
    # Stage 3: Certified Plan Contract Output
    draw.rectangle([rx, 505, rx + rw, 655], outline=INK, width=2)
    draw.rectangle([rx + 3, 508, rx + rw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 513), 'CERTIFIED PLAN CONTRACT -> TO STRIATAL ACTION GATE', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 535, rx + rw - 20, 535], fill=INK_MUTED, width=1)
    s3_lines = [
        ('Contract Output Payload:', FONT_BODY_B),
        ('  plan_contract = {', FONT_CODE),
        ('    "steps": ["step1_verified", "step2_verified"],  "consequence": "HIGH",', FONT_CODE),
        ('    "pre_mortem_risk": 0.12,  "rollback_snapshot": "~/.hermes/backup/snap_42"', FONT_CODE),
        ('  }', FONT_CODE),
        ('Dispatched directly to hooks/brain-cognitive-guard for bounded-latency enforcement.', FONT_BODY)
    ]
    cy = 542
    for txt, fnt in s3_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 16
        
    # Flow Arrows with side labels
    draw_flow_arrow(draw, rx + rw/2, 270, rx + rw/2, 310, 'Pass Simulation', 'right')
    draw_flow_arrow(draw, rx + rw/2, 465, rx + rw/2, 505, 'All Clutches Cleared', 'right')
    draw_flow_arrow(draw, 500, 385, rx, 385, 'Beam Split', 'top')
    
    draw.text((rx + 20, 672), 'Architectural Principle: Planning is the practical world-model layer preventing irreversible execution disasters.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/planner_world_model_contract.jpg', quality=95)
    print('Plate XXII saved to assets/planner_world_model_contract.jpg')

# =============================================================================
# PLATE XXIII: ACTION GATE DECISION MATRIX
# =============================================================================
def build_plate_xxiii():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/brain_crop.jpg', (55, 190, 430, 470))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXIII: ToMi STRIATAL INHIBITORY ACTION GATE DECISION MATRIX',
                'BASAL GANGLIA ACTION SELECTION & BOUNDED-LATENCY EXECUTION ENFORCEMENT')
    
    draw.rectangle([55, 115, 485, 175], outline=INK, width=2)
    draw.rectangle([58, 118, 482, 172], outline=INK_MUTED, width=1)
    draw.text((70, 123), 'STIMULUS: COMMAND:* HOOK EVENT', fill=INK, font=FONT_HEAD)
    draw.text((70, 143), 'Intercepted via hooks/brain-cognitive-guard (emit_collect)', fill=INK_MUTED, font=FONT_BODY)
    draw.text((70, 158), 'Enforces bounded-latency code brake (< 1ms shutoff)', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 670), 'Anatomical Striatal Circuitry (Caudate, Putamen, STN, GPi)', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 530
    rw = 780
    
    # Pathway 1: DIRECT PATHWAY (GO)
    draw.rectangle([rx, 115, rx + rw, 270], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + rw - 3, 267], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 124), 'DIRECT PATHWAY (GO) — ACTION AUTHORIZED', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 146, rx + rw - 20, 146], fill=INK_MUTED, width=1)
    p1_lines = [
        ('Activation Condition:', FONT_BODY_B),
        ('  • Preconditions strictly verified in Active Wiki or working system state', FONT_BODY),
        ('  • Epistemic uncertainty low (confidence c >= 0.85, risk score R < 0.30)', FONT_BODY),
        ('  • No conflicting or disputed assertions in belief state (tom.py / okf_gate)', FONT_BODY),
        ('Runtime Enforcement:', FONT_BODY_B),
        ('  • emit_collect() returns {"decision": "handled" | "proceed"}', FONT_CODE),
        ('  • Execution authorized immediately; trace logged to experience.db', FONT_BODY)
    ]
    cy = 152
    for txt, fnt in p1_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 16
        
    # Pathway 2: INDIRECT PATHWAY (NO-GO)
    draw.rectangle([rx, 310, rx + rw, 465], outline=INK, width=2)
    draw.rectangle([rx + 3, 313, rx + rw - 3, 462], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 318), 'INDIRECT PATHWAY (NO-GO) — INHIBITED EXECUTION', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 340, rx + rw - 20, 340], fill=INK_MUTED, width=1)
    p2_lines = [
        ('Activation Condition:', FONT_BODY_B),
        ('  • Unverified assumptions present or epistemic confidence c < 0.85', FONT_BODY),
        ('  • Disputed propositions discovered in knowledge base or recent session diff', FONT_BODY),
        ('  • High operational uncertainty requiring clarification or state inspection', FONT_BODY),
        ('Runtime Enforcement:', FONT_BODY_B),
        ('  • emit_collect() returns {"decision": "deny", "message": "[NO_GO: Epistemic risk]"}', FONT_CODE),
        ('  • Command actively HALTED before running; router dispatches Auditor profile', FONT_BODY)
    ]
    cy = 346
    for txt, fnt in p2_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 16
        
    # Pathway 3: HYPERDIRECT PATHWAY (EMERGENCY BRAKE)
    draw.rectangle([rx, 505, rx + rw, 655], outline=INK, width=2)
    draw.rectangle([rx + 3, 508, rx + rw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 513), 'HYPERDIRECT PATHWAY (EMERGENCY BRAKE) — HARD SHUTOFF', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 535, rx + rw - 20, 535], fill=INK_MUTED, width=1)
    p3_lines = [
        ('Activation Condition:', FONT_BODY_B),
        ('  • Irreversible destructive action detected (e.g. DROP TABLE, rm -rf, raw overwrite)', FONT_BODY),
        ('  • Safety invariant violation or un-sandboxed execution boundary breach', FONT_BODY),
        ('  • Critical state modification attempted without pre-flight backup snapshot', FONT_BODY),
        ('Runtime Enforcement:', FONT_BODY_B),
        ('  • emit_collect() returns {"decision": "deny", "message": "[HYPERDIRECT_BRAKE: Abort]"}', FONT_CODE),
        ('  • Instant code-level shutoff (bounded latency < 1ms, bypasses model deliberation)', FONT_BODY)
    ]
    cy = 541
    for txt, fnt in p3_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 16
        
    # Arrows from brain to pathways
    draw_flow_arrow(draw, 430, 260, rx, 192, 'Go Signal', 'top')
    draw_flow_arrow(draw, 450, 385, rx, 385, 'Inhibit Signal', 'top')
    draw_flow_arrow(draw, 410, 510, rx, 578, 'Emergency Stop', 'top')
    
    draw.text((rx + 20, 672), 'Hermes Hook Contract: agent:step discards returns. Only command:* honors deny via emit_collect().', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/action_gate_decision_matrix.jpg', quality=95)
    print('Plate XXIII saved to assets/action_gate_decision_matrix.jpg')

# =============================================================================
# PLATE XXIV: CONSEQUENCE-GATED EXECUTION & VOI MATRIX
# =============================================================================
def build_plate_xxiv():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/tight_scale.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXIV: ToMi CONSEQUENCE-GATED EXECUTION & VALUE OF INFORMATION',
                'EPISTEMIC UNCERTAINTY vs OPERATIONAL CONSEQUENCE 2x2 DECISION MATRIX')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'EPISTEMIC RISK BEAM BALANCE', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Weighs empirical ground truth against operational irreversibility', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Balancing verification cost against catastrophe risk', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Precision Knife-Edge Beam Balance & Epistemic Brake Apparatus', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    cx = rx + rw // 2
    cy = 115 + (655 - 115) // 2
    
    qw = 370
    qh = 255
    
    # Quadrant II (Top-Left): High Consequence, Low Uncertainty
    draw.rectangle([rx, 115, rx + qw, 115 + qh], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + qw - 3, 115 + qh - 3], outline=INK_MUTED, width=1)
    draw.text((rx + 15, 124), 'CAREFUL VERIFIED ROLLOUT', fill=INK, font=FONT_HEAD)
    draw.text((rx + 15, 144), 'HIGH CONSEQUENCE  |  LOW UNCERTAINTY', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + 15, 160, rx + qw - 15, 160], fill=INK_MUTED, width=1)
    q2_text = [
        ('Protocol:', FONT_BODY_B),
        ('• Mandatory pre-flight snapshot diff', FONT_BODY),
        ('• Step-by-step verification assertions', FONT_BODY),
        ('• Fail-closed rollback mechanism', FONT_BODY),
        ('• Log detailed audit trace to experience.db', FONT_BODY),
        ('Action: PROCEED WITH VERIFICATION', FONT_BODY_B)
    ]
    y = 168
    for t, f in q2_text:
        draw.text((rx + 15, y), t, fill=INK, font=f)
        y += 17
        
    # Quadrant I (Top-Right): High Consequence, High Uncertainty
    draw.rectangle([cx + 15, 115, cx + 15 + qw, 115 + qh], outline=INK, width=2)
    draw.rectangle([cx + 18, 118, cx + 15 + qw - 3, 115 + qh - 3], outline=INK_MUTED, width=1)
    draw.text((cx + 30, 124), 'CONSERVATIVE HALT & PRE-MORTEM', fill=INK, font=FONT_HEAD)
    draw.text((cx + 30, 144), 'HIGH CONSEQUENCE  |  HIGH UNCERTAINTY', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([cx + 30, 160, cx + 15 + qw - 15, 160], fill=INK_MUTED, width=1)
    q1_text = [
        ('Protocol:', FONT_BODY_B),
        ('• Active tool execution strictly DENIED', FONT_BODY_B),
        ('• Invoke Planner for pre-mortem simulation', FONT_BODY),
        ('• Dispatch Researcher / Auditor sub-agent', FONT_BODY),
        ('• Escalate to human operator for intent alignment', FONT_BODY),
        ('Action: HALT & SIMULATE FIRST', FONT_BODY_B)
    ]
    y = 168
    for t, f in q1_text:
        draw.text((cx + 30, y), t, fill=INK, font=f)
        y += 17

    # Quadrant III (Bottom-Left): Low Consequence, Low Uncertainty
    draw.rectangle([rx, cy + 15, rx + qw, cy + 15 + qh], outline=INK, width=2)
    draw.rectangle([rx + 3, cy + 18, rx + qw - 3, cy + 15 + qh - 3], outline=INK_MUTED, width=1)
    draw.text((rx + 15, cy + 24), 'AUTONOMOUS DIRECT EXECUTION', fill=INK, font=FONT_HEAD)
    draw.text((rx + 15, cy + 44), 'LOW CONSEQUENCE  |  LOW UNCERTAINTY', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + 15, cy + 60, rx + qw - 15, cy + 60], fill=INK_MUTED, width=1)
    q3_text = [
        ('Protocol:', FONT_BODY_B),
        ('• Direct System 1 fast-path execution', FONT_BODY),
        ('• Bypass heavy planning & sub-agents', FONT_BODY),
        ('• Cowan limit context optimization (<4 slots)', FONT_BODY),
        ('• Asynchronous telemetry logging', FONT_BODY),
        ('Action: EXECUTE IMMEDIATELY (GO)', FONT_BODY_B)
    ]
    y = cy + 68
    for t, f in q3_text:
        draw.text((rx + 15, y), t, fill=INK, font=f)
        y += 17

    # Quadrant IV (Bottom-Right): Low Consequence, High Uncertainty
    draw.rectangle([cx + 15, cy + 15, cx + 15 + qw, cy + 15 + qh], outline=INK, width=2)
    draw.rectangle([cx + 18, cy + 18, cx + 15 + qw - 3, cy + 15 + qh - 3], outline=INK_MUTED, width=1)
    draw.text((cx + 30, cy + 24), 'RAPID EMPIRICAL PROBING', fill=INK, font=FONT_HEAD)
    draw.text((cx + 30, cy + 44), 'LOW CONSEQUENCE  |  HIGH UNCERTAINTY', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([cx + 30, cy + 60, cx + 15 + qw - 15, cy + 60], fill=INK_MUTED, width=1)
    q4_text = [
        ('Protocol:', FONT_BODY_B),
        ('• Value of Information (VOI) > Probing Cost', FONT_BODY_B),
        ('• Run low-cost inspection command / probe', FONT_BODY),
        ('• Observe actual empirical diff directly', FONT_BODY),
        ('• Collapse uncertainty with reality check', FONT_BODY),
        ('Action: PROBE TO LEARN BEFORE ACTING', FONT_BODY_B)
    ]
    y = cy + 68
    for t, f in q4_text:
        draw.text((cx + 30, y), t, fill=INK, font=f)
        y += 17
        
    draw.text((rx + 20, 672), 'Invariable Rule: High consequence prevents assumption; low consequence prevents endless clarification.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/consequence_gated_execution.jpg', quality=95)
    print('Plate XXIV saved to assets/consequence_gated_execution.jpg')

# =============================================================================
# PLATE XXV: COGNITIVE ROUTING MODES
# =============================================================================
def build_plate_xxv():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/tight_rotary.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXV: ToMi DUAL-PROCESS COGNITIVE ROUTING MODES',
                'FOUR OPERATIONAL MODES: SYSTEM 1 HEURISTICS vs SYSTEM 2 DELIBERATION')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'CENTRAL COGNITIVE ROUTER (routing.py)', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Dynamic compute allocation matching task complexity & risk', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Stepped rotary transmission selecting execution gear', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Rotary Stepped Transmission & Epistemic Escapement Apparatus', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    step_h = 120
    
    modes = [
        ('MODE I: DIRECT SYSTEM 1 EXECUTION', 'Low complexity, low risk, high competence (C >= 0.85)', [
            '• Single-turn tool execution, exact wikilink / BM25 lexical lookup',
            '• Zero model deliberation; bounded latency < 50ms; telemetry to operations'
        ]),
        ('MODE II: REACTIVE DIALOGUE & SOCIAL PRAGMATICS', 'Conversational turn, user clarification, pedagogical calibration', [
            '• Theory of Mind (tom.py) epistemic discrepancy evaluation',
            '• Gricean maxim adherence: Quantity (5<=W<=600), Quality, Relation, Manner'
        ]),
        ('MODE III: DELIBERATIVE SYSTEM 2 ROLLOUT', 'High operational consequence, multi-step dependencies, irreversible mutations', [
            '• Planner world-model engagement with pre-mortem failure simulation',
            '• Three-layer verification enforcement; rollback snapshots created'
        ]),
        ('MODE IV: EPISTEMIC EXPANSION & SUB-AGENT RESEARCH', 'Knowledge void, contradictory evidence, or multi-hop relational queries', [
            '• Dispatches isolated sub-agents: Researcher (local SearXNG :8080) or Oracle Librarian',
            '• Pure 500-token crystal delta returned; zero context window clutter'
        ])
    ]
    
    y = 115
    for title, sub, bullets in modes:
        draw.rectangle([rx, y, rx + rw, y + step_h], outline=INK, width=2)
        draw.rectangle([rx + 3, y + 3, rx + rw - 3, y + step_h - 3], outline=INK_MUTED, width=1)
        draw.text((rx + 18, y + 10), title, fill=INK, font=FONT_HEAD)
        draw.text((rx + 18, y + 30), sub, fill=INK_MUTED, font=FONT_BODY_B)
        draw.line([rx + 18, y + 48, rx + rw - 18, y + 48], fill=INK_MUTED, width=1)
        by = y + 56
        for b in bullets:
            draw.text((rx + 18, by), b, fill=INK, font=FONT_BODY)
            by += 18
        y += step_h + 15
        
    draw.text((rx + 20, 672), 'Routing Rule: Dense hop-classifier routes single-hop to lexical index and multi-hop to graph diffusion.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/cognitive_routing_modes.jpg', quality=95)
    print('Plate XXV saved to assets/cognitive_routing_modes.jpg')

# =============================================================================
# PLATE XXVI: METACOGNITIVE ROUTING FLOW
# =============================================================================
def build_plate_xxvi():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/tight_horn.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXVI: ToMi METACOGNITIVE ROUTING ARBITRATION FLOW',
                'DYNAMIC HYDRAULIC GOVERNOR ARBITRATING BETWEEN SYSTEM 1 & SYSTEM 2')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'CENTRIFUGAL STIMULUS TRANSDUCER', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Measures task novelty, hop count, and epistemic volatility', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Acoustic horn feeding dual escapement evaluators', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Acoustic Brass Horn, Flyball Centrifugal Pendulum & Solenoid Distributor', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    
    # Input Stimulus Analysis Block
    draw.rectangle([rx, 115, rx + rw, 235], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + rw - 3, 232], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 124), 'STAGE I: PRE-TURN STIMULUS FEATURE EXTRACTION', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 146, rx + rw - 20, 146], fill=INK_MUTED, width=1)
    s1_lines = [
        ('• Evaluates Query Complexity: Hop count H in {1, >1}, token density, entity ambiguity', FONT_BODY),
        ('• Assesses Epistemic State: Confidence c, presence of disputed facts in okf_gate', FONT_BODY),
        ('• Estimates Consequence: Reversibility score gamma in [0, 1], destructive command flags', FONT_BODY),
        ('• Reads Historical Competence: Prior success rate mu from experience.db (Beta distribution)', FONT_BODY)
    ]
    cy = 153
    for txt, fnt in s1_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 17
        
    # Arbitration Decision Gate
    draw.rectangle([rx, 255, rx + rw, 385], outline=INK, width=2)
    draw.rectangle([rx + 3, 258, rx + rw - 3, 382], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 264), 'STAGE II: METACOGNITIVE ARBITRATION LOGIC', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 286, rx + rw - 20, 286], fill=INK_MUTED, width=1)
    s2_lines = [
        ('Arbitration Invariant:', FONT_BODY_B),
        ('  IF  Competence mu >= 0.85  AND  Hop Count H == 1  AND  Consequence gamma < 0.30:', FONT_CODE),
        ('      ROUTE -> SYSTEM 1 FAST-PATH (Instant Lexical / Direct Execution)', FONT_BODY_B),
        ('  ELSE (Hop Count H > 1  OR  Confidence c < 0.85  OR  Consequence gamma >= 0.30):', FONT_CODE),
        ('      ROUTE -> SYSTEM 2 DELIBERATIVE (Planner Pre-Mortem + Sub-Agent Research)', FONT_BODY_B),
        ('  Pre-turn stimulus analysis cached in ~/.hermes/cache/brain/cognition/ (300s TTL)', FONT_SMALL)
    ]
    cy = 292
    for txt, fnt in s2_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 14
        
    # Parallel Arms Execution
    aw = (rw - 20) // 2
    # Left Arm: System 1
    draw.rectangle([rx, 405, rx + aw, 655], outline=INK, width=2)
    draw.rectangle([rx + 3, 408, rx + aw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + 15, 415), 'SYSTEM 1: HEURISTIC ARM', fill=INK, font=FONT_HEAD)
    draw.text((rx + 15, 435), 'FAST, LOW-COMPUTE REFLEX', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + 15, 450, rx + aw - 15, 450], fill=INK_MUTED, width=1)
    sys1_text = [
        '• Direct tool call dispatch',
        '• Exact wiki title match (<5ms)',
        '• ParadeDB BM25 search (12ms)',
        '• Cowan limit context slots',
        '• Zero planning overhead',
        '• Bound latency: < 50ms'
    ]
    y = 460
    for t in sys1_text:
        draw.text((rx + 15, y), t, fill=INK, font=FONT_BODY)
        y += 24
        
    # Right Arm: System 2
    draw.rectangle([rx + aw + 20, 405, rx + rw, 655], outline=INK, width=2)
    draw.rectangle([rx + aw + 23, 408, rx + rw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + aw + 35, 415), 'SYSTEM 2: DELIBERATIVE ARM', fill=INK, font=FONT_HEAD)
    draw.text((rx + aw + 35, 435), 'HIGH-COMPUTE WORLD-MODEL', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + aw + 35, 450, rx + rw - 15, 450], fill=INK_MUTED, width=1)
    sys2_text = [
        '• Planner pre-mortem rollout',
        '• Graphify PPR graph diffusion',
        '• Isolated Researcher profile',
        '• Three-layer reality protocol',
        '• Compulsory rollback snapshot',
        '• Deep synthesis delta injection'
    ]
    y = 460
    for t in sys2_text:
        draw.text((rx + aw + 35, y), t, fill=INK, font=FONT_BODY)
        y += 24
        
    draw.text((rx + 20, 672), 'Empirical Finding: Single-hop queries degrade under graph RAG; multi-hop queries require diffusion.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/metacognitive_routing_flow.jpg', quality=95)
    print('Plate XXVI saved to assets/metacognitive_routing_flow.jpg')

# =============================================================================
# PLATE XXVII: EXPERIENCE COMPETENCE LOOP
# =============================================================================
def build_plate_xxvii():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/tight_peg.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXVII: ToMi EXPERIENCE COMPETENCE LOOP & 7-TABLE LEDGER',
                'BAYESIAN COMPETENCE TRACKING, REALITY AUDITING & EVIDENCE-GATED REFLECTION')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'MECHANICAL INTEGRATOR & COUNTER', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Revolving peg barrel ratchets success (alpha) vs failure (beta) gears', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Empirical feedback loop grounded in real-world outcomes', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Clockwork Music Box Drum, Trip Levers & Striking Action Bells', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    
    # Section 1: Bayesian Competence Tracker
    draw.rectangle([rx, 115, rx + rw, 255], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + rw - 3, 252], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 124), 'BAYESIAN COMPETENCE TRACKER: Beta(alpha, beta)', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 146, rx + rw - 20, 146], fill=INK_MUTED, width=1)
    b_lines = [
        ('Mathematical Formulation:', FONT_BODY_B),
        ('  Competence Metric: C = alpha / (alpha + beta)      Uncertainty Variance: sigma^2 = (alpha*beta) / ((alpha+beta)^2 * (alpha+beta+1))', FONT_CODE),
        ('• On Verified Success (Exit 0, State Diff Matches): alpha <- alpha + 1  (Strengthens fast-path)', FONT_BODY),
        ('• On Observed Failure (Non-zero exit, State Mismatch): beta <- beta + 1  (Demotes to Deliberative)', FONT_BODY),
        ('• Threshold: C >= 0.85 unlocks System 1 autonomous execution; C < 0.85 demands System 2 audit', FONT_BODY_B)
    ]
    cy = 152
    for txt, fnt in b_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 18
        
    # Section 2: The 7-Table Competence Ledger (experience.db)
    draw.rectangle([rx, 275, rx + rw, 505], outline=INK, width=2)
    draw.rectangle([rx + 3, 278, rx + rw - 3, 502], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 284), 'THE 7-TABLE COMPETENCE LEDGER (~/.hermes/personal-organizer/data/experience.db)', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 306, rx + rw - 20, 306], fill=INK_MUTED, width=1)
    tables = [
        ('1. operations:', 'Action execution traces (action, target, result, duration_ms, tokens_used)'),
        ('2. verification_checks:', 'Reality check comparisons (intended_state vs observed_reality)'),
        ('3. routing_events:', 'Cognitive profile dispatch decisions, router rationale, and success rates'),
        ('4. skill_events:', 'Procedural skill invocations, argument contracts, and error stack traces'),
        ('5. reflections:', 'Evidence-grounded architectural lessons, warnings, and pattern recognitions'),
        ('6. key_decisions:', 'Major system design choices, alternatives considered, and immutable rationale'),
        ('7. prospective_log:', 'Triggered future cue intentions, scheduled alerts, and execution outcomes')
    ]
    cy = 314
    for t_name, t_desc in tables:
        draw.text((rx + 20, cy), t_name, fill=INK, font=FONT_BODY_B)
        draw.text((rx + 220, cy), t_desc, fill=INK_MID, font=FONT_BODY)
        cy += 24
        
    # Section 3: Evidence-Gated Reflection
    draw.rectangle([rx, 525, rx + rw, 655], outline=INK, width=2)
    draw.rectangle([rx + 3, 528, rx + rw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 534), 'EVIDENCE-GATED REFLECTION (ZERO IDLE RUMINATION)', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 556, rx + rw - 20, 556], fill=INK_MUTED, width=1)
    r_lines = [
        ('Reflection is NEVER invoked on idle clocks. Triggered EXCLUSIVELY by:', FONT_BODY_B),
        ('  1. Verified command failure or non-zero exit code during execution.', FONT_BODY),
        ('  2. Unexpected state diff requiring recovery from unpredicted system conditions.', FONT_BODY),
        ('  3. Human user explicit correction, directive override, or negative feedback.', FONT_BODY),
        ('  4. Procedural skill runtime failure or precondition boundary breach.', FONT_BODY)
    ]
    cy = 562
    for txt, fnt in r_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 18
        
    draw.text((rx + 20, 672), 'Cardinal Rule: Reality gets the final vote. Competence grows through verified friction, not prompt drift.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/experience_competence_loop.jpg', quality=95)
    print('Plate XXVII saved to assets/experience_competence_loop.jpg')

# =============================================================================
# PLATE XXVIII: THREE-LAYER REALITY PROTOCOL
# =============================================================================
def build_plate_xxviii():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/tight_obelisk.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXVIII: ToMi THREE-LAYER REALITY VERIFICATION PROTOCOL',
                'FAIL-CLOSED HIERARCHICAL PROVING: CODE ASSERTIONS -> STATE DIFFS -> AUDITOR JUDGMENT')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'MONUMENTAL BEDROCK VERIFICATION', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Durable bedrock testing anchors disposable higher-level reasoning', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Fail-closed verification hierarchy ensuring operational integrity', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Ancient Stone Obelisk Bedrock & Modular Wooden Scaffolding', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    
    layers = [
        ('LAYER 1: DETERMINISTIC CODE ASSERTIONS (PRIMARY AUTHORITY)', 'Fastest, un-spoofable empirical proof; executed via deterministic shell & python tests', [
            '• Process exit code verification (must strictly evaluate: exit == 0)',
            '• File existence, non-zero size, and SHA256 checksum integrity verification',
            '• Process status (PID alive in OS table, listening socket bound on port)',
            '• Automated unit test suites (e.g. python -m unittest tests/test_*.py)',
            '• Evaluation Latency: < 15ms  |  Authority: Absolute & Fail-Closed'
        ]),
        ('LAYER 2: EMPIRICAL STATE VERIFICATION (DIFFERENTIAL SNAPSHOTS)', 'Diffing actual system state against expected post-conditions to detect side effects', [
            '• Pre-state snapshot taken before mutating command execution',
            '• Post-state snapshot captured immediately after command termination',
            '• Diff comparison: Verifies that ONLY intended files / DB rows changed',
            '• Detects leaked temporary artifacts, corrupted tables, or accidental deletes',
            '• Evaluation Latency: < 150ms  |  Authority: High Invariant Proof'
        ]),
        ('LAYER 3: AUDITOR JUDGMENT (FALLBACK QUALITATIVE REVIEW)', 'Invoked ONLY when deterministic tests cannot reach; governed by dedicated Auditor sub-agent', [
            '• Qualitative semantic review (e.g. conversational tone, UX visual elegance)',
            '• Multi-perspective adversarial debate on complex ambiguous trade-offs',
            '• Epistemic conflict resolution when knowledge base documents contradict',
            '• Strictly forbidden from overriding Layer 1 deterministic test failures',
            '• Evaluation Latency: ~1200ms  |  Authority: Subservient to Code'
        ])
    ]
    
    y = 115
    for title, sub, bullets in layers:
        draw.rectangle([rx, y, rx + rw, y + 165], outline=INK, width=2)
        draw.rectangle([rx + 3, y + 3, rx + rw - 3, y + 162], outline=INK_MUTED, width=1)
        draw.text((rx + 18, y + 11), title, fill=INK, font=FONT_HEAD)
        draw.text((rx + 18, y + 31), sub, fill=INK_MUTED, font=FONT_BODY_B)
        draw.line([rx + 18, y + 49, rx + rw - 18, y + 49], fill=INK_MUTED, width=1)
        by = y + 56
        for b in bullets:
            draw.text((rx + 18, by), b, fill=INK, font=FONT_BODY)
            by += 18
        y += 180
        
    draw.text((rx + 20, 672), 'Hierarchy Rule: If Layer 1 fails, execution halts instantly. Layer 3 can NEVER override a failing exit code.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/three_layer_verification_protocol.jpg', quality=95)
    print('Plate XXVIII saved to assets/three_layer_verification_protocol.jpg')

# =============================================================================
# PLATE XXIX: PROCEDURAL LEARNING EVOLUTION
# =============================================================================
def build_plate_xxix():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/tight_distill.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXIX: ToMi PROCEDURAL LEARNING & SKILL EVOLUTION',
                'METALLURGICAL DISTILLATION: FROM RAW EXECUTION TRACES TO NATIVE HERMES SKILLS')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'ALCHEMICAL DISTILLATION RETORT', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Smelts raw operational traces through condensation into pure reflex', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Procedural skill compilation pipeline from experience.db traces', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Alchemical Boiling Flask, Condensing Coil & Glass Carboy Vault', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    step_h = 120
    
    stages = [
        ('STAGE I: TRACE MINING & PATTERN EXTRACTION', 'Scanning experience.db for repeated, successful operational sequences', [
            '• Background consolidation daemon runs during idle periods',
            '• Clusters identical multi-step tool calls solving recurrent engineering problems',
            '• Prunes failed trajectories, non-zero exits, and conversational back-and-forth'
        ]),
        ('STAGE II: SKILL COMPILATION & SCHEMA SYNTHESIS', 'Casting refined procedures into standardized, governed skill templates', [
            '• Generates structured YAML frontmatter: name, description, tool requirements',
            '• Synthesizes deterministic execution scripts (scripts/*.py) and reference docs',
            '• Creates fail-closed parameter validation schemas to prevent hallucinated inputs'
        ]),
        ('STAGE III: BENCHMARK SUITE AUDITING', 'Rigorous automated testing in isolated virtual sandbox environments', [
            '• Drop-hammer test: Executes newly synthesized skill against test fixtures',
            '• Verifies Layer 1 deterministic exit codes (exit == 0) and state delta fidelity',
            '• Enforces sandboxing invariants: No un-sandboxed root escalations allowed'
        ]),
        ('STAGE IV: NATIVE RUNTIME PROMOTION', 'Deployment to active Hermes Skill repository (~/.hermes/skills/)', [
            '• Installed into agent skill discovery path for instant zero-deliberation reflex',
            '• Published via scrubbed publisher: python3 scripts/publish_profiles_and_skills.py',
            '• Full provenance tracked: Origin trace, author model, compilation date'
        ])
    ]
    
    y = 115
    for title, sub, bullets in stages:
        draw.rectangle([rx, y, rx + rw, y + step_h], outline=INK, width=2)
        draw.rectangle([rx + 3, y + 3, rx + rw - 3, y + step_h - 3], outline=INK_MUTED, width=1)
        draw.text((rx + 18, y + 10), title, fill=INK, font=FONT_HEAD)
        draw.text((rx + 18, y + 30), sub, fill=INK_MUTED, font=FONT_BODY_B)
        draw.line([rx + 18, y + 48, rx + rw - 18, y + 48], fill=INK_MUTED, width=1)
        by = y + 56
        for b in bullets:
            draw.text((rx + 18, by), b, fill=INK, font=FONT_BODY)
            by += 18
        y += step_h + 15
        
    draw.text((rx + 20, 672), 'Neuroscience Grounding: Plasticity consolidates idle episodes into procedural motor reflexes.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/procedural_learning_evolution.jpg', quality=95)
    print('Plate XXIX saved to assets/procedural_learning_evolution.jpg')

# =============================================================================
# PLATE XXX: PROCEDURAL LEARNING LOOP
# =============================================================================
def build_plate_xxx():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/clean_loop.jpg', (55, 190, 430, 470))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXX: ToMi PROCEDURAL CYBERNETIC LEARNING LOOP',
                'CLOSED-LOOP CYCLICAL REFINEMENT: TRACE -> SYNTHESIS -> AUDIT -> INVOCATION -> DRIFT PRUNING')
    
    draw.rectangle([55, 115, 485, 175], outline=INK, width=2)
    draw.rectangle([58, 118, 482, 172], outline=INK_MUTED, width=1)
    draw.text((70, 123), 'CELESTIAL CYBERNETIC FEEDBACK RING', fill=INK, font=FONT_HEAD)
    draw.text((70, 143), 'Continuously calibrates skills against empirical reality drift', fill=INK_MUTED, font=FONT_BODY)
    draw.text((70, 158), 'Closed-loop cybernetic governance and drift pruning engine', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Celestial Armillary Sphere, Telemetry Dial Ring & Feedback Compass', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    
    # Cycle Box 1: Continuous Ingestion & Synthesis
    draw.rectangle([rx, 115, rx + rw, 270], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + rw - 3, 267], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 124), 'I. TELEMETRY INGESTION & SKILL COMPILATION', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 146, rx + rw - 20, 146], fill=INK_MUTED, width=1)
    c1_lines = [
        ('1. Action Execution Traces: Real tool runs stream to experience.db (operations table)', FONT_BODY),
        ('2. Surprise Detection: Traces with non-zero exit or high state diffs marked for review', FONT_BODY),
        ('3. Offline Synthesis: Hippocampal consolidation cron (04:00 daily) synthesizes skills', FONT_BODY),
        ('4. Canonical SKILL.md Output: Emits executable scripts, recipes, and YAML schemas', FONT_BODY_B)
    ]
    cy = 152
    for txt, fnt in c1_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 18
        
    # Cycle Box 2: Runtime Execution & Monitoring
    draw.rectangle([rx, 310, rx + rw, 465], outline=INK, width=2)
    draw.rectangle([rx + 3, 313, rx + rw - 3, 462], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 318), 'II. RUNTIME INVOCATION & TELEMETRY MONITORING', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 340, rx + rw - 20, 340], fill=INK_MUTED, width=1)
    c2_lines = [
        ('1. Zero-Deliberation Reflex: Installed skills trigger directly via keyword/task matching', FONT_BODY),
        ('2. Execution Telemetry: Logs runtime duration, token consumption, and error states', FONT_BODY),
        ('3. Reality Diff Verification: Asserts that output changes conform to skill contract', FONT_BODY),
        ('4. Competence Ledger Update: Adjusts Beta(alpha, beta) success ratios dynamically', FONT_BODY_B)
    ]
    cy = 346
    for txt, fnt in c2_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 18
        
    # Cycle Box 3: Automated Drift Pruning & Retirement
    draw.rectangle([rx, 505, rx + rw, 655], outline=INK, width=2)
    draw.rectangle([rx + 3, 508, rx + rw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 513), 'III. AUTOMATED DRIFT PRUNING & RETIREMENT', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 535, rx + rw - 20, 535], fill=INK_MUTED, width=1)
    c3_lines = [
        ('1. Drift Detection: Identifies skills whose success rate falls below threshold (C < 0.70)', FONT_BODY),
        ('2. Interface Breakage Quarantine: Moving APIs or broken dependencies flag skill quarantine', FONT_BODY),
        ('3. Automated Refactoring: Re-spawns Planner to update outdated CLI flags or schemas', FONT_BODY),
        ('4. Deprecation Archive: Decays unused or permanently superseded skills cleanly', FONT_BODY_B)
    ]
    cy = 541
    for txt, fnt in c3_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 18
        
    draw_flow_arrow(draw, rx + rw/2, 270, rx + rw/2, 310, 'Deploy to Runtime', 'right')
    draw_flow_arrow(draw, rx + rw/2, 465, rx + rw/2, 505, 'Performance Audit', 'right')
    
    draw.text((rx + 20, 672), 'Cybernetic Governance: The procedural loop prunes stale habits and compiles reliable operational reflexes.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/procedural_learning_loop.jpg', quality=95)
    print('Plate XXX saved to assets/procedural_learning_loop.jpg')

# =============================================================================
# PLATE XXXI: COMMAND DECK DASHBOARD
# =============================================================================
def build_plate_xxxi():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/clean_console.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXXI: ToMi EXECUTIVE COMMAND DECK ARCHITECTURE',
                'OPERATIONS HUD (:8088), MULTI-CHANNEL DISPATCH & ADAPTER INTEGRATION')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'MASTER BRIDGE OPERATIONS CONSOLE', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Central cathode-ray tube, telemetry dials, and telegraph keys', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Executive control interface for multi-tier memory and services', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Executive Console, Waveform Oscilloscope & Archival Card Drawers', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    
    # Section 1: Command Deck Core Modules
    draw.rectangle([rx, 115, rx + rw, 305], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + rw - 3, 302], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 124), 'EXECUTIVE OPERATIONS WEB DASHBOARD (PORT 8088)', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 146, rx + rw - 20, 146], fill=INK_MUTED, width=1)
    modules = [
        ('• Executive Operations HUD:', 'Real-time telemetry of memory tiers, Docker containers, token streams, profiles'),
        ('• Multi-View Calendar:', 'Unified Day / Week / Month view aggregating tasks, subscriptions, and .ics feeds'),
        ('• Personal Organizer Pipeline:', 'Live interactive CRUD task cards with priority sorting and progress rings'),
        ('• Multi-Channel Reminders:', 'Dispatches alerts to Telegram, Discord, Slack, Email, SMS, or Desktop'),
        ('• Second Brain Reader:', 'Instant search and document viewer across Active Wiki and Oracle Vault pages'),
        ('• In-Deck Slide-Over Copilot:', 'Native interactive chat drawer connecting directly to Main Hermes Agent')
    ]
    cy = 153
    for m_head, m_desc in modules:
        draw.text((rx + 20, cy), m_head, fill=INK, font=FONT_BODY_B)
        draw.text((rx + 235, cy), m_desc, fill=INK_MID, font=FONT_BODY)
        cy += 24
        
    # Section 2: Companion Adapters & Ports
    draw.rectangle([rx, 325, rx + rw, 505], outline=INK, width=2)
    draw.rectangle([rx + 3, 328, rx + rw - 3, 502], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 334), 'UPSTREAM COMPANIONS & SERVICE PORT BINDINGS', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 356, rx + rw - 20, 356], fill=INK_MUTED, width=1)
    ports = [
        ('Port 8088:', 'Command Deck UI & OpenAPI REST Server (http://<host-lan-ip>:8088)'),
        ('Port 8001:', 'Personal Organizer State Engine (deterministic SQLite CRUD & reminders)'),
        ('Port 8080:', 'Local SearXNG Metasearch Engine (exclusive to Researcher Profile)'),
        ('Port 8000:', 'Honcho Autobiographical User Modeling & Psychological State API'),
        ('Port 8790:', 'ai-visualizer: Real-time procedural avatar stage (thinking / speaking / idle)'),
        ('Port 8794:', 'barehands: 3D webcam hand-tracking spatial holographic interface')
    ]
    cy = 363
    for p_port, p_desc in ports:
        draw.text((rx + 20, cy), p_port, fill=INK, font=FONT_BODY_B)
        draw.text((rx + 115, cy), p_desc, fill=INK_MID, font=FONT_BODY)
        cy += 22
        
    # Section 3: Architecture Separation
    draw.rectangle([rx, 525, rx + rw, 655], outline=INK, width=2)
    draw.rectangle([rx + 3, 528, rx + rw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 534), 'NON-INVASIVE COMPANION ADAPTER ARCHITECTURE', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 556, rx + rw - 20, 556], fill=INK_MUTED, width=1)
    a_lines = [
        ('• Zero Code Contamination: Companions connect via plugins/adapters/ without altering core', FONT_BODY),
        ('• Visualizer Synchronizer: hooks/hermes-visualizer-sync pushes live agent state transitions', FONT_BODY),
        ('• Holographic Board: skills/barehands/scripts/board.py renders 3D floating glass cards', FONT_BODY)
    ]
    cy = 563
    for txt, fnt in a_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 20
        
    draw.text((rx + 20, 672), 'Network Architecture: Published on 0.0.0.0:8088 for accessible local LAN operation.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/command_deck_dashboard.jpg', quality=95)
    canvas.save('docs/assets/hermes_brain_dashboard.jpg', quality=95)
    print('Plate XXXI saved to assets/command_deck_dashboard.jpg and docs/assets/hermes_brain_dashboard.jpg')

# =============================================================================
# PLATE XXXII: VM DEPLOYMENT TOPOLOGY
# =============================================================================
def build_plate_xxxii():
    canvas = get_base_canvas()
    canvas = paste_engraving(canvas, 'scratch/crops/pure_strata.jpg', (60, 200, 440, 460))
    draw = ImageDraw.Draw(canvas)
    draw_header(draw, 'PLATE XXXII: ToMi SELF-HOSTED VM DEPLOYMENT TOPOLOGY',
                'ISOLATED HYPERVISOR ARCHITECTURE, INTER-SERVICE BUS & DURABLE BEDROCK VAULT')
    
    draw.rectangle([60, 115, 480, 175], outline=INK, width=2)
    draw.rectangle([63, 118, 477, 172], outline=INK_MUTED, width=1)
    draw.text((75, 123), 'SUBTERRANEAN BEDROCK POWERHOUSE', fill=INK, font=FONT_HEAD)
    draw.text((75, 143), 'Durable geological strata vault supporting isolated virtual chambers', fill=INK_MUTED, font=FONT_BODY)
    draw.text((75, 158), 'Persistent granite bedrock survives disposable container failure', fill=INK, font=FONT_SMALL)
    
    draw.text((80, 668), 'Geological Bedrock Strata, Granite Foundation & Surveying Calipers', fill=INK_MUTED, font=FONT_SMALL_B)
    
    rx = 540
    rw = 770
    
    # Hypervisor Host Box
    draw.rectangle([rx, 115, rx + rw, 225], outline=INK, width=2)
    draw.rectangle([rx + 3, 118, rx + rw - 3, 222], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 124), 'PROXMOX VE / KVM BARE-METAL HYPERVISOR HOST', fill=INK, font=FONT_HEAD)
    draw.line([rx + 20, 146, rx + rw - 20, 146], fill=INK_MUTED, width=1)
    h_lines = [
        ('• Host OS: Debian 12 / Proxmox VE with PCIe passthrough (NVIDIA RTX GPU compute)', FONT_BODY),
        ('• Storage Foundation: ZFS mirror zpool hosting durable raw virtual disks and backups', FONT_BODY),
        ('• Virtual Network: Isolated internal bridge (vmbr1, 10.10.0.0/24) with strict egress rules', FONT_BODY)
    ]
    cy = 153
    for txt, fnt in h_lines:
        draw.text((rx + 20, cy), txt, fill=INK, font=fnt)
        cy += 20
        
    # The 4 Isolated VMs (Grid 2x2)
    vw = (rw - 20) // 2
    vh = 175
    
    # VM 1: Core Hermes Runtime
    draw.rectangle([rx, 240, rx + vw, 240 + vh], outline=INK, width=2)
    draw.rectangle([rx + 3, 243, rx + vw - 3, 240 + vh - 3], outline=INK_MUTED, width=1)
    draw.text((rx + 15, 249), 'VM 1: CORE HERMES RUNTIME', fill=INK, font=FONT_HEAD)
    draw.text((rx + 15, 269), 'Main Agent, Profiles & Hooks', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + 15, 284, rx + vw - 15, 284], fill=INK_MUTED, width=1)
    vm1_text = [
        '• Main Hermes executive profile',
        '• Researcher, Planner, Oracle profiles',
        '• Striatal Action Gate & hook system',
        '• Append-only SessionDB (~/.hermes/)'
    ]
    y = 293
    for t in vm1_text:
        draw.text((rx + 15, y), t, fill=INK, font=FONT_BODY)
        y += 20
        
    # VM 2: Cognitive Stores
    draw.rectangle([rx + vw + 20, 240, rx + rw, 240 + vh], outline=INK, width=2)
    draw.rectangle([rx + vw + 23, 243, rx + rw - 3, 240 + vh - 3], outline=INK_MUTED, width=1)
    draw.text((rx + vw + 35, 249), 'VM 2: COGNITIVE STORES', fill=INK, font=FONT_HEAD)
    draw.text((rx + vw + 35, 269), 'Postgres 18.6 + pgvector (:5433)', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + vw + 35, 284, rx + rw - 15, 284], fill=INK_MUTED, width=1)
    vm2_text = [
        '• PostgreSQL 18.6 with pgvector HNSW',
        '• ParadeDB pg_search BM25 lexical index',
        '• Qwen3 2560-dim dense vector embeddings',
        '• Reciprocal Rank Fusion (RRF, k=60)'
    ]
    y = 293
    for t in vm2_text:
        draw.text((rx + vw + 35, y), t, fill=INK, font=FONT_BODY)
        y += 20
        
    # VM 3: Web Services
    draw.rectangle([rx, 430, rx + vw, 430 + vh], outline=INK, width=2)
    draw.rectangle([rx + 3, 433, rx + vw - 3, 430 + vh - 3], outline=INK_MUTED, width=1)
    draw.text((rx + 15, 439), 'VM 3: WEB & SERVICES', fill=INK, font=FONT_HEAD)
    draw.text((rx + 15, 459), 'Command Deck (:8088) & Organizer', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + 15, 474, rx + vw - 15, 474], fill=INK_MUTED, width=1)
    vm3_text = [
        '• Command Deck UI & API (:8088)',
        '• Personal Organizer REST API (:8001)',
        '• SearXNG local metasearch (:8080)',
        '• Honcho user model API (:8000)'
    ]
    y = 483
    for t in vm3_text:
        draw.text((rx + 15, y), t, fill=INK, font=FONT_BODY)
        y += 20
        
    # VM 4: Companions
    draw.rectangle([rx + vw + 20, 430, rx + rw, 430 + vh], outline=INK, width=2)
    draw.rectangle([rx + vw + 23, 433, rx + rw - 3, 430 + vh - 3], outline=INK_MUTED, width=1)
    draw.text((rx + vw + 35, 440), 'VM 4: COMPANION STAGES', fill=INK, font=FONT_HEAD)
    draw.text((rx + vw + 35, 460), 'Avatar (:8790) & Barehands (:8794)', fill=INK_MUTED, font=FONT_SMALL_B)
    draw.line([rx + vw + 35, 475, rx + rw - 15, 475], fill=INK_MUTED, width=1)
    vm4_text = [
        '• ai-visualizer procedural avatar (:8790)',
        '• barehands 3D webcam tracking (:8794)',
        '• Isolated non-privileged container sandbox',
        '• Driven non-invasively via hook adapters'
    ]
    y = 483
    for t in vm4_text:
        draw.text((rx + vw + 35, y), t, fill=INK, font=FONT_BODY)
        y += 20
        
    # Bottom Bedrock Vault Bar
    draw.rectangle([rx, 615, rx + rw, 655], outline=INK, width=2)
    draw.rectangle([rx + 3, 618, rx + rw - 3, 652], outline=INK_MUTED, width=1)
    draw.text((rx + 20, 626), 'DURABLE BEDROCK VAULT: organizer.db | experience.db | ~/.hermes/active-wiki/ | ~/.hermes/oracle/', fill=INK, font=FONT_BODY_B)
    
    draw.text((rx + 20, 672), 'Self-Hosting Invariant: Durable bedrock files survive total VM container reconstruction without data loss.', fill=INK_MUTED, font=FONT_SMALL)
    canvas.save('assets/vm_deployment_topology.jpg', quality=95)
    print('Plate XXXII saved to assets/vm_deployment_topology.jpg')

def main():
    os.makedirs('assets', exist_ok=True)
    os.makedirs('docs/assets', exist_ok=True)
    print('Building Plates XXII through XXXII in authentic vintage engraving aesthetic...')
    build_plate_xxii()
    build_plate_xxiii()
    build_plate_xxiv()
    build_plate_xxv()
    build_plate_xxvi()
    build_plate_xxvii()
    build_plate_xxviii()
    build_plate_xxix()
    build_plate_xxx()
    build_plate_xxxi()
    build_plate_xxxii()
    print('All 11 plates built successfully!')

if __name__ == '__main__':
    main()
