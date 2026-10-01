#!/usr/bin/env python3
"""
scripts/generate_vintage_plates.py

Master Vintage Cybernetics Folio Generator (Plates IX through XXXII).
Renders 24 high-fidelity, large-type, graphically rich engineering plates
matching the Norbert Wiener / Ross Ashby mid-century manual aesthetic on
warm, authentic organic parchment.
"""

import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np

W, H = 1376, 768

# Refined Ink Palette
INK_DARK = (24, 20, 16)       # Primary deep walnut copperplate ink
INK_MID = (55, 42, 32)        # Secondary body ink
INK_MUTED = (95, 78, 62)      # Explanatory annotations
INK_RUST = (145, 42, 28)      # Highlight / Warning / Active needle
INK_GREEN = (38, 92, 45)      # Verification / Go / Low risk
INK_BLUE = (35, 70, 115)      # Epistemic / Invariant accent

# Large, highly legible fonts
FONT_TITLE_LG = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 31)
FONT_TITLE_SM = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 24)
FONT_SUBTITLE = ImageFont.truetype('C:\\Windows\\Fonts\\georgia.ttf', 15)
FONT_HERO = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 22)
FONT_SECTION = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 19)
FONT_BODY = ImageFont.truetype('C:\\Windows\\Fonts\\georgia.ttf', 16)
FONT_BODY_B = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 16)
FONT_SMALL = ImageFont.truetype('C:\\Windows\\Fonts\\georgia.ttf', 13)
FONT_SMALL_B = ImageFont.truetype('C:\\Windows\\Fonts\\georgiab.ttf', 13)
FONT_CODE = ImageFont.truetype('C:\\Windows\\Fonts\\consolab.ttf', 14)


def get_parchment_canvas(seed=42):
    np.random.seed(seed)
    y = np.linspace(0, 1, H)[:, None]
    x = np.linspace(0, 1, W)[None, :]
    r = np.sqrt(((x - 0.5) * 1.1) ** 2 + ((y - 0.5) * 1.3) ** 2)
    m = np.sin(x * 5.2 + y * 3.7) * 7.0 + np.cos(x * 9.1 - y * 6.3) * 5.0 + np.sin(x * 17.0 + y * 13.0) * 3.5
    edge_decay = (r ** 2.2) * 52.0
    base_r = 232.0 - edge_decay + m
    base_g = 208.0 - edge_decay * 1.15 + m * 0.95
    base_b = 168.0 - edge_decay * 1.35 + m * 0.8
    total_noise = np.random.normal(0, 3.0, (H, W)) + np.random.uniform(-2.0, 2.0, (H, W))
    fiber_h = np.random.normal(0, 1.0, (H, 1)) * np.ones((1, W))
    fiber_v = np.random.normal(0, 1.0, (1, W)) * np.ones((H, 1))
    total_noise += fiber_h + fiber_v
    img_r = np.clip(base_r + total_noise, 0, 255).astype(np.uint8)
    img_g = np.clip(base_g + total_noise, 0, 255).astype(np.uint8)
    img_b = np.clip(base_b + total_noise * 0.85, 0, 255).astype(np.uint8)
    return Image.fromarray(np.stack([img_r, img_g, img_b], axis=-1))


def draw_master_frame(draw, title, subtitle):
    m = 26
    draw.rectangle([m, m, W - m, H - m], outline=INK_DARK, width=2)
    draw.rectangle([m + 4, m + 4, W - m - 4, H - m - 4], outline=INK_DARK, width=1)
    for cx, cy in [(m, m), (W - m, m), (m, H - m), (W - m, H - m)]:
        draw.arc([cx - 8, cy - 8, cx + 8, cy + 8], 0, 360, fill=INK_DARK, width=2)
        draw.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=INK_DARK)
        
    font_t = FONT_TITLE_LG
    if draw.textlength(title, font=font_t) > W - 140:
        font_t = FONT_TITLE_SM
    tw = draw.textlength(title, font=font_t)
    sw = draw.textlength(subtitle, font=FONT_SUBTITLE)
    draw.text(((W - tw) / 2, 38), title, fill=INK_DARK, font=font_t)
    draw.text(((W - sw) / 2, 75), subtitle, fill=INK_MID, font=FONT_SUBTITLE)
    draw.line([W/2 - 280, 98, W/2 + 280, 98], fill=INK_MID, width=1)


def draw_card(draw, x, y, w, h, title=None, subtitle=None, bullets=None, badge=None, double_border=True, border_color=INK_DARK):
    draw.rectangle([x, y, x + w, y + h], outline=border_color, width=2)
    if double_border:
        draw.rectangle([x + 3, y + 3, x + w - 3, y + h - 3], outline=INK_MID, width=1)
        
    if badge:
        bw = draw.textlength(badge, font=FONT_SMALL_B) + 14
        bx = x + w - bw - 12
        by = y + 10
        draw.rectangle([bx, by, bx + bw, by + 20], outline=border_color, width=1)
        draw.text((bx + 7, by + 3), badge, fill=border_color, font=FONT_SMALL_B)
        
    cur_y = y + 16
    if title:
        draw.text((x + 16, cur_y), title, fill=border_color, font=FONT_SECTION)
        cur_y += 30
    if subtitle:
        draw.text((x + 16, cur_y), subtitle, fill=INK_RUST, font=FONT_BODY_B)
        cur_y += 26
    if bullets:
        for b in bullets:
            if isinstance(b, tuple):
                text, font, color = b
                draw.text((x + 16, cur_y), text, fill=color, font=font)
            else:
                draw.text((x + 16, cur_y), b, fill=INK_MID, font=FONT_BODY)
            cur_y += 24


def draw_dial(draw, cx, cy, radius, label, value_label, needle_deg, color=INK_RUST):
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], outline=INK_DARK, width=2)
    draw.ellipse([cx - radius + 3, cy - radius + 3, cx + radius - 3, cy + radius - 3], outline=INK_MID, width=1)
    for deg in range(-120, 121, 20):
        rad = np.radians(deg - 90)
        x1 = cx + (radius - 8) * np.cos(rad)
        y1 = cy + (radius - 8) * np.sin(rad)
        x2 = cx + (radius - 2) * np.cos(rad)
        y2 = cy + (radius - 2) * np.sin(rad)
        draw.line([x1, y1, x2, y2], fill=INK_DARK, width=1 if deg % 40 != 0 else 2)
    n_rad = np.radians(needle_deg - 90)
    nx = cx + (radius - 12) * np.cos(n_rad)
    ny = cy + (radius - 12) * np.sin(n_rad)
    draw.line([cx, cy, nx, ny], fill=color, width=2)
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=INK_DARK)
    tw = draw.textlength(label, font=FONT_SMALL)
    draw.text((cx - tw / 2, cy + radius + 8), label, fill=INK_DARK, font=FONT_SMALL)
    vw = draw.textlength(value_label, font=FONT_BODY_B)
    draw.text((cx - vw / 2, cy + radius + 24), value_label, fill=color, font=FONT_BODY_B)


def draw_arrow_h(draw, x1, x2, y, label=None, color=INK_DARK):
    draw.line([x1, y, x2, y], fill=color, width=2)
    if x2 > x1:
        draw.polygon([(x2 - 10, y - 6), (x2 - 10, y + 6), (x2, y)], fill=color)
    else:
        draw.polygon([(x2 + 10, y - 6), (x2 + 10, y + 6), (x2, y)], fill=color)
    if label:
        lw = draw.textlength(label, font=FONT_SMALL_B)
        draw.text(((x1 + x2 - lw) / 2, y - 18), label, fill=color, font=FONT_SMALL_B)


def draw_arrow_v(draw, x, y1, y2, label=None, color=INK_DARK):
    draw.line([x, y1, x, y2], fill=color, width=2)
    if y2 > y1:
        draw.polygon([(x - 6, y2 - 10), (x + 6, y2 - 10), (x, y2)], fill=color)
    else:
        draw.polygon([(x - 6, y2 + 10), (x + 6, y2 + 10), (x, y2)], fill=color)
    if label:
        draw.text((x + 10, (y1 + y2) / 2 - 9), label, fill=color, font=FONT_SMALL_B)


# -------------------------------------------------------------
# PLATES DEFINITIONS
# -------------------------------------------------------------
def gen_retrieval_cascade():
    img = get_parchment_canvas(42)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE IX: 6-LEVEL HIERARCHICAL RETRIEVAL CASCADE',
                      'TIERED LATENCY, CAPACITY & ATTENTION ENTROPY FILTERING ARCHITECTURE')
    
    levels = [
        ('L0: WORKING CONTEXT BUFFER', 'dlPFC attention slots (Cowan limit 4 ± 1 chunks), active dialog frame', '0 ms', '100% (Instant)'),
        ('L1: DETERMINISTIC FAST-PATH', 'Exact title & [[wikilink]] match from Active Markdown Wiki', '< 5 ms', '98% Precision'),
        ('L2: PARADEDB BM25 LEXICAL SEARCH', 'PostgreSQL pg_search with saturation & length normalization', '12 ms', '1,106 Hits/s'),
        ('L3: PGVECTOR HNSW DENSE EMBEDDINGS', 'Qwen3 2560-dim vectors + Reciprocal Rank Fusion (RRF, k=60)', '45 ms', 'Semantic Rerank'),
        ('L4: GRAPHIFY KNOWLEDGE GRAPH', 'Personalized PageRank diffusion over multi-hop concept relations', '120 ms', 'Multi-Hop Walk'),
        ('L5: CANONICAL COLD ORACLE VAULT', 'Historical research vault lookup via isolated Librarian sub-agent', '850 ms', 'Lossless Deep'),
    ]
    
    start_y = 125
    step_h = 88
    box_w = 830
    box_x = 70
    
    for i, (title, desc, lat, eff) in enumerate(levels):
        y = start_y + i * step_h
        draw.rectangle([box_x, y, box_x + box_w, y + 74], outline=INK_DARK, width=2)
        draw.rectangle([box_x + 3, y + 3, box_x + box_w - 3, y + 71], outline=INK_MID, width=1)
        
        badge_cx = box_x + 36
        badge_cy = y + 37
        draw.ellipse([badge_cx - 24, badge_cy - 24, badge_cx + 24, badge_cy + 24], outline=INK_DARK, width=2)
        draw.ellipse([badge_cx - 21, badge_cy - 21, badge_cx + 21, badge_cy + 21], outline=INK_MID, width=1)
        draw.text((badge_cx - 13, badge_cy - 11), f"L{i}", fill=INK_DARK, font=FONT_SECTION)
        
        draw.text((box_x + 72, y + 12), title, fill=INK_DARK, font=FONT_SECTION)
        draw.text((box_x + 72, y + 42), desc, fill=INK_MID, font=FONT_BODY)
        
        draw.line([box_x + box_w - 180, y, box_x + box_w - 180, y + 74], fill=INK_MID, width=1)
        draw.text((box_x + box_w - 165, y + 14), f"Latency: {lat}", fill=INK_DARK, font=FONT_BODY_B)
        draw.text((box_x + box_w - 165, y + 42), f"Throughput: {eff}", fill=INK_MUTED, font=FONT_SMALL)
        
        if i < 5:
            arrow_y = y + 74
            cx = box_x + box_w / 2
            draw.line([cx, arrow_y, cx, arrow_y + 14], fill=INK_DARK, width=2)
            draw.polygon([(cx - 6, arrow_y + 8), (cx + 6, arrow_y + 8), (cx, arrow_y + 14)], fill=INK_DARK)
            
            gate_x = box_x + box_w
            gate_y = y + 37
            draw.line([gate_x, gate_y, gate_x + 35, gate_y], fill=INK_DARK, width=1)
            draw.line([gate_x + 35, gate_y, 970, 310], fill=INK_MID, width=1)
            
    rx = 940
    ry = 125
    rw = 365
    rh = 598
    draw.rectangle([rx, ry, rx + rw, ry + rh], outline=INK_DARK, width=2)
    draw.rectangle([rx + 4, ry + 4, rx + rw - 4, ry + rh - 4], outline=INK_MID, width=1)
    
    gh_w = draw.textlength("EARLY EXIT GATING", font=FONT_SECTION)
    draw.text((rx + (rw - gh_w) / 2, ry + 18), "EARLY EXIT GATING", fill=INK_DARK, font=FONT_SECTION)
    draw.line([rx + 25, ry + 46, rx + rw - 25, ry + 46], fill=INK_MID, width=1)
    
    draw_dial(draw, rx + rw / 2, ry + 130, 58, "CONFIDENCE METER", "c >= 0.88", 45)
    
    f_y = ry + 245
    draw.rectangle([rx + 20, f_y, rx + rw - 20, f_y + 90], outline=INK_DARK, width=1)
    draw.text((rx + 32, f_y + 12), "TERMINATION CONDITION:", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((rx + 32, f_y + 36), "IF  Confidence c >= θ_retrieval", fill=INK_RUST, font=FONT_BODY_B)
    draw.text((rx + 32, f_y + 60), "THEN  Halt Cascade & Return", fill=INK_DARK, font=FONT_BODY)
    
    n_y = ry + 360
    draw.text((rx + 25, n_y), "CASCADE INVARIANTS:", fill=INK_DARK, font=FONT_BODY_B)
    invariants = [
        "• 82% queries resolve at L0-L2",
        "• L3 semantic vectors called only",
        "  when lexical score < θ",
        "• Graph diffusion reserved for",
        "  multi-hop relational queries",
        "• dlPFC context protected from",
        "  needle-in-haystack pollution",
    ]
    cur_ny = n_y + 28
    for inv in invariants:
        draw.text((rx + 25, cur_ny), inv, fill=INK_MID, font=FONT_BODY)
        cur_ny += 24
        
    img.save('assets/retrieval_cascade_hierarchy.jpg', quality=95)


def gen_oracle_pipeline():
    img = get_parchment_canvas(43)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE X: ORACLE HISTORICAL LIBRARIAN RETRIEVAL PIPELINE',
                      'ISOLATED SUB-AGENT CONTEXT DECOMPRESSION & EVIDENCE PRESERVATION')
    
    draw_card(draw, 70, 130, 360, 230, 'MAIN HERMES AGENT', 'EXECUTIVE CONTEXT', [
        ('• User interaction & tool execution', FONT_BODY, INK_MID),
        ('• Epistemic gate & cognitive router', FONT_BODY, INK_MID),
        ('• Rule: NEVER searches vault directly', FONT_BODY_B, INK_RUST),
        ('• Protected working context frame', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 70, 440, 360, 250, 'ORACLE LIBRARIAN', 'ISOLATED SUB-AGENT PROFILE', [
        ('• Dedicated long-term research specialist', FONT_BODY, INK_MID),
        ('• Scans 14,000+ historical deliverables', FONT_BODY, INK_MID),
        ('• Deep full-text BM25 & dense vector search', FONT_BODY, INK_MID),
        ('• Evaluates bi-temporal provenance tags', FONT_BODY, INK_MID),
        ('• Context insulation: zero clutter leak', FONT_BODY_B, INK_BLUE)
    ])
    
    draw_arrow_v(draw, 250, 360, 440, "1. Delegate Query")
    
    draw_card(draw, 510, 130, 440, 260, 'CANONICAL ORACLE VAULT', 'COLD CURATED ARCHIVE (~/.hermes/oracle/brain/)', [
        ('• Curated Markdown Pages (Historical Synthesis)', FONT_BODY_B, INK_DARK),
        ('• Provenance frontmatter: date, author, parent', FONT_BODY, INK_MID),
        ('• Bi-temporal validity timestamps', FONT_BODY, INK_MID),
        ('• Lossless decanting destination', FONT_BODY, INK_MID),
        ('• Indexed in PostgreSQL 18.6 pg_search BM25', FONT_BODY_B, INK_BLUE)
    ])
    
    draw_card(draw, 510, 430, 440, 260, 'RAW EVIDENCE VAULT', 'IMMUTABLE SOURCE LOGS (~/.hermes/oracle/raw/)', [
        ('• Unmodified raw tool transcripts & diffs', FONT_BODY_B, INK_DARK),
        ('• Benchmark test outputs & validation dumps', FONT_BODY, INK_MID),
        ('• Read-only audit trail for disputation', FONT_BODY, INK_MID),
        ('• Never mutated or destructively summarized', FONT_BODY_B, INK_RUST),
        ('• Provenance foundation for all synthesis', FONT_BODY, INK_MID)
    ])
    
    draw.line([(430, 565), (510, 565)], fill=INK_DARK, width=2)
    draw.polygon([(500, 559), (500, 571), (510, 565)], fill=INK_DARK)
    draw.text((440, 545), "2. Scan Raw", fill=INK_DARK, font=FONT_SMALL_B)
    
    draw.line([(430, 500), (470, 500), (470, 260), (510, 260)], fill=INK_DARK, width=2)
    draw.polygon([(500, 254), (500, 266), (510, 260)], fill=INK_DARK)
    draw.text((438, 480), "2. Query", fill=INK_DARK, font=FONT_SMALL_B)
    
    draw_card(draw, 1020, 240, 290, 340, 'SYNTHESIS OUT', 'HIGH-DENSITY COMPRESSION', [
        ('Compression Funnel:', FONT_BODY_B, INK_DARK),
        ('  100K+ raw corpus tokens', FONT_CODE, INK_MUTED),
        ('             │ (Filter & Rank)', FONT_CODE, INK_MID),
        ('             ▼', FONT_CODE, INK_MID),
        ('  500-token precise delta', FONT_BODY_B, INK_GREEN),
        ('', FONT_BODY, INK_MID),
        ('• Clean answer injection', FONT_BODY, INK_MID),
        ('• Full provenance pointers', FONT_BODY, INK_MID),
        ('• Zero context window waste', FONT_BODY_B, INK_DARK)
    ])
    
    draw.line([(950, 260), (985, 260), (985, 410), (1020, 410)], fill=INK_DARK, width=2)
    draw.line([(950, 560), (985, 560), (985, 410), (1020, 410)], fill=INK_DARK, width=2)
    draw.polygon([(1010, 404), (1010, 416), (1020, 410)], fill=INK_DARK)
    draw.text((955, 385), "3. Synthesis", fill=INK_DARK, font=FONT_SMALL_B)
    
    ret_text = "4. Clean Synthesis Delta Loaded into dlPFC Active Context"
    tw = draw.textlength(ret_text, font=FONT_BODY_B)
    tx = (W - tw) / 2
    draw.line([(1165, 240), (1165, 115), (tx + tw + 12, 115)], fill=INK_RUST, width=2)
    draw.line([(tx - 12, 115), (250, 115), (250, 130)], fill=INK_RUST, width=2)
    draw.polygon([(244, 120), (256, 120), (250, 130)], fill=INK_RUST)
    draw.text((tx, 105), ret_text, fill=INK_RUST, font=FONT_BODY_B)
    
    img.save('assets/oracle_retrieval_pipeline.jpg', quality=95)


def gen_additive_synthesis():
    img = get_parchment_canvas(44)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XI: ADDITIVE MULTI-RESOLUTION SYNTHESIS PRINCIPLE',
                      'NON-DESTRUCTIVE EPISODIC ACCUMULATION VERSUS LOSSY COMPRESSION')
    
    draw_card(draw, 70, 130, 430, 570, 'DESTRUCTIVE COMPRESSION', 'FLAWED CONVENTIONAL ARCHITECTURE', [
        ('Naive Compression Pipeline:', FONT_BODY_B, INK_DARK),
        ('  [Raw Episode: 100K Tokens]', FONT_CODE, INK_MID),
        ('               │', FONT_CODE, INK_MID),
        ('               ▼  (Lossy Summarizer)', FONT_CODE, INK_RUST),
        ('  [Lossy Summary: 2K Tokens]', FONT_CODE, INK_MID),
        ('               │', FONT_CODE, INK_MID),
        ('               ▼  (Discards Original)', FONT_CODE, INK_RUST),
        ('  [Evidence Permanently Erased]', FONT_CODE, INK_RUST),
        ('', FONT_BODY, INK_MID),
        ('Empirically Measured Failure Modes:', FONT_BODY_B, INK_DARK),
        ('• Numbers, nuance, and execution traces vanish', FONT_BODY, INK_MID),
        ('• Hallucinations compound across turns', FONT_BODY, INK_MID),
        ('• Verification becomes mathematically impossible', FONT_BODY, INK_MID),
        ('• AUROC for contradiction drops to chance (0.59)', FONT_BODY_B, INK_RUST)
    ], badge='REJECTED', border_color=INK_RUST)
    
    draw.rectangle([100, 600, 470, 665], outline=INK_RUST, width=2)
    draw.text((120, 615), "ARCHITECTURAL DEFECT:", fill=INK_RUST, font=FONT_BODY_B)
    draw.text((120, 638), "Destructive loss cannot be undone.", fill=INK_DARK, font=FONT_BODY)
    
    draw_card(draw, 540, 130, 765, 570, 'ToMi ADDITIVE RESOLUTION STRATA', 'THREE-LAYER PRESERVATIONAL COGNITIVE HIERARCHY', badge='APPROVED')
    
    draw_card(draw, 570, 195, 705, 115, 'LAYER 2: COMPACT EXECUTIVE ABSTRACT', '1-Line Epistemic Fact in dlPFC Active Working Memory', [
        ('• Ultra-dense summary token injected into conversation context', FONT_BODY, INK_MID),
        ('• Carries direct pointer: [[TopicName#Decisions]] & Bi-Temporal ID', FONT_BODY_B, INK_DARK)
    ])
    
    draw_arrow_v(draw, 920, 310, 350, "References Lower Layer", color=INK_BLUE)
    
    draw_card(draw, 570, 350, 705, 135, 'LAYER 1: HIGH-DENSITY STRUCTURED SYNTHESIS', 'Canonical Markdown Documentation in Active Wiki & Oracle Vault', [
        ('• Formatted technical markdown, architectural rationale, code diffs', FONT_BODY, INK_MID),
        ('• Defeater graph connections, AGM minimal-mutilation revision records', FONT_BODY, INK_MID),
        ('• Contains bidirectional wikilinks to source files and test runs', FONT_BODY_B, INK_BLUE)
    ])
    
    draw_arrow_v(draw, 920, 485, 525, "Grounds in Bedrock Proof", color=INK_GREEN)
    
    draw_card(draw, 570, 525, 705, 145, 'LAYER 0: PRESERVED RAW EVIDENCE (BEDROCK)', 'Lossless Immutable Filesystem Storage (~/.hermes/oracle/raw/)', [
        ('• Complete tool transcripts, shell stdout, test logs, raw benchmarks', FONT_BODY, INK_MID),
        ('• Immutable and append-only: Never truncated, mutated, or deleted', FONT_BODY_B, INK_RUST),
        ('• Ground truth bedrock: Enables retroactive auditor audit at any time', FONT_BODY, INK_MID)
    ])
    
    img.save('assets/additive_synthesis_principle.jpg', quality=95)


def gen_knowledge_lifecycle():
    img = get_parchment_canvas(45)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XII: KNOWLEDGE DECANTING & MEMORY LIFECYCLE PIPELINE',
                      'ORDERED TRANSITION FROM EPISODIC WORKING CONTEXT TO IMMUTABLE VAULT')
    
    stages = [
        ('STAGE 1: ACTIVE SESSION', 'Episodic Working Context', [
            '• Immediate user interaction',
            '• Raw tool stdout / stderr logs',
            '• Temporary working hypothesis',
            '• Cowan limit 4 ± 1 chunks',
            '• Scratchpad working notes',
            '• Ephemeral session memory',
            '',
            ('Target: RAM Working Frame', FONT_CODE, INK_DARK),
            ('Format: Ephemeral KV Buffers', FONT_CODE, INK_MID)
        ], None),
        ('STAGE 2: ACTIVE WIKI', 'Tier 2 Hot Semantic Store', [
            '• Fast markdown capture',
            '• Immediate project wiki notes',
            '• Cross-linked [[wikilinks]]',
            '• Bi-temporal version tag',
            '• Active project synthesis',
            '• Read/write working tier',
            '',
            ('Target: ~/.hermes/active-wiki/', FONT_CODE, INK_DARK),
            ('Format: Curated Markdown', FONT_CODE, INK_MID)
        ], None),
        ('STAGE 3: DECANTING GATE', 'Rigorous Consolidation Check', [
            '• Checksum verified on disk',
            '• PRAGMA integrity audit',
            '• Empirical proof (Exit 0)',
            '• Supersession links bound',
            '• Auditor quality review',
            '• Striatal gate clearance',
            '',
            ('Target: scripts/decant_guard.py', FONT_CODE, INK_DARK),
            ('Format: PRAGMA & Hash Check', FONT_CODE, INK_MID)
        ], None),
        ('STAGE 4: ORACLE VAULT', 'Tier 3 Immutable Archive', [
            '• Canonical research vault',
            '• PostgreSQL BM25 index',
            '• pgvector HNSW embeddings',
            '• Lossless raw evidence logs',
            '• Immutable historical record',
            '• Append-only cold archive',
            '',
            ('Target: ~/.hermes/oracle/brain/', FONT_CODE, INK_DARK),
            ('Format: Lossless Plaintext', FONT_CODE, INK_MID)
        ], None)
    ]
    
    card_w = 285
    start_x = 70
    gap = 25
    y = 150
    h = 420
    
    for i, (title, sub, bullets, badge) in enumerate(stages):
        x = start_x + i * (card_w + gap)
        draw_card(draw, x, y, card_w, h, title, sub, bullets, badge=badge)
        if i < 3:
            ax1 = x + card_w
            ax2 = ax1 + gap
            ay = y + h // 2
            draw_arrow_h(draw, ax1, ax2, ay)
            draw.text((ax1 + 2, ay - 20), "Pass", fill=INK_GREEN, font=FONT_SMALL_B)
            
    draw_card(draw, 70, 595, 1235, 105, 'ARCHITECTURAL INVARIANT: CONSOLIDATION OCCURS WITHOUT INFORMATION LOSS', None, [
        ('• Active knowledge is decanted to cold storage only when empirical criteria are satisfied.', FONT_BODY, INK_MID),
        ('• Nightly SWR sleep daemon compiles procedural rules while raw historical evidence remains permanently untouched.', FONT_BODY_B, INK_DARK)
    ])
    
    img.save('assets/knowledge_lifecycle_pipeline.jpg', quality=95)


def gen_knowledge_reactivation():
    img = get_parchment_canvas(46)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XIII: HISTORICAL KNOWLEDGE REACTIVATION FLOW',
                      'LOSSLESS ACTIVE-CONTEXT RECALL WITHOUT MUTATING IMMUTABLE ARCHIVES')
    
    draw_card(draw, 70, 140, 360, 240, 'ACTIVE QUERY / SUBGOAL', 'PREFRONTAL dlPFC REQUEST', [
        ('• Agent encounters knowledge gap', FONT_BODY, INK_MID),
        ('• Subgoal requires historical data', FONT_BODY, INK_MID),
        ('• Dispatches targeted request', FONT_BODY, INK_MID),
        ('• Strict context token budget', FONT_BODY_B, INK_RUST)
    ])
    
    draw_card(draw, 500, 140, 420, 240, 'ORACLE SEARCH ENGINES', 'HYBRID LEXICAL & DENSE INDEX', [
        ('• ParadeDB BM25: Keyword hits (1,106/s)', FONT_BODY_B, INK_DARK),
        ('• pgvector HNSW: Semantic cosine vector', FONT_BODY, INK_MID),
        ('• Reciprocal Rank Fusion: rrf_k = 60.0', FONT_BODY, INK_BLUE),
        ('• Retrieve-then-read: In source order', FONT_BODY, INK_MID)
    ])
    
    draw_arrow_h(draw, 430, 500, 260, "1. Search Query")
    
    draw_card(draw, 980, 140, 325, 240, 'EPISTEMIC GATE', 'VALIDITY VERIFICATION', [
        ('• Check supersession chain', FONT_BODY_B, INK_RUST),
        ('• Has fact been invalidated?', FONT_BODY, INK_MID),
        ('• Bi-temporal valid window', FONT_BODY, INK_MID),
        ('• Provenance path check', FONT_BODY, INK_MID)
    ])
    
    draw_arrow_h(draw, 920, 980, 260, "2. Top Chunks")
    
    draw_card(draw, 70, 430, 510, 260, 'VAULT IMMUTABILITY INVARIANT', 'HISTORICAL ARCHIVE REMAINS PRISTINE', [
        ('• Vault pages are never mutated during lookup', FONT_BODY, INK_MID),
        ('• Read-only access locks protect provenance', FONT_BODY_B, INK_DARK),
        ('• Changes are recorded as additive new versions', FONT_BODY, INK_MID),
        ('• Full bi-temporal audit trail maintained forever', FONT_BODY_B, INK_BLUE),
        ('• Lossless Layer 0 raw logs preserve ground truth', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 660, 430, 645, 260, 'REACTIVATION INTO WORKING FRAME', 'PROJECTION INTO PREFRONTAL dlPFC ATTENTION SLOTS', [
        ('• Clean, high-density synthesis delta loaded into active conversation frame', FONT_BODY_B, INK_DARK),
        ('• Read-only reference: Agent uses fact without mutating historical record', FONT_BODY, INK_MID),
        ('• Preserves Cowan limit (4 ± 1 chunks) by returning compact answers', FONT_BODY, INK_MID),
        ('• Bidirectional wikilink retains link to Layer 0 raw logs for audit', FONT_BODY_B, INK_GREEN)
    ])
    
    draw_arrow_v(draw, 1142, 380, 430, "3. Verified Delta", color=INK_GREEN)
    draw_arrow_h(draw, 660, 580, 560, "Audit Link", color=INK_BLUE)
    
    img.save('assets/knowledge_reactivation_flow.jpg', quality=95)


def gen_durable_vs_rebuildable():
    img = get_parchment_canvas(47)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XIV: DURABLE KNOWLEDGE VERSUS REBUILDABLE INDEX PHILOSOPHY',
                      'CANONICAL BEDROCK SOURCE OF TRUTH VS. EPHEMERAL DERIVED ACCELERATORS')
    
    col_w = 590
    y = 135
    h = 460
    
    draw_card(draw, 70, y, col_w, h, 'CANONICAL & DURABLE (SOURCE OF TRUTH)', 'THE PERMANENT BEDROCK (NEVER DESTROYED)', [
        ('1. Plain Markdown Corpora:', FONT_BODY_B, INK_DARK),
        ('   • Active Wiki (~/.hermes/active-wiki/)', FONT_CODE, INK_MID),
        ('   • Oracle Curated Vault (~/.hermes/oracle/brain/)', FONT_CODE, INK_MID),
        ('2. Deterministic [[wikilink]] Relational References', FONT_BODY_B, INK_DARK),
        ('3. Atomic Git Version History & SHA-256 Commits', FONT_BODY_B, INK_DARK),
        ('4. Preserved Raw Evidence & Output Traces (~/.hermes/oracle/raw/)', FONT_BODY_B, INK_DARK),
        ('', FONT_BODY, INK_MID),
        ('CORE INVARIANT:', FONT_BODY_B, INK_RUST),
        ('• Human-readable, git-versioned, survives total infrastructure wipe.', FONT_BODY, INK_MID),
        ('• No proprietary database engine lock-in.', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 715, y, col_w, h, 'DISPOSABLE & REBUILDABLE (ACCELERATORS)', 'EPHEMERAL DERIVED SEARCH INDEXES (REBUILDABLE)', [
        ('1. PostgreSQL 18.6 pgvector HNSW Index:', FONT_BODY_B, INK_DARK),
        ('   • Qwen3 2560-dim dense semantic embeddings', FONT_CODE, INK_MID),
        ('2. ParadeDB pg_search BM25 Inverted Token Index:', FONT_BODY_B, INK_DARK),
        ('   • Full-text keyword token matrices', FONT_CODE, INK_MID),
        ('3. Graphify AST Knowledge Graph:', FONT_BODY_B, INK_DARK),
        ('   • Derived concept graph & PageRank diffusion cache', FONT_CODE, INK_MID),
        ('4. Ephemeral SQLite Caches & Vector Buffers', FONT_BODY_B, INK_DARK),
        ('', FONT_BODY, INK_MID),
        ('CORE INVARIANT:', FONT_BODY_B, INK_BLUE),
        ('• Disposable: Any index can be wiped and re-extracted from Markdown.', FONT_BODY, INK_MID),
        ('• Search accelerates retrieval; it never defines truth.', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 70, 610, 1235, 95, 'THE ONE-WAY ARCHITECTURAL CONTRACT', None, [
        ('ONE-WAY EXTRACTION: Markdown Files ──[Extract & Index]──> PostgreSQL, BM25 & Graphify Indexes', FONT_BODY_B, INK_DARK),
        ('If any database corrupts or desynchronizes, `python scripts/brain_sync.py --rebuild` restores 100% fidelity in seconds.', FONT_BODY, INK_MID)
    ])
    
    img.save('assets/durable_vs_rebuildable.jpg', quality=95)


def gen_graphify_flow():
    img = get_parchment_canvas(50)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XV: DERIVED KNOWLEDGE GRAPH & MULTI-HOP TRAVERSAL FLOW',
                      'RELATIONAL NAVIGATION ACROSS EXPLICIT WIKILINKS AND EXTRACTED CONCEPTS')
    
    draw_card(draw, 70, 125, 1235, 105, 'COMPLEX MULTI-ENTITY INQUIRY', 'QUERY ROUTING STAGE', [
        ('Input Query: "How does the Somatic Marker risk score modulate the Striatal Action Gate during shell execution?"', FONT_BODY_B, INK_DARK),
        ('Evaluator: Learned Hop Classifier (Dense Vector Projection, macro-F1 = 0.86)', FONT_BODY, INK_BLUE)
    ])
    
    draw_arrow_v(draw, 350, 230, 275, "Single-Hop (<12ms)", color=INK_GREEN)
    draw_arrow_v(draw, 980, 230, 275, "Multi-Hop Relational", color=INK_RUST)
    
    draw_card(draw, 70, 275, 560, 255, 'SINGLE-HOP: DIRECT LEXICAL / RAG', 'FAST BM25 EXACT LOOKUP (<12ms LATENCY)', [
        ('• Scans ParadeDB BM25 index on PostgreSQL', FONT_BODY, INK_MID),
        ('• Direct keyword match over indexed [[wikilinks]]', FONT_BODY, INK_MID),
        ('• Sub-millisecond title and section lookup', FONT_BODY, INK_MID),
        ('• Bypasses graph traversal overhead entirely', FONT_BODY_B, INK_GREEN),
        ('• Benchmark: Tuned BM25 leads by ~20 points at scale', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 680, 275, 625, 255, 'MULTI-HOP: GRAPH TRAVERSAL', 'PERSONALIZED PAGERANK DIFFUSION (PPR)', [
        ('• Traverses derived AST concept and wikilink graph', FONT_BODY, INK_MID),
        ('• Path Extraction: [SomaticMarker] ──[biases]──> [StriatalGate]', FONT_BODY_B, INK_DARK),
        ('• Resolves supersession chains & version dependencies', FONT_BODY, INK_MID),
        ('• Revision-chain recall reaches 100% vs 25% for raw RAG', FONT_BODY_B, INK_BLUE),
        ('• Bounded: Used ONLY where single-hop RAG fails', FONT_BODY, INK_RUST)
    ])
    
    draw_arrow_v(draw, 350, 530, 565, color=INK_GREEN)
    draw_arrow_v(draw, 980, 530, 565, color=INK_RUST)
    
    draw_card(draw, 70, 565, 1235, 140, 'PROVENANCE PATH RECONSTRUCTION', 'EXPLANATORY AUDIT TRAIL', [
        ('EXPLICIT RECONSTRUCTED GRAPH PATH:', FONT_BODY_B, INK_DARK),
        ('  Concept A: SomaticMarker (risk_score) ──[modulates]──> Concept B: ActionGate (GO/NO_GO) ──> Fact: Halts on Exit Non-Zero', FONT_CODE, INK_BLUE),
        ('Deterministic Rule: Every traversed hop must cite a real file anchor. Hallucinated edges are rejected by the Epistemic Gate.', FONT_BODY, INK_MID)
    ])
    
    img.save('assets/graphify_retrieval_flow.jpg', quality=95)


def gen_organizer_vs_kanban():
    img = get_parchment_canvas(51)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XVI: TASK ORCHESTRATION DIVISION: ORGANIZER VS. KANBAN',
                      'DETERMINISTIC LIFETIME CALENDAR STATE VERSUS EPHEMERAL EXECUTION CHECKLISTS')
    
    col_w = 590
    y = 135
    h = 450
    
    draw_card(draw, 70, y, col_w, h, 'PERSONAL ORGANIZER (organizer.db)', 'HUMAN LIFE & CALENDAR STATE (SQLITE ON DISK)', [
        ('1. Human Tasks & Milestones:', FONT_BODY_B, INK_DARK),
        ('   • Projects, deadlines, priority sorting, progress rings', FONT_BODY, INK_MID),
        ('2. Subscription & Renewal Management:', FONT_BODY_B, INK_DARK),
        ('   • Domain renewals, cloud billing dates, service contracts', FONT_BODY, INK_MID),
        ('3. Waiting-For & Delegated States:', FONT_BODY_B, INK_DARK),
        ('   • External counterparty dependencies & follow-up dates', FONT_BODY, INK_MID),
        ('4. Multi-Channel Timed Reminders:', FONT_BODY_B, INK_DARK),
        ('   • Dispatched via Telegram, Discord, Slack, SMS, Desktop', FONT_BODY, INK_MID),
        ('5. Prospective Intentions Ledger (Gollwitzer IF-THEN rules)', FONT_BODY_B, INK_RUST),
        ('', FONT_BODY, INK_MID),
        ('LIFECYCLE INVARIANT: Survives agent wipes and reboots.', FONT_BODY_B, INK_GREEN)
    ])
    
    draw_card(draw, 715, y, col_w, h, 'HERMES KANBAN (kanban.db)', 'AGENT EXECUTION & SUBTASKS (FAST IN-MEMORY / DB)', [
        ('1. Autonomous Sub-Agent Decomposition:', FONT_BODY_B, INK_DARK),
        ('   • Planner subgoals, multi-profile dispatch queues', FONT_BODY, INK_MID),
        ('2. Parallel Tool Workflows & Checklists:', FONT_BODY_B, INK_DARK),
        ('   • Shell commands, compiler passes, test suites', FONT_BODY, INK_MID),
        ('3. Intermediate Refactoring Stages:', FONT_BODY_B, INK_DARK),
        ('   • File modification queues, git staging operations', FONT_BODY, INK_MID),
        ('4. Ephemeral Verification Traces:', FONT_BODY_B, INK_DARK),
        ('   • Verify-on-stop assertion logs, test exit codes', FONT_BODY, INK_MID),
        ('5. Temporary Workspace Branch Isolation', FONT_BODY_B, INK_BLUE),
        ('', FONT_BODY, INK_MID),
        ('LIFECYCLE INVARIANT: Ephemeral; tied to active job duration.', FONT_BODY_B, INK_RUST)
    ])
    
    draw_card(draw, 70, 605, 1235, 100, 'THE ORCHESTRATION DIVISION OF AUTHORITY', None, [
        ('• The human user\'s life, commitments, and deadlines live in `organizer.db`. The agent never mutates these without consent.', FONT_BODY_B, INK_DARK),
        ('• The agent\'s internal work breakdown lives in `kanban.db` and can be wiped and re-planned at zero cost.', FONT_BODY, INK_MID)
    ])
    
    img.save('assets/organizer_vs_kanban_division.jpg', quality=95)


def gen_prospective_engine():
    img = get_parchment_canvas(52)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XVII: PROSPECTIVE MEMORY ENGINE (FUTURE INTENTIONS)',
                      'GOLLWITZER IMPLEMENTATION INTENTIONS: IF CUE X OCCURS THEN EXECUTE Y')
    
    draw_card(draw, 70, 130, 1235, 140, 'INTENTION PARSING & EXTRACTION (brain/prospective/intentions.py)', 'NATURAL LANGUAGE INTENTION FORMULATION', [
        ('Human Input:  "When the server restarts, verify the ParadeDB search index."', FONT_BODY_B, INK_DARK),
        ('Parsed Cue:   TriggerCondition("server restarts")  |  Expiry: TTL(24h)  |  Context: Infrastructure', FONT_CODE, INK_BLUE),
        ('Target Action: IntentionAction("verify ParadeDB index health via scripts/integrity_check.py")', FONT_CODE, INK_GREEN)
    ])
    
    table_x = 70
    table_y = 295
    table_w = 1235
    table_h = 240
    draw.rectangle([table_x, table_y, table_x + table_w, table_y + table_h], outline=INK_DARK, width=2)
    draw.rectangle([table_x + 3, table_y + 3, table_x + table_w - 3, table_y + table_h - 3], outline=INK_MID, width=1)
    
    draw.rectangle([table_x, table_y, table_x + table_w, table_y + 40], fill=(215, 192, 150), outline=INK_DARK, width=1)
    draw.text((table_x + 20, table_y + 10), "ID", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((table_x + 80, table_y + 10), "TRIGGER CUE PATTERN", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((table_x + 440, table_y + 10), "INTENDED ACTION TARGET", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((table_x + 920, table_y + 10), "STATUS", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((table_x + 1070, table_y + 10), "TTL / EXPIRY", fill=INK_DARK, font=FONT_BODY_B)
    
    rows = [
        ("1", "server restarts / boot event", "Check ParadeDB BM25 index & pgvector health", "ACTIVE", "24 Hours"),
        ("2", "discuss GPU architecture", "Audit PCIe memory bandwidth & VRAM headroom", "ACTIVE", "7 Days"),
        ("3", "git push main", "Execute integrity_check.py & verify PRAGMAs", "ACTIVE", "48 Hours"),
        ("4", "package delivery event", "Surface hardware assembly checklist to user", "ACTIVE", "12 Hours"),
    ]
    
    for i, (rid, cue, act, stat, ttl) in enumerate(rows):
        ry = table_y + 40 + i * 48
        draw.line([table_x, ry, table_x + table_w, ry], fill=INK_MID, width=1)
        draw.text((table_x + 20, ry + 14), rid, fill=INK_DARK, font=FONT_BODY)
        draw.text((table_x + 80, ry + 14), cue, fill=INK_DARK, font=FONT_BODY_B)
        draw.text((table_x + 440, ry + 14), act, fill=INK_MID, font=FONT_BODY)
        draw.text((table_x + 920, ry + 14), stat, fill=INK_GREEN, font=FONT_BODY_B)
        draw.text((table_x + 1070, ry + 14), ttl, fill=INK_RUST, font=FONT_BODY)
        
    for gx in [table_x + 60, table_x + 420, table_x + 900, table_x + 1050]:
        draw.line([gx, table_y, gx, table_y + table_h], fill=INK_MID, width=1)
        
    draw_card(draw, 70, 560, 1235, 145, 'BENCHMARK MEASUREMENT: THE VALUE OF TYPED PROSPECTIVE MEMORY', None, [
        ('• On purpose-built prospective memory benchmarks, typed intention storage moved accuracy from 4.2% to 66.2% Set-F1.', FONT_BODY_B, INK_DARK),
        ('• Beat every retrospective memory method tested (none exceeded 54.4%).', FONT_BODY, INK_MID),
        ('• Architectural reason: Lifecycle rules live in deterministic code rather than drifting inside model probabilistic weights.', FONT_BODY_B, INK_BLUE)
    ])
    
    img.save('assets/prospective_memory_engine.jpg', quality=95)


def gen_prospective_triggering():
    img = get_parchment_canvas(53)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XVIII: PROSPECTIVE EVENT-TRIGGERING ARCHITECTURE',
                      'CONTINUOUS CUE EVALUATION STREAM AND MULTI-CHANNEL DISPATCH')
    
    draw_card(draw, 70, 125, 1235, 120, 'EVENT STIMULUS STREAM (INCOMING SENSORY RELAY)', 'CONTINUOUS MONITORING WITHOUT POLLING LOOPS', [
        ('Sensory Sources: Shell tool output  •  CLI exit codes  •  Cron scheduler ticks (60s)  •  Agent turn start triggers', FONT_BODY_B, INK_DARK),
        ('Relayed non-invasively through Thalamic sensory buffer (`brain/thalamus/buffer.py`) with Shannon entropy gating.', FONT_BODY, INK_MID)
    ])
    
    draw_arrow_v(draw, 688, 245, 285, "Stimulus Ingestion")
    
    draw_card(draw, 70, 285, 580, 215, 'TEMPORAL CUE EVALUATOR', 'TIME-BASED REMINDERS (`scripts/check_reminders.py`)', [
        ('• Evaluated every 60 seconds (<0.01% CPU, <5MB RAM)', FONT_BODY, INK_MID),
        ('• Condition: Current Timestamp >= Due Date', FONT_CODE, INK_DARK),
        ('• Dispatches pending alert notifications', FONT_BODY, INK_MID),
        ('• Handles snooze, recurring cadences, and deadlines', FONT_BODY_B, INK_BLUE)
    ])
    
    draw_card(draw, 725, 285, 580, 215, 'CONTEXTUAL CUE EVALUATOR', 'EVENT PATTERN MATCHER (`brain/prospective/intentions.py`)', [
        ('• Evaluated on every agent turn and tool execution', FONT_BODY, INK_MID),
        ('• Condition: PatternMatch(Stimulus, CueTrigger)', FONT_CODE, INK_DARK),
        ('• Matches natural language regex and semantic similarity', FONT_BODY, INK_MID),
        ('• Fires intention execution upon cue detection', FONT_BODY_B, INK_GREEN)
    ])
    
    draw_arrow_v(draw, 360, 500, 540)
    draw_arrow_v(draw, 1015, 500, 540)
    
    draw_card(draw, 70, 540, 1235, 165, 'INTENTION EXECUTION DISPATCHER (MULTI-CHANNEL)', 'SIMULTANEOUS AGENT SURFACING & USER NOTIFICATION', [
        ('1. IN-SESSION AGENT PROMPT: Injects intention context directly into active Hermes prompt frame.', FONT_BODY_B, INK_DARK),
        ('2. OUTBOUND USER NOTIFICATIONS: Dispatches alerts to Telegram Bot, Discord Webhook, Slack, SMS, or Desktop.', FONT_BODY_B, INK_BLUE),
        ('3. DETERMINISTIC STATE MUTATION: Marks intention FULFILLED in `organizer.db` with completion timestamp.', FONT_BODY_B, INK_GREEN),
        ('Zero Cloud Dependency: Runs entirely self-hosted on local hardware.', FONT_BODY, INK_MUTED)
    ])
    
    img.save('assets/prospective_event_triggering.jpg', quality=95)


def gen_epistemic_action_gate():
    img = get_parchment_canvas(54)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XIX: EPISTEMIC ACTION GATE: EVIDENCE IS NOT BELIEF',
                      'PROVENANCE-BASED CONFIDENCE VERIFICATION PRIOR TO TOOL EXECUTION')
    
    draw_card(draw, 70, 130, 360, 260, 'EPISTEMIC CLASSIFIER', 'PROVENANCE SORTING', [
        ('Incoming Claim Ingestion:', FONT_BODY_B, INK_DARK),
        ('• Class 1: user_asserted (Stated by user)', FONT_BODY, INK_MID),
        ('• Class 2: verified_empirical (Exit 0)', FONT_BODY_B, INK_GREEN),
        ('• Class 3: inferred_unverified (Hypothesis)', FONT_BODY, INK_MID),
        ('• Class 4: disputed (Contradiction)', FONT_BODY_B, INK_RUST),
        ('• Class 5: superseded (Outdated)', FONT_BODY, INK_MUTED)
    ])
    
    cx, cy = 688, 250
    draw.rectangle([480, 130, 896, 260], outline=INK_DARK, width=2)
    draw.rectangle([483, 133, 893, 257], outline=INK_MID, width=1)
    draw.text((560, 145), "CONFIDENCE SCORING ENGINE", fill=INK_DARK, font=FONT_SECTION)
    
    draw_dial(draw, cx, cy + 15, 52, "EPISTEMIC CONFIDENCE", "c = 0.94", 60, color=INK_GREEN)
    
    draw_arrow_h(draw, 430, 480, 240, "Claims")
    draw_arrow_h(draw, 896, 960, 195, "Pass", color=INK_GREEN)
    draw_arrow_h(draw, 896, 960, 325, "Fail", color=INK_RUST)
    
    draw_card(draw, 960, 130, 345, 135, 'PROCEED TO ACTION', 'GO PATHWAY (c >= 0.85)', [
        ('• High epistemic confidence', FONT_BODY, INK_MID),
        ('• Reversible action verified', FONT_BODY, INK_MID),
        ('• Tool execution authorized', FONT_BODY_B, INK_GREEN)
    ], border_color=INK_GREEN)
    
    draw_card(draw, 960, 275, 345, 135, 'EPISTEMIC GATE LOCK', 'NO-GO / DISPUTED', [
        ('• Contradictory evidence detected', FONT_BODY, INK_MID),
        ('• Execution halted immediately', FONT_BODY_B, INK_RUST),
        ('• Auditor sub-agent dispatched', FONT_BODY, INK_MID)
    ], border_color=INK_RUST)
    
    draw_card(draw, 70, 430, 1235, 275, 'CONCRETE DISPUTATION RESOLUTION TRACE', 'HOW ToMi HANDLES CONFLICTING EVIDENCE', [
        ('SCENARIO: Source A asserts `context = 128K`, while Source B asserts `context = 256K`:', FONT_BODY_B, INK_DARK),
        ('  1. DISPUTE REGISTRATION: Epistemic Gate sets claim status to DISPUTED (Confidence drops from 0.90 to 0.40).', FONT_BODY, INK_MID),
        ('  2. ACTION INHIBITION: Striatal action gate blocks shell commands attempting to configure cluster memory.', FONT_BODY_B, INK_RUST),
        ('  3. AUDITOR DELEGATION: Main Hermes spawns Auditor sub-agent with isolated context to inspect raw runtime config.', FONT_BODY, INK_MID),
        ('  4. DETERMINISTIC RESOLUTION: Auditor runs `llama-server --version`, finds model supports 256K, updates record to verified_empirical.', FONT_BODY_B, INK_GREEN),
        ('  5. BELIEF COMMITTED: AGM Levi Identity updates Knowledge Base without destroying Source A historical provenance.', FONT_BODY, INK_BLUE)
    ])
    
    img.save('assets/epistemic_action_gate.jpg', quality=95)


def gen_epistemic_lifecycle():
    img = get_parchment_canvas(55)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XX: EPISTEMIC BELIEF LIFECYCLE & STATE MACHINE',
                      'MATHEMATICAL STATE TRANSITIONS UNDER POLLOCK DEFEASIBLE LOGIC')
    
    nodes = [
        ('RAW EVIDENCE', 'Sensory stimulus / tool log', 200, 210, INK_DARK),
        ('INFERRED UNVERIFIED', 'LLM hypothesis / deduction', 580, 210, INK_MID),
        ('VERIFIED EMPIRICAL', 'Exit 0 / Tests / Assertions', 980, 210, INK_GREEN),
        ('DISPUTED', 'Rebutting defeater detected', 580, 420, INK_RUST),
        ('CANONICAL BELIEF', 'Entrenched in Knowledge Base', 980, 420, INK_BLUE),
        ('SUPERSEDED', 'Cleanly replaced by newer fact', 580, 600, INK_MUTED),
    ]
    
    for title, desc, cx, cy, col in nodes:
        w, h = 260, 95
        x, y = cx - w//2, cy - h//2
        draw.rectangle([x, y, x + w, y + h], outline=col, width=2)
        draw.rectangle([x + 3, y + 3, x + w - 3, y + h - 3], outline=INK_MID, width=1)
        tw = draw.textlength(title, font=FONT_SECTION)
        draw.text((cx - tw/2, y + 16), title, fill=col, font=FONT_SECTION)
        dw = draw.textlength(desc, font=FONT_SMALL)
        draw.text((cx - dw/2, y + 52), desc, fill=INK_MID, font=FONT_SMALL)
        
    draw_arrow_h(draw, 330, 450, 210, "1. Deduce", color=INK_DARK)
    draw_arrow_h(draw, 710, 850, 210, "2. Verify (Exit 0)", color=INK_GREEN)
    
    draw_arrow_v(draw, 580, 258, 372, "Contradiction", color=INK_RUST)
    draw_arrow_v(draw, 980, 258, 372, "3. AGM Entrench", color=INK_BLUE)
    
    draw_arrow_h(draw, 710, 850, 420, "Reconcile", color=INK_BLUE)
    draw_arrow_v(draw, 580, 468, 552, "Invalidated", color=INK_MUTED)
    
    draw_card(draw, 70, 665, 1235, 65, 'IMMUTABILITY INVARIANT: PARENT BELIEFS ARE NEVER DELETED', None, [
        ('When a belief becomes SUPERSEDED, it remains as an immutable parent in the history graph for counterfactual audit.', FONT_BODY_B, INK_DARK)
    ])
    
    img.save('assets/epistemic_belief_lifecycle.jpg', quality=95)


def gen_research_protocol():
    img = get_parchment_canvas(60)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXI: RESEARCH PROTOCOL & CONTEXT ISOLATION FLOW',
                      'PROTECTING EXECUTIVE ATTENTION FROM WEB SCRAPING NOISE VIA ISOLATED DELEGATION')
    
    draw_card(draw, 70, 130, 360, 260, 'MAIN HERMES AGENT', 'EXECUTIVE WORKSPACE', [
        ('• Direct user conversation & intent', FONT_BODY, INK_MID),
        ('• dlPFC Cowan limit: 4 ± 1 chunks', FONT_BODY_B, INK_DARK),
        ('• ABSOLUTE INVARIANT:', FONT_BODY_B, INK_RUST),
        ('  Main Hermes NEVER searches web', FONT_BODY_B, INK_RUST),
        ('• Insulated from HTML / DOM noise', FONT_BODY, INK_MID),
        ('• Dispatches clean research tasks', FONT_BODY, INK_GREEN)
    ])
    
    draw_card(draw, 500, 130, 440, 260, 'RESEARCHER PROFILE', 'ISOLATED SUB-AGENT CONTEXT', [
        ('1. SearXNG Metasearch (:8080):', FONT_BODY_B, INK_DARK),
        ('   • Aggregates 70+ engines locally', FONT_BODY, INK_MID),
        ('2. Firecrawl Scraper & CamoFox:', FONT_BODY_B, INK_DARK),
        ('   • Headless DOM -> Clean Markdown', FONT_BODY, INK_MID),
        ('3. Source Epistemic Cross-Check:', FONT_BODY_B, INK_DARK),
        ('   • Triangulates claims across domains', FONT_BODY, INK_BLUE)
    ])
    
    draw_arrow_h(draw, 430, 500, 250, "1. Delegate Task")
    
    draw_card(draw, 1010, 130, 295, 260, 'RESEARCH BRIEF', 'COMPACT DELIVERABLE', [
        ('Output Specifications:', FONT_BODY_B, INK_DARK),
        ('• 500-800 token factual delta', FONT_BODY_B, INK_GREEN),
        ('• Verifiable citation URLs', FONT_BODY, INK_MID),
        ('• Epistemic provenance tags', FONT_BODY, INK_MID),
        ('• Zero raw HTML / CSS garbage', FONT_BODY_B, INK_RUST),
        ('• Injected into Main dlPFC', FONT_BODY_B, INK_DARK)
    ])
    
    draw_arrow_h(draw, 940, 1010, 250, "2. Synthesize")
    
    draw.line([(1155, 390), (1155, 435), (250, 435), (250, 390)], fill=INK_RUST, width=2)
    draw.polygon([(244, 400), (256, 400), (250, 390)], fill=INK_RUST)
    draw.text((540, 415), "3. Clean Markdown Synthesis Delta Returned to Main Hermes", fill=INK_RUST, font=FONT_BODY_B)
    
    draw_card(draw, 70, 465, 1235, 240, 'THE ARCHITECTURAL VALUE OF CONTEXT ISOLATION', None, [
        ('• Scraping a single modern documentation page ingests 50,000+ tokens of navigational boilerplate, scripts, and tracking markup.', FONT_BODY, INK_MID),
        ('• If ingested directly into the executive agent, needle-in-a-haystack attention degrades by up to 54%, collapsing reasoning precision.', FONT_BODY_B, INK_RUST),
        ('• By delegating web search to the isolated Researcher profile, Main Hermes maintains pristine, focused working memory.', FONT_BODY_B, INK_GREEN),
        ('• Result: Unlimited research depth with zero context pollution.', FONT_BODY_B, INK_BLUE)
    ])
    
    img.save('assets/research_protocol_flow.jpg', quality=95)


def gen_planner_contract():
    img = get_parchment_canvas(61)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXII: PLANNER WORLD-MODEL CONTRACT & PRE-MORTEM REASONING',
                      'COUNTERFACTUAL SIMULATION OF FAILURE MODES PRIOR TO ACTION DISPATCH')
    
    draw_card(draw, 70, 130, 1235, 110, 'HIGH-CONSEQUENCE GOAL SPECIFICATION', 'INPUT STIMULUS', [
        ('Goal Request: "Migrate PostgreSQL database, rebuild HNSW vector indexes, and update production systemd units."', FONT_BODY_B, INK_DARK),
        ('Planner Sub-Agent activates pre-mortem counterfactual simulation before issuing any shell command.', FONT_BODY, INK_BLUE)
    ])
    
    draw_arrow_v(draw, 688, 240, 275)
    
    draw.rectangle([340, 275, 1036, 335], outline=INK_RUST, width=2)
    draw.text((365, 288), "PRE-MORTEM QUESTION: \"Assume this failed catastrophically. What broke?\"", fill=INK_RUST, font=FONT_SECTION)
    
    draw.line([(688, 335), (688, 352)], fill=INK_DARK, width=2)
    draw.line([(260, 352), (1115, 352)], fill=INK_DARK, width=2)
    draw_arrow_v(draw, 260, 352, 375, color=INK_BLUE)
    draw_arrow_v(draw, 688, 352, 375, color=INK_RUST)
    draw_arrow_v(draw, 1115, 352, 375, color=INK_GREEN)
    
    bw = 380
    bh = 200
    by = 375
    
    draw_card(draw, 70, by, bw, bh, '1. HIDDEN DEPENDENCIES', 'ENVIRONMENT PREREQUISITES', [
        ('• Verify required packages installed', FONT_BODY, INK_MID),
        ('• Check database port bindings (5433)', FONT_BODY, INK_MID),
        ('• Validate disk headroom for vacuum', FONT_BODY, INK_MID),
        ('• Audit shared library versions', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 498, by, bw, bh, '2. IRREVERSIBILITY CHECK', 'DESTRUCTIVE WRITE AUDIT', [
        ('• Flag file deletions & table drops', FONT_BODY_B, INK_RUST),
        ('• Require atomic database snapshots', FONT_BODY, INK_MID),
        ('• Mandate automated rollback script', FONT_BODY_B, INK_DARK),
        ('• Verify backup checksum on disk', FONT_BODY, INK_MID)
    ], border_color=INK_RUST)
    
    draw_card(draw, 925, by, bw, bh, '3. UNVERIFIED ASSUMPTIONS', 'EPISTEMIC GROUNDING', [
        ('• Interrogate speculative hypotheses', FONT_BODY, INK_MID),
        ('• Confirm live cluster config matches docs', FONT_BODY, INK_MID),
        ('• Run read-only probes (`EXPLAIN`)', FONT_BODY_B, INK_GREEN),
        ('• Block until facts are verified_empirical', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 70, 605, 1235, 100, 'RESULT: GROUNDED, REVERSIBLE EXECUTION PLAN', None, [
        ('Execution proceeds ONLY when pre-mortem failure modes are neutralized with explicit rollback gates.', FONT_BODY_B, INK_DARK),
        ('Commands are wrapped in consequence gates: read-only verification -> atomic mutation -> post-condition validation.', FONT_BODY, INK_GREEN)
    ])
    
    img.save('assets/planner_world_model_contract.jpg', quality=95)


def gen_action_gate():
    img = get_parchment_canvas(62)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXIII: STRIATAL INHIBITORY ACTION GATE (BASAL GANGLIA)',
                      'THREE BOUNDED-LATENCY PATHWAYS: GO, NO-GO, AND HYPERDIRECT EMERGENCY BRAKE')
    
    draw_card(draw, 70, 130, 1235, 95, 'ACTION STIMULUS: SHELL COMMAND / TOOL EXECUTION', 'HOOK: hooks/brain-cognitive-guard (on command:*)', [
        ('Incoming action evaluated against Epistemic Status, Somatic Risk Score, and System Invariants in <5ms.', FONT_BODY_B, INK_DARK)
    ])
    
    draw_arrow_v(draw, 275, 225, 275, color=INK_GREEN)
    draw_arrow_v(draw, 688, 225, 275, color=INK_RUST)
    draw_arrow_v(draw, 1100, 225, 275, color=INK_DARK)
    
    pw = 380
    ph = 330
    py = 275
    
    draw_card(draw, 70, py, pw, ph, 'DIRECT PATHWAY', 'DECISION: GO', [
        ('Condition:', FONT_BODY_B, INK_DARK),
        ('• Preconditions empirically verified', FONT_BODY, INK_MID),
        ('• Epistemic confidence c >= 0.85', FONT_BODY, INK_MID),
        ('• Action is fully reversible', FONT_BODY, INK_MID),
        ('• Somatic risk score < 0.30', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Runtime Outcome:', FONT_BODY_B, INK_DARK),
        ('• Tool execution authorized instantly', FONT_BODY_B, INK_GREEN),
        ('• Zero human friction or latency lag', FONT_BODY, INK_MID)
    ], border_color=INK_GREEN)
    
    draw_card(draw, 498, py, pw, ph, 'INDIRECT PATHWAY', 'DECISION: NO-GO', [
        ('Condition:', FONT_BODY_B, INK_DARK),
        ('• Disputed claims or missing proof', FONT_BODY_B, INK_RUST),
        ('• Unverified speculative hypothesis', FONT_BODY, INK_MID),
        ('• Moderate somatic risk (0.30 - 0.70)', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Runtime Outcome:', FONT_BODY_B, INK_DARK),
        ('• Execution inhibited', FONT_BODY_B, INK_RUST),
        ('• Dispatches Auditor / Researcher probe', FONT_BODY, INK_MID),
        ('• Unblocks once ground truth resolved', FONT_BODY_B, INK_BLUE)
    ], border_color=INK_RUST)
    
    draw_card(draw, 925, py, pw, ph, 'HYPERDIRECT PATHWAY', 'DECISION: EMERGENCY BRAKE', [
        ('Condition:', FONT_BODY_B, INK_DARK),
        ('• Irreversible destructive command', FONT_BODY_B, INK_RUST),
        ('  (`rm -rf`, `DROP DATABASE`)', FONT_CODE, INK_DARK),
        ('• Safety invariant violation', FONT_BODY_B, INK_RUST),
        ('• Somatic visceral alarm > 0.85', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Runtime Outcome:', FONT_BODY_B, INK_DARK),
        ('• Hard halt: emit_collect -> deny', FONT_BODY_B, INK_RUST),
        ('• Requires explicit human consent', FONT_BODY_B, INK_DARK)
    ], border_color=INK_DARK)
    
    draw_card(draw, 70, 620, 1235, 90, 'HERMES CORE RUNTIME HOOK CONTRACT', None, [
        ('• In Hermes runtime, only `command:*` events honor return values (`deny` / `handled` / `rewrite`).', FONT_BODY_B, INK_DARK),
        ('• On `agent:step`, handlers discard returns, so cognitive gating must enforce at the tool execution boundary.', FONT_BODY, INK_MID)
    ])
    
    img.save('assets/action_gate_decision_matrix.jpg', quality=95)


def gen_consequence_gated():
    img = get_parchment_canvas(63)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXIV: CONSEQUENCE-GATED EXECUTION & VALUE OF INFORMATION',
                      'DYNAMIC BALANCING OF AUTONOMY VERSUS VERIFICATION UNDER UNCERTAINTY')
    
    mx = 360
    my = 150
    qw = 460
    qh = 240
    
    draw.text((mx + qw // 2 - 130, my - 30), "LOW OPERATIONAL CONSEQUENCE", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((mx + qw + 20 + qw // 2 - 130, my - 30), "HIGH OPERATIONAL CONSEQUENCE", fill=INK_RUST, font=FONT_BODY_B)
    
    draw.text((mx - 270, my + 100), "LOW UNCERTAINTY", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((mx - 270, my + qh + 120), "HIGH UNCERTAINTY", fill=INK_RUST, font=FONT_BODY_B)
    
    draw_card(draw, mx, my, qw, qh, 'AUTONOMOUS EXECUTION', 'SYSTEM 1 FAST PATH', [
        ('• Deterministic, safe tool actions', FONT_BODY, INK_MID),
        ('• Local file reads, regex parsing, status checks', FONT_BODY, INK_MID),
        ('• High measured competence in `experience.db`', FONT_BODY, INK_MID),
        ('• Zero confirmation prompts required', FONT_BODY_B, INK_GREEN)
    ], border_color=INK_GREEN)
    
    draw_card(draw, mx + qw + 20, my, qw, qh, 'CAREFUL VERIFICATION', 'DRY-RUN & PRE-MORTEM', [
        ('• Verified facts, but high blast radius', FONT_BODY_B, INK_DARK),
        ('• Production deployments, database migrations', FONT_BODY, INK_MID),
        ('• Dry-run simulation before execution', FONT_BODY, INK_MID),
        ('• Automated rollback checkpoint created', FONT_BODY_B, INK_BLUE)
    ], border_color=INK_BLUE)
    
    draw_card(draw, mx, my + qh + 20, qw, qh, 'RAPID PROBING', 'VALUE OF INFORMATION PROBE', [
        ('• Ambiguous parameters, but zero destructive risk', FONT_BODY, INK_MID),
        ('• Read-only probe resolves ambiguity instantly', FONT_BODY_B, INK_DARK),
        ('• Runs `--help`, `SELECT COUNT(*)`, test suite', FONT_BODY, INK_MID),
        ('• Avoids asking unnecessary user questions', FONT_BODY_B, INK_GREEN)
    ], border_color=INK_DARK)
    
    draw_card(draw, mx + qw + 20, my + qh + 20, qw, qh, 'CONSERVATIVE HALT', 'EPISTEMIC GATE LOCK', [
        ('• High consequence and ambiguous ground truth', FONT_BODY_B, INK_RUST),
        ('• Striatal action gate halts immediately', FONT_BODY_B, INK_RUST),
        ('• Spawns Auditor / prompts human operator', FONT_BODY, INK_MID),
        ('• Zero reckless guesswork permitted', FONT_BODY_B, INK_DARK)
    ], border_color=INK_RUST)
    
    draw_card(draw, 70, 660, 1235, 65, 'VALUE OF INFORMATION INVARIANT: PROBE CHEAPLY BEFORE ASKING', None, [
        ('ToMi probes the environment with read-only tools whenever consequence is low, eliminating 80% of annoying user questions.', FONT_BODY_B, INK_DARK)
    ])
    
    img.save('assets/consequence_gated_execution.jpg', quality=95)


def gen_cognitive_modes():
    img = get_parchment_canvas(64)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXV: ToMi COGNITIVE ROUTING MODES (TASK TOPOLOGY)',
                      'DYNAMIC ALLOCATION OF COGNITIVE COMPUTE TO TASK COMPLEXITY')
    
    modes = [
        ('1. DIRECT EXECUTION', 'Fast-Path System 1 Tooling', [
            '• Low-complexity tool commands',
            '• Unit test runs, file reads, grep',
            '• System 1 fast path (<10ms)',
            '• High competence in experience.db',
            '• Zero confirmation prompts',
            '• Direct tool dispatch in-process'
        ], INK_GREEN),
        ('2. REACTIVE DIALOGUE', 'Conversational Theory of Mind', [
            '• User Q&A & intent clarification',
            '• Recursive Theory of Mind (tom.py)',
            '• Gricean conversational maxims',
            '• Pragmatic implicature decoding',
            '• Belief & intention tracking',
            '• Zero tool execution overhead'
        ], INK_BLUE),
        ('3. DELIBERATIVE PLAN', 'System 2 Pre-Mortem Rollout', [
            '• Multi-step software architecture',
            '• Planner sub-agent decomposition',
            '• Pre-mortem failure analysis',
            '• Consequence-gated execution',
            '• Rollback checkpoint synthesis',
            '• Automated recovery fallbacks'
        ], INK_RUST),
        ('4. EPISTEMIC SEARCH', 'Deep Research & Vault Retrieval', [
            '• Missing or disputed ground truth',
            '• Delegated to Researcher / Oracle',
            '• SearXNG local metasearch (:8080)',
            '• Firecrawl headless web extraction',
            '• Additive synthesis to cold vault',
            '• dlPFC context insulated from noise'
        ], INK_DARK),
    ]
    
    card_w = 285
    start_x = 70
    gap = 25
    y = 150
    h = 440
    
    for i, (title, sub, bullets, col) in enumerate(modes):
        x = start_x + i * (card_w + gap)
        draw_card(draw, x, y, card_w, h, title, sub, bullets, border_color=col)
        
    draw_card(draw, 70, 615, 1235, 95, 'EMPIRICAL BENCHMARK: TASK ROUTING BEATS ONE-SIZE-FITS-ALL AGENTS', None, [
        ('• Direct lookups route to ParadeDB BM25 lexical search; multi-hop questions route to Graphify PageRank diffusion.', FONT_BODY_B, INK_DARK),
        ('• Dynamic routing achieves optimal token efficiency: simple tasks run instantly; complex tasks receive full pre-mortem compute.', FONT_BODY, INK_MID)
    ])
    
    img.save('assets/cognitive_routing_modes.jpg', quality=95)


def gen_metacognitive_routing():
    img = get_parchment_canvas(65)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXVI: METACOGNITIVE ROUTING FLOW (SYSTEM 1 VS. SYSTEM 2)',
                      'KAHNEMAN DUAL-PROCESS ROUTING GROUNDED IN MEASURED TASK COMPETENCE')
    
    draw_card(draw, 70, 125, 1235, 120, 'INCOMING STIMULUS STREAM (USER REQUEST / ENVIRONMENT EVENT)', 'PRE-TURN SENSORY BUFFER', [
        ('Evaluator: Metacognitive Pre-Turn Allocator (`brain/cortex/router.py`)', FONT_BODY_B, INK_DARK),
        ('Inputs: Domain novelty score  •  Somatic marker risk weight  •  Competence history Beta(alpha, beta) in `experience.db`', FONT_BODY, INK_MID)
    ])
    
    draw_arrow_v(draw, 350, 245, 280, "High Competence", color=INK_GREEN)
    draw_arrow_v(draw, 980, 245, 280, "High Consequence", color=INK_RUST)
    
    draw_card(draw, 70, 280, 560, 315, 'SYSTEM 1: FAST INTUITIVE PATH', 'LOW OVERHEAD DETERMINISTIC EXECUTION', [
        ('Trigger Conditions:', FONT_BODY_B, INK_DARK),
        ('• Competence ledger posterior >= 0.85', FONT_BODY, INK_GREEN),
        ('• Known procedural skill in `skills/` library', FONT_BODY, INK_MID),
        ('• Reversible action with low blast radius', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Execution Dynamics:', FONT_BODY_B, INK_DARK),
        ('• Direct tool dispatch without sub-agent fork', FONT_BODY, INK_MID),
        ('• Sub-millisecond cognitive latency', FONT_BODY, INK_GREEN),
        ('• Preserves user conversational momentum', FONT_BODY, INK_MID)
    ], border_color=INK_GREEN)
    
    draw_card(draw, 680, 280, 625, 310, 'SYSTEM 2: DELIBERATIVE ROLLOUT', 'HIGH-COMPUTE REASONING & PRE-MORTEM ROLLOUT', [
        ('Trigger Conditions:', FONT_BODY_B, INK_DARK),
        ('• Novel or unfamiliar domain without prior trace', FONT_BODY, INK_MID),
        ('• High operational consequence or disputed claims', FONT_BODY_B, INK_RUST),
        ('• Somatic visceral risk alarm > 0.40', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Execution Dynamics:', FONT_BODY_B, INK_DARK),
        ('• Spawns Planner sub-agent with isolated context', FONT_BODY, INK_MID),
        ('• Pre-mortem counterfactual simulation executed', FONT_BODY_B, INK_BLUE),
        ('• Multi-path rollback verification before execution', FONT_BODY, INK_MID)
    ], border_color=INK_BLUE)
    
    draw_card(draw, 70, 615, 1235, 95, 'EXECUTION FEEDBACK & TRACE LOGGING', None, [
        ('Both pathways converge into action execution, where outcomes are deterministically verified and recorded into `experience.db`.', FONT_BODY_B, INK_DARK),
        ('System 2 successes compile into reusable procedural skills, allowing future tasks to run via System 1.', FONT_BODY, INK_GREEN)
    ])
    
    img.save('assets/metacognitive_routing_flow.jpg', quality=95)


def gen_experience_loop():
    img = get_parchment_canvas(70)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXVII: EXPERIENCE COMPETENCE LOOP (experience.db)',
                      'CONTINUOUS EMPIRICAL REINFORCEMENT & POSTERIOR COMPETENCE UPDATES')
    
    draw_card(draw, 70, 130, 480, 260, '1. TASK EXECUTION TRACE', 'RAW RUNTIME ACTION LOGGING', [
        ('• Captures action name, target file/endpoint, params', FONT_BODY, INK_MID),
        ('• Measures duration_ms & tokens_used per step', FONT_BODY, INK_MID),
        ('• Logs initial environmental hypothesis', FONT_BODY, INK_MID),
        ('• Appends trace to `operations` table', FONT_BODY_B, INK_DARK)
    ])
    
    draw_card(draw, 70, 425, 480, 275, '2. VERIFY-ON-STOP REALITY CHECK', 'THREE-LAYER EMPIRICAL TESTING', [
        ('• Layer 1: Deterministic assert (Exit 0, file exists)', FONT_BODY_B, INK_GREEN),
        ('• Layer 2: Empirical state diff (DB rows, port bind)', FONT_BODY_B, INK_BLUE),
        ('• Layer 3: Auditor judgment (qualitative coherence)', FONT_BODY, INK_MID),
        ('• Invariant: Reality gets the final vote', FONT_BODY_B, INK_RUST),
        ('• Records result to `verification_checks` table', FONT_BODY, INK_MID)
    ])
    
    draw_arrow_v(draw, 310, 390, 425, "Outcome Check")
    
    draw_card(draw, 580, 130, 360, 570, '3. BAYESIAN POSTERIOR', 'BETA DISTRIBUTION LEDGER', border_color=INK_BLUE)
    draw_dial(draw, 760, 255, 60, "DOMAIN COMPETENCE", "P(Success) = 0.94", 65, color=INK_GREEN)
    
    draw.text((600, 355), "POSTERIOR FORMULA:", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((600, 385), "Posterior = Beta(α + succ, β + fail)", fill=INK_BLUE, font=FONT_BODY_B)
    draw.text((600, 415), "Mean Competence C = α / (α + β)", fill=INK_DARK, font=FONT_BODY)
    
    draw.line([600, 445, 920, 445], fill=INK_MID, width=1)
    
    draw.text((600, 460), "ROUTING IMPLICATION:", fill=INK_DARK, font=FONT_BODY_B)
    draw.text((600, 488), "• If C >= 0.85: System 1 Fast Path", fill=INK_GREEN, font=FONT_BODY_B)
    draw.text((600, 516), "• If C < 0.85:  System 2 Deliberative", fill=INK_RUST, font=FONT_BODY_B)
    draw.text((600, 544), "• Lowers cognitive cost automatically", fill=INK_MID, font=FONT_BODY)
    draw.text((600, 572), "  as skills are repeatedly proven.", fill=INK_MID, font=FONT_BODY)
    
    draw_arrow_h(draw, 550, 580, 560, color=INK_GREEN)
    
    draw_card(draw, 985, 130, 320, 290, 'THE 7-TABLE LEDGER', 'SQLITE: experience.db', [
        ('1. operations (Traces)', FONT_BODY_B, INK_DARK),
        ('2. verification_checks', FONT_BODY, INK_MID),
        ('3. routing_events', FONT_BODY, INK_MID),
        ('4. skill_events (Runs)', FONT_BODY, INK_MID),
        ('5. reflections (Lessons)', FONT_BODY, INK_BLUE),
        ('6. key_decisions (ADRs)', FONT_BODY, INK_DARK),
        ('7. prospective_log', FONT_BODY, INK_MID)
    ])
    
    draw_card(draw, 985, 445, 320, 255, 'EVIDENCE REFLECTION', 'TRIGGERED BY SURPRISE', [
        ('Trigger Conditions:', FONT_BODY_B, INK_DARK),
        ('• Command error / non-zero', FONT_BODY_B, INK_RUST),
        ('• Unexpected state delta', FONT_BODY, INK_MID),
        ('• Human user correction', FONT_BODY_B, INK_RUST),
        ('• High surprise (S >= 0.70)', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Never wastes idle compute.', FONT_BODY_B, INK_DARK)
    ], border_color=INK_RUST)
    
    draw.line([940, 570, 985, 570], fill=INK_RUST, width=2)
    draw.polygon([(975, 564), (975, 576), (985, 570)], fill=INK_RUST)
    
    img.save('assets/experience_competence_loop.jpg', quality=95)


def gen_three_layer():
    img = get_parchment_canvas(71)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXVIII: THREE-LAYER REALITY VERIFICATION PROTOCOL',
                      'HIERARCHICAL GROUNDING FROM DETERMINISTIC CODE TO AUDITOR JUDGMENT')
    
    layers = [
        ('LAYER 1: DETERMINISTIC ASSERTIONS', 'HIGHEST EPISTEMIC WEIGHT (EXIT 0 / REGEX / PREDICATES)', [
            ('• Shell exit codes (0 vs non-zero), process execution status, file existence checks', FONT_BODY_B, INK_DARK),
            ('• Deterministic regex parsing, database query integrity, PRAGMA assertions', FONT_BODY, INK_MID),
            ('• Properties: 0ms evaluation latency, 0 token cost, absolute veto authority over higher layers', FONT_BODY_B, INK_GREEN)
        ], INK_GREEN),
        ('LAYER 2: EMPIRICAL STATE VERIFICATION', 'REALITY DELTA AUDITING (POST-CONDITION STATE DIFF)', [
            ('• File content diffing, database row validation, network port responsiveness', FONT_BODY_B, INK_DARK),
            ('• Diffing actual observed system state against expected post-conditions', FONT_BODY, INK_MID),
            ('• Catches silent tool failures where exit code was 0 but no output artifact was created', FONT_BODY_B, INK_BLUE)
        ], INK_BLUE),
        ('LAYER 3: AUDITOR JUDGMENT', 'QUALITATIVE SEMANTIC REVIEW (INVOKED ONLY WHEN CODE CANNOT CHECK)', [
            ('• Independent Auditor sub-agent audits code completeness, elegance, and semantic alignment', FONT_BODY_B, INK_DARK),
            ('• Invoked ONLY when Layer 1 and Layer 2 deterministic checks cannot physically apply', FONT_BODY, INK_MID),
            ('• Invariant: Qualitative opinion can NEVER overturn a failed deterministic test', FONT_BODY_B, INK_RUST)
        ], INK_DARK),
    ]
    
    y = 135
    h = 135
    gap = 22
    
    for i, (title, sub, bullets, col) in enumerate(layers):
        cy = y + i * (h + gap)
        draw_card(draw, 70, cy, 1235, h, title, sub, bullets, border_color=col)
        if i < 2:
            draw_arrow_v(draw, 688, cy + h, cy + h + gap, color=col)
            
    draw_card(draw, 70, 610, 1235, 95, 'CORE INVARIANT: REALITY GETS THE FINAL VOTE', None, [
        ('Prompting tweaks cannot bypass empirical verification. If Layer 1 fails, the task is a failure regardless of LLM confidence.', FONT_BODY_B, INK_RUST),
        ('Every execution trace in `experience.db` requires empirical post-condition proof before competence weights update.', FONT_BODY, INK_MID)
    ], border_color=INK_RUST)
    
    img.save('assets/three_layer_verification_protocol.jpg', quality=95)


def gen_procedural_evolution():
    img = get_parchment_canvas(72)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXIX: PROCEDURAL LEARNING: NATIVE SKILL EVOLUTION',
                      'COMPILING REPEATED EMPIRICAL SUCCESSES INTO GOVERNED HERMES SKILLS')
    
    steps = [
        ('1. TRACE EXTRACTION', 'From experience.db', [
            '• Repeated successful traces',
            '• Parameter patterns captured',
            '• Verified empirical checks',
            '• Trigger: scripts/reflect.py',
            '• Trajectory abstraction pass',
            '• Identifies candidate heuristics',
            '',
            ('Source: experience.operations', FONT_CODE, INK_DARK),
            ('Criteria: Exit 0 & Count >= 3', FONT_CODE, INK_MID)
        ], INK_DARK),
        ('2. SKILL COMPILATION', 'Drafting SKILL.md Logic', [
            '• Draft SKILL.md in registry',
            '• Embeds deterministic CLI logic',
            '• Auto-generates test harness',
            '• Defines parameter schemas',
            '• Packages reusable workflow',
            '• Creates isolation boundary',
            '',
            ('Standard: YAML Frontmatter', FONT_CODE, INK_DARK),
            ('Harness: scripts/test_skill.py', FONT_CODE, INK_MID)
        ], INK_BLUE),
        ('3. BENCHMARK AUDIT', 'Sandbox Validation', [
            '• Isolated benchmark run',
            '• Must achieve >= 95% success',
            '• Stress-tested under failure',
            '• Auditor review gate pass',
            '• Regression suite execution',
            '• Verifies zero side-effects',
            '',
            ('Sandbox: Isolated Sub-Agent', FONT_CODE, INK_DARK),
            ('Target: Zero Regressions', FONT_CODE, INK_MID)
        ], INK_RUST),
        ('4. NATIVE PROMOTION', 'Added to skills/', [
            '• Promoted to active library',
            '• Added to 58 native skills',
            '• Loaded into agent discovery',
            '• System 1 fast-path enabled',
            '• Available across all profiles',
            '• Sub-second cached execution',
            '',
            ('Target: skills/<name>/', FONT_CODE, INK_DARK),
            ('Routing: Fast Path (<10ms)', FONT_CODE, INK_MID)
        ], INK_GREEN)
    ]
    
    card_w = 285
    start_x = 70
    gap = 25
    y = 150
    h = 440
    
    for i, (title, sub, bullets, col) in enumerate(steps):
        x = start_x + i * (card_w + gap)
        draw_card(draw, x, y, card_w, h, title, sub, bullets, border_color=col)
        if i < 3:
            ax1 = x + card_w
            ax2 = ax1 + gap
            ay = y + h // 2
            draw_arrow_h(draw, ax1, ax2, ay, color=col)
            draw.text((ax1 + 2, ay - 20), "Pass", fill=col, font=FONT_SMALL_B)
            
    draw_card(draw, 70, 615, 1235, 95, 'NO CUSTOM SKILL FOUNDRY INVARIANT', None, [
        ('Hermes Agent already has a battle-tested procedural skill standard (`skills/<name>/SKILL.md`).', FONT_BODY_B, INK_DARK),
        ('ToMi avoids proprietary lock-in by compiling directly into native Hermes skills, instantly usable by any profile.', FONT_BODY, INK_GREEN)
    ])
    
    img.save('assets/procedural_learning_evolution.jpg', quality=95)


def gen_procedural_loop():
    img = get_parchment_canvas(73)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXX: PROCEDURAL LEARNING CLOSED CYBERNETIC LOOP',
                      'ACT-R PROCEDURALIZATION: FROM DELIBERATIVE TRAJECTORIES TO COMPILED SKILLS')
    
    # 4 Quadrant Cards
    draw_card(draw, 70, 125, 410, 175, '1. DELIBERATIVE ROLLOUT', 'SYSTEM 2 TASK EXECUTION', [
        ('• Planner sub-agent generates execution DAG', FONT_BODY, INK_MID),
        ('• Multi-step tool calls dispatched sequentially', FONT_BODY, INK_MID),
        ('• High token overhead & conversational latency', FONT_BODY_B, INK_RUST),
        ('• Full execution trace logged to experience.db', FONT_BODY, INK_MID)
    ], border_color=INK_DARK)
    
    draw_card(draw, 896, 125, 410, 175, '2. REALITY VERIFICATION', 'THREE-LAYER POST-CONDITION CHECK', [
        ('• Layer 1: Deterministic assert (Exit 0, exists)', FONT_BODY_B, INK_GREEN),
        ('• Layer 2: Empirical state diff (DB rows, ports)', FONT_BODY, INK_BLUE),
        ('• Layer 3: Independent Auditor review', FONT_BODY, INK_MID),
        ('• Reality gets absolute veto before skill capture', FONT_BODY_B, INK_RUST)
    ], border_color=INK_GREEN)
    
    draw_card(draw, 896, 360, 410, 175, '3. EVIDENCE-GATED REFLECTION', 'TRIGGERED ON SURPRISE DELTA', [
        ('• Activated on command error or novel solution', FONT_BODY, INK_MID),
        ('• Extracts invariant workflow & parameters', FONT_BODY_B, INK_DARK),
        ('• Discards ephemeral noise & session tokens', FONT_BODY, INK_MID),
        ('• Drafts candidate SKILL.md specification', FONT_BODY_B, INK_BLUE)
    ], border_color=INK_RUST)
    
    draw_card(draw, 70, 360, 410, 175, '4. COMPILED SYSTEM 1 REUSE', 'DETERMINISTIC SKILL EXECUTION', [
        ('• Promoted to native skills/<name>/SKILL.md', FONT_BODY_B, INK_GREEN),
        ('• Replaces multi-turn planning with single run', FONT_BODY, INK_MID),
        ('• Sub-millisecond cognitive latency (<10ms)', FONT_BODY_B, INK_GREEN),
        ('• 100% test reproducibility across profiles', FONT_BODY, INK_MID)
    ], border_color=INK_BLUE)
    
    # Connecting Arrows
    draw_arrow_h(draw, 480, 896, 185, "1 -> 2: Verified Execution Trace", color=INK_DARK)
    draw_arrow_v(draw, 1101, 300, 360, "2 -> 3: Surprise Delta", color=INK_RUST)
    draw_arrow_h(draw, 896, 480, 480, "3 -> 4: Compile & Sandbox Validate", color=INK_BLUE)
    draw_arrow_v(draw, 275, 360, 300, "Fast Path (System 1)", color=INK_GREEN)
    
    # Central Engraved Cybernetic Core Medallion
    cx, cy = 688, 335
    r_outer = 105
    draw.ellipse([cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer], outline=INK_DARK, width=2)
    draw.ellipse([cx - r_outer + 4, cy - r_outer + 4, cx + r_outer - 4, cy + r_outer - 4], outline=INK_MID, width=1)
    
    # Degree Ticks
    for deg in range(0, 360, 10):
        rad = np.radians(deg)
        t_len = 8 if deg % 30 == 0 else 4
        x1 = cx + (r_outer - t_len) * np.cos(rad)
        y1 = cy + (r_outer - t_len) * np.sin(rad)
        x2 = cx + (r_outer - 2) * np.cos(rad)
        y2 = cy + (r_outer - 2) * np.sin(rad)
        draw.line([x1, y1, x2, y2], fill=INK_DARK, width=1 if deg % 30 != 0 else 2)
        
    draw.ellipse([cx - 76, cy - 76, cx + 76, cy + 76], outline=INK_MID, width=1)
    
    t1 = "CYBERNETIC CORE"
    tw1 = draw.textlength(t1, font=FONT_SECTION)
    draw.text((cx - tw1/2, cy - 42), t1, fill=INK_DARK, font=FONT_SECTION)
    
    t2 = "ACT-R Proceduralization"
    tw2 = draw.textlength(t2, font=FONT_BODY)
    draw.text((cx - tw2/2, cy - 14), t2, fill=INK_BLUE, font=FONT_BODY)
    
    t3 = "System 2  -->  System 1"
    tw3 = draw.textlength(t3, font=FONT_BODY_B)
    draw.text((cx - tw3/2, cy + 12), t3, fill=INK_GREEN, font=FONT_BODY_B)
    
    t4 = "Entropy Reduction"
    tw4 = draw.textlength(t4, font=FONT_SMALL)
    draw.text((cx - tw4/2, cy + 36), t4, fill=INK_MUTED, font=FONT_SMALL)
    
    draw_card(draw, 70, 555, 1235, 155, 'COGNITIVE ARCHITECTURE THEOREM: PROCEDURALIZATION ELIMINATES LATENCY', None, [
        ('• In John Anderson\'s ACT-R cognitive architecture, proceduralization converts slow, conscious declarative knowledge into fast production rules.', FONT_BODY, INK_MID),
        ('• In ToMi, repeated multi-step agent trajectories compile into native single-command Hermes skills.', FONT_BODY_B, INK_DARK),
        ('• Result: Multi-minute planning turns collapse into sub-millisecond deterministic skill runs with 100% test reproducibility.', FONT_BODY_B, INK_GREEN)
    ])
    
    img.save('assets/procedural_learning_loop.jpg', quality=95)


def gen_command_deck():
    img = get_parchment_canvas(74)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXXI: COMMAND DECK DASHBOARD ARCHITECTURE',
                      'EXECUTIVE OPERATIONS HUD AND SPATIAL COMPANION ADAPTERS (PORT 8088)')
    
    col_w = 590
    y = 135
    h = 470
    
    draw_card(draw, 70, y, col_w, h, 'FASTAPI & UVICORN BACKEND (:8088)', 'dashboard/dashboard_server.py (0.0.0.0 HOST BINDING)', [
        ('Core REST Endpoints:', FONT_BODY_B, INK_DARK),
        ('• /api/telemetry ──> Cognitive load, tokens & memory status', FONT_CODE, INK_MID),
        ('• /api/organizer ──> Deterministic CRUD tasks & deadlines (SQLite)', FONT_CODE, INK_MID),
        ('• /api/bots      ──> Multi-profile synchronization across 15 profiles', FONT_CODE, INK_MID),
        ('• /api/voice     ──> Local Speech-to-Speech WebRTC gateway (:8765)', FONT_CODE, INK_MID),
        ('• /api/search    ──> Second Brain reader across Active & Oracle wikis', FONT_CODE, INK_MID),
        ('• /api/decisions ──> Architecture decision ledger review & audit', FONT_CODE, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Backend Architecture Invariants:', FONT_BODY_B, INK_BLUE),
        ('• Asynchronous, low-latency Python ASGI engine', FONT_BODY, INK_MID),
        ('• Serves static assets on 0.0.0.0 for seamless LAN access', FONT_BODY, INK_MID),
        ('• Zero cloud dependencies: Connects to local SQLite & Postgres', FONT_BODY_B, INK_GREEN)
    ])
    
    draw_card(draw, 715, y, col_w, h, 'FRONTEND PRESENTATION DECK', 'index.html & app-bots.js (VANILLA JS, ZERO NODE BLOAT)', [
        ('Deck User Interface Modules:', FONT_BODY_B, INK_DARK),
        ('• Executive HUD: Memory tiers, system health, active profiles', FONT_BODY, INK_MID),
        ('• Multi-View Calendar: Tasks, renewals, reminders, project rings', FONT_BODY, INK_MID),
        ('• Second Brain Reader: Instant search & formatted markdown reader', FONT_BODY, INK_MID),
        ('• In-Deck Slide-Over Copilot: Direct conversational chat with Hermes', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Upstream Companion Adapters (Non-Invasive):', FONT_BODY_B, INK_DARK),
        ('• AI Visualizer (Port 8790): Reactive avatar face stage (Neural Core)', FONT_BODY_B, INK_BLUE),
        ('• Barehands 3D (Port 8794): Webcam spatial hand-tracking interface', FONT_BODY_B, INK_GREEN),
        ('', FONT_BODY, INK_MID),
        ('LAN Port Binding: Accessible at http://<host-lan-ip>:8088', FONT_BODY_B, INK_RUST)
    ])
    
    draw_card(draw, 70, 625, 1235, 85, 'ZERO CLOUD DEPENDENCY INVARIANT', None, [
        ('The Command Deck runs completely offline on your local network. No external CDNs, no tracking scripts, and no SaaS subscriptions.', FONT_BODY_B, INK_DARK)
    ])
    
    img.save('assets/command_deck_dashboard.jpg', quality=95)
    img.save('docs/assets/hermes_brain_dashboard.jpg', quality=95)


def gen_vm_topology():
    img = get_parchment_canvas(75)
    draw = ImageDraw.Draw(img)
    draw_master_frame(draw, 'PLATE XXXII: SELF-HOSTED VM & CONTAINER DEPLOYMENT TOPOLOGY',
                      'ISOLATED CONTAINER SERVICE TOPOLOGY AND DETERMINISTIC LOCAL FILE STORES')
    
    draw_card(draw, 70, 130, 1235, 460, 'HOST SYSTEM / PROXMOX HYPERVISOR (LAN: 10.1.1.x)', 'CONTAINERIZED ISOLATED MICROSERVICES')
    
    col_w = 560
    iy = 195
    ih = 370
    
    draw_card(draw, 95, iy, col_w, ih, 'CONTAINERIZED SERVICES & PORTS', 'ISOLATED DOCKER / PODMAN NETWORKS', [
        ('• Port 8088 ──> Command Deck Dashboard UI & REST API Gateway', FONT_CODE, INK_DARK),
        ('• Port 8000 ──> Honcho Autobiographical Memory Engine (Postgres)', FONT_CODE, INK_MID),
        ('• Port 5433 ──> PostgreSQL 18.6 (pgvector HNSW + ParadeDB BM25)', FONT_CODE, INK_BLUE),
        ('• Port 8080 ──> SearXNG Privacy Metasearch (70+ engines aggregated)', FONT_CODE, INK_MID),
        ('• Port 8790 ──> AI Visualizer (Procedural Avatar Stage: Neural Core)', FONT_CODE, INK_MID),
        ('• Port 8794 ──> Barehands 3D (Spatial Hand-Tracking Hologram)', FONT_CODE, INK_MID),
        ('• Port 8765 ──> S2S Speech-to-Speech Local Voice Container', FONT_CODE, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Networking: Strict localhost / private LAN isolation.', FONT_BODY_B, INK_GREEN)
    ])
    
    draw_card(draw, 720, iy, col_w, ih, 'DETERMINISTIC LOCAL FILE STORES', 'THE PERMANENT BEDROCK ON DISK', [
        ('1. ~/.hermes/personal-organizer/data/organizer.db', FONT_CODE, INK_DARK),
        ('   • Tasks, projects, deadlines, reminders, intentions (SQLite)', FONT_BODY, INK_MID),
        ('2. ~/.hermes/active-wiki/', FONT_CODE, INK_DARK),
        ('   • Hot Markdown corpus, active notes, [[wikilinks]]', FONT_BODY, INK_MID),
        ('3. ~/.hermes/oracle/brain/ & raw/', FONT_CODE, INK_DARK),
        ('   • Cold curated research vault & immutable raw logs', FONT_BODY, INK_MID),
        ('4. ~/.hermes/session.db', FONT_CODE, INK_DARK),
        ('   • Append-only Hermes conversation & tool execution transcripts', FONT_BODY, INK_MID),
        ('', FONT_BODY, INK_MID),
        ('Storage: Plain files & standard SQLite; survives container wipes.', FONT_BODY_B, INK_BLUE)
    ])
    
    draw_card(draw, 70, 610, 1235, 100, 'SECURITY & PRIVACY INVARIANT: COMPLETE LOCAL DATA SOVEREIGNTY', None, [
        ('• Zero data leaks: Conversations, personal tasks, and research vaults never leave local hardware.', FONT_BODY_B, INK_DARK),
        ('• Any container can be destroyed and restarted without data loss: persistent state lives strictly in mounted file stores.', FONT_BODY, INK_GREEN)
    ])
    
    img.save('assets/vm_deployment_topology.jpg', quality=95)


def main():
    print("Generating complete suite of 24 high-fidelity plates (Plates IX through XXXII)...")
    gen_retrieval_cascade()
    gen_oracle_pipeline()
    gen_additive_synthesis()
    gen_knowledge_lifecycle()
    gen_knowledge_reactivation()
    gen_durable_vs_rebuildable()
    gen_graphify_flow()
    gen_organizer_vs_kanban()
    gen_prospective_engine()
    gen_prospective_triggering()
    gen_epistemic_action_gate()
    gen_epistemic_lifecycle()
    gen_research_protocol()
    gen_planner_contract()
    gen_action_gate()
    gen_consequence_gated()
    gen_cognitive_modes()
    gen_metacognitive_routing()
    gen_experience_loop()
    gen_three_layer()
    gen_procedural_evolution()
    gen_procedural_loop()
    gen_command_deck()
    gen_vm_topology()
    print("All 24 plates generated successfully!")


if __name__ == '__main__':
    main()
