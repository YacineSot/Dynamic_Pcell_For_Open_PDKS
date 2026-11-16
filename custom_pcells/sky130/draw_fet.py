# Copyright 2022 Mabrains LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

########################################################################################################################
## Mosfets Pcells Generators for Klayout of skywater130
########################################################################################################################

from math import ceil, floor
import gdsfactory as gf
from .layers_def import *
from .pdk import take_component
from .draw_guard_ring import draw_gr
from .via_generator import *
import klayout.db as kdb
import uuid

def draw_fet(
    cell,
    l: float = 0.15,
    w: float = 0.42,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.3,
    nf: int = 1, 
    grw: float = 0.17,
    type: str = "sky130_fd_pr__nfet_01v8",
    bulk: str = "None",
    con_bet_fin: int = 1,
    gate_con_pos: str = "alternating",
    interdig: int = 0,
    patt: str = "",
    gr_shape: str = "", 
    gr_distances: tuple = (0.32,0.27),
    contacts_ratios: tuple = (80,80),
    contacts_levels: tuple = (0, 0)
):
    dev_type = 'pfet' if 'pfet' in type.lower() else 'nfet'

    # Native KLayout Geometry Helpers (Bypasses all GDSFactory Validation Overhead)
    def add_rect(xmin, ymin, xmax, ymax, layer_spec):
        layer_idx = cell.layout().layer(layer_spec[0], layer_spec[1])
        cell.shapes(layer_idx).insert(kdb.DBox(xmin, ymin, xmax, ymax))

    def add_label(text, x, y, layer_spec):
        layer_idx = cell.layout().layer(layer_spec[0], layer_spec[1])
        cell.shapes(layer_idx).insert(kdb.DText(text, kdb.DTrans(kdb.DTrans.R0, x, y)))

    # Base Dimensions & Enclosures
    end_cap, diff_tap_spacing, poly_tap_spacing = 0.2, gr_distances[0], gr_distances[1]
    diff_sdm_enc, tap_sdm_enc = 0.125, 0.125
    gate_npc_ext, npc_spacing = 0.11, 0
    gate_lvt_enc, gate_hvt_enc = 0.18, 0.18
    hv_enclosing, nwell_enclosing, areaid_lvn_enc = 0.185, 0.18, 0.1
    
    if type == "sky130_fd_pr__pfet_g5v0d10v5": nwell_enclosing = 0.34

    licon_size, licon_spacing, licon_dt_enc, licon_p_enc = (0.17,0.17), (0.19,0.19), (0.04,0.06), (0.05,0.08)
    sd_l_con = ((sd_con_col)*licon_size[0]) + ((sd_con_col-1)*licon_spacing[0]) + 2*licon_dt_enc[0]
    sd_l = sd_l_con + 0.05

    if dev_type == 'pfet':
        diff_implant, tap_implant, has_nwell = psdm_layer, nsdm_layer, True
    else:
        diff_implant, tap_implant, has_nwell = nsdm_layer, psdm_layer, False

    # Container solely for vias (keeps gf isolated from pure rectangles)
    unique_id = uuid.uuid4().hex[:8]
    via_container = gf.Component(f"via_container_{unique_id}")

    # ---------------------------------------------------------
    # 1. GENERATE DIFFUSION & CONTACTS
    # ---------------------------------------------------------
    interdig = interdig and len(patt)
    ng = len(patt) if (interdig and patt) else nf
    l_d = sd_l + ng*l + (ng-1)*inter_sd_l + sd_l 
    
    add_rect(0, 0, l_d, w, diff_layer)

    contacts_w = w * contacts_ratios[0]/100
    cont_offset = (w - contacts_w)/2
    
    # Outer Source/Drain Contacts
    via_stack(cell, x_range=(sd_l/2 - sd_l_con/2, sd_l/2 + sd_l_con/2), y_range=(cont_offset, contacts_w + cont_offset), base_layer=diff_layer, metal_level=contacts_levels[0])
    via_stack(cell, x_range=(l_d - (sd_l/2) - sd_l_con/2, l_d - (sd_l/2) + sd_l_con/2), y_range=(cont_offset, contacts_w + cont_offset), base_layer=diff_layer, metal_level=contacts_levels[0])
    
    # Inner Source/Drain Contacts
    if con_bet_fin == 1 and ng > 1: 
        for i in range(ng - 1):
            cx = sd_l + l + i*(l + inter_sd_l) + inter_sd_l/2
            via_stack(cell, x_range=(cx - inter_sd_l/2, cx + inter_sd_l/2), y_range=(cont_offset, contacts_w + cont_offset), base_layer=diff_layer, metal_level=contacts_levels[0])
    
    # ---------------------------------------------------------
    # 2. UNIFIED POLY & INTERDIGITATION
    # ---------------------------------------------------------
    pc_x = licon_p_enc[0] + licon_size[0] + licon_p_enc[0] if (l <= licon_size[0] + 2*licon_p_enc[0]) else l
    pc_x = pc_x * contacts_ratios[1] / 100
    pc_y = licon_p_enc[1] + licon_size[1] + licon_p_enc[1]

    pat = list(patt) if len(patt) >= ng else [patt[0] if patt else 'G']*ng
    route_cfg = {"top": "none", "bottom": "none"}
    
    if gate_con_pos == "none": pass
    elif gate_con_pos == "top": route_cfg["top"] = "all"
    elif gate_con_pos == "bottom": route_cfg["bottom"] = "all"
    elif gate_con_pos == "alternating" and ng > 1: route_cfg["top"], route_cfg["bottom"] = "odd", "even"
    else: route_cfg["top"], route_cfg["bottom"] = "all", "all"

    def check_active(cfg_val, idx):
        if cfg_val == "none": return False
        if cfg_val == "all": return True
        return (idx % 2 == 0) if cfg_val == "even" else (idx % 2 != 0)

    def get_contact_y(idx, is_top):
        stagger = (inter_sd_l < npc_spacing + 2*gate_npc_ext)
        if is_top:
            base_y = w + end_cap
            if stagger: return base_y + 0.2 if gate_con_pos == "alternating" else (base_y if idx % 2 == 0 else base_y + pc_y + npc_spacing + 0.1)
            return base_y
        else:
            base_y = -end_cap - pc_y
            if stagger: return base_y - 0.2 if gate_con_pos == "alternating" else (base_y if idx % 2 == 0 else base_y - (pc_y + npc_spacing + 0.1))
            return base_y

    top_signals, bot_signals = [], []
    for i in range(ng):
        if check_active(route_cfg["top"], i) and pat[i] not in top_signals: top_signals.append(pat[i])
        if check_active(route_cfg["bottom"], i) and pat[i] not in bot_signals: bot_signals.append(pat[i])

    m2_spacing, m2_y = 0.14, 0.15 + 2*0.055 
    via1_size, via1_enc, via1_spacing = (0.15,0.15), (0.085,0.055), (0.17,0.17)

    pc_cy_top_max = max((get_contact_y(i, True) for i in range(ng) if check_active(route_cfg["top"], i)), default=w + end_cap)
    pc_cy_bot_min = min((get_contact_y(i, False) for i in range(ng) if check_active(route_cfg["bottom"], i)), default=-end_cap)
    
    base_m2_y_top = pc_cy_top_max + pc_y + 0.06 + m2_spacing
    base_m2_y_bot = pc_cy_bot_min - 0.06 - m2_spacing - m2_y

    # Horizontal M2 Buses
    if interdig and top_signals:
        for row in range(len(top_signals)):
            y_start = base_m2_y_top + row * (m2_y + m2_spacing)
            add_rect(0, y_start, l_d, y_start + m2_y, m2_layer)
            
    if interdig and bot_signals:
        for row in range(len(bot_signals)):
            y_start = base_m2_y_bot - row * (m2_y + m2_spacing)
            add_rect(0, y_start, l_d, y_start + m2_y, m2_layer)

    # THE SINGLE LOOP
    for i in range(ng):
        poly_x = sd_l + i*(l + inter_sd_l)
        poly_x_center = poly_x + l/2
        poly_y_min, poly_y_max = -end_cap, w + end_cap
        
        if check_active(route_cfg["top"], i):
            cy = get_contact_y(i, True)
            poly_y_max = cy + pc_y
            
            # Gate Rectangle + Via
            add_rect(poly_x_center - pc_x/2, cy, poly_x_center + pc_x/2, cy + pc_y, poly_layer)
            via_stack(cell, x_range=(poly_x_center - pc_x/2, poly_x_center + pc_x/2), y_range=(cy, cy + pc_y), base_layer=poly_layer, metal_level=contacts_levels[1], li_enc_dir="H")
            
            if interdig:
                m1_ymin = cy + 0.06
                m1_ymax = base_m2_y_top + top_signals.index(pat[i])*(m2_y+m2_spacing) + m2_y
                add_rect(poly_x_center - pc_x/2, m1_ymin, poly_x_center + pc_x/2, m1_ymax, m1_layer)
                via_generator(x_range=(poly_x_center - pc_x/2, poly_x_center + pc_x/2), y_range=(m1_ymax - m2_y, m1_ymax), via_enclosure=via1_enc, via_layer=via1_layer, via_size=via1_size, via_spacing=via1_spacing)
                add_label(f"{pat[i]}", poly_x_center, m1_ymax - m2_y/2, m1_lbl)
                
        if check_active(route_cfg["bottom"], i):
            cy = get_contact_y(i, False)
            poly_y_min = cy
            
            # Gate Rectangle + Via
            add_rect(poly_x_center - pc_x/2, cy, poly_x_center + pc_x/2, cy + pc_y, poly_layer)
            via_stack(cell, x_range=(poly_x_center - pc_x/2, poly_x_center + pc_x/2), y_range=(cy, cy + pc_y), base_layer=poly_layer, metal_level=contacts_levels[1], li_enc_dir="H")
            
            if interdig:
                m1_ymax = cy + pc_y - 0.06
                m1_ymin = base_m2_y_bot - bot_signals.index(pat[i])*(m2_y+m2_spacing)
                add_rect(poly_x_center - pc_x/2, m1_ymin, poly_x_center + pc_x/2, m1_ymax, m1_layer)
                via_generator(x_range=(poly_x_center - pc_x/2, poly_x_center + pc_x/2), y_range=(m1_ymin, m1_ymin + m2_y), via_enclosure=via1_enc, via_layer=via1_layer, via_size=via1_size, via_spacing=via1_spacing)
                add_label(f"{pat[i]}", poly_x_center, m1_ymin + m2_y/2, m1_lbl)
                
        # Main Poly gate body
        add_rect(poly_x, poly_y_min, poly_x + l, poly_y_max, poly_layer)

    # M3 Jumpers (bridges top and bottom buses if signals match)
    if interdig and gate_con_pos == "alternating":
        m3_x, m3_spacing = 0.15 + 2*0.085, 0.3 
        for i, sig_b in enumerate(bot_signals):
            if sig_b in top_signals:
                j = top_signals.index(sig_b)
                join_w = m2_y + (i+1)*(m3_spacing+m3_x)
                
                m2_join_b_ymin = base_m2_y_bot - i*(m2_spacing+m2_y)
                m2_join_u_ymin = base_m2_y_top + j*(m2_spacing+m2_y)
                
                add_rect(0 - join_w, m2_join_b_ymin, 0, m2_join_b_ymin + m2_y, m2_layer)
                add_rect(0 - join_w, m2_join_u_ymin, 0, m2_join_u_ymin + m2_y, m2_layer)
                add_rect(0 - join_w, m2_join_b_ymin, 0 - join_w + m3_x, m2_join_u_ymin + m2_y, m1_layer)
                
                # M1->M2 Vias at jumper edges
                via_generator(x_range=(0 - join_w, 0 - join_w + m3_x), y_range=(m2_join_u_ymin, m2_join_u_ymin + m2_y), via_enclosure=via1_enc, via_size=via1_size, via_layer=via1_layer, via_spacing=via1_spacing)
                via_generator(x_range=(0 - join_w, 0 - join_w + m3_x), y_range=(m2_join_b_ymin, m2_join_b_ymin + m2_y), via_enclosure=via1_enc, via_size=via1_size, via_layer=via1_layer, via_spacing=via1_spacing)

    # ---------------------------------------------------------
    # 3. BULK / GUARD RING TIES
    # ---------------------------------------------------------
    if bulk == "None":
        add_rect(-diff_sdm_enc, -diff_sdm_enc, l_d + diff_sdm_enc, w + diff_sdm_enc, diff_implant)
    elif bulk == "bulk tie":
        rb_w = 1.5*sd_l if dev_type=='nfet' else 1.3*sd_l
        add_rect(-rb_w, 0, 0, w, tap_layer)
        add_rect(-diff_sdm_enc, -diff_sdm_enc, l_d + diff_sdm_enc, w + diff_sdm_enc, diff_implant)
        
        if dev_type == 'nfet':
            add_rect(-rb_w - tap_sdm_enc, -tap_sdm_enc, -diff_sdm_enc, w + tap_sdm_enc, tap_implant)
        else:
            add_rect(-rb_w - tap_sdm_enc, -tap_sdm_enc, 0 + tap_sdm_enc, w + tap_sdm_enc, tap_implant)
            
        via_stack(cell, x_range=(-rb_w+0.1, -0.1), y_range=(0, w), base_layer=tap_layer, metal_level=0)
    elif bulk == "guard ring":
        add_rect(-diff_sdm_enc, -diff_sdm_enc, l_d + diff_sdm_enc, w + diff_sdm_enc, diff_implant)

    # Convert the remaining GF Vias immediately to native geometry
    via_container.flatten()
    take_component(via_container, cell)

    # ---------------------------------------------------------
    # 4. VOLTAGE & WELL IMPLANTS
    # ---------------------------------------------------------
    # Rapid bounds calculation directly from the native cell (fast)
    bbox = cell.dbbox()
    c_inst_xmin, c_inst_ymin = bbox.left, bbox.bottom
    c_inst_xmax, c_inst_ymax = bbox.right, bbox.top

    if has_nwell:
        add_rect(c_inst_xmin - nwell_enclosing, c_inst_ymin - nwell_enclosing, c_inst_xmax + nwell_enclosing, c_inst_ymax + nwell_enclosing, nwell_layer)
    # elif has_nwell and bulk == "guard ring":
    #     nwell_xmin, nwell_ymin = c_inst_xmin - diff_tap_spacing - grw - tap_sdm_enc - nwell_enclosing, c_inst_ymin - poly_tap_spacing - grw - tap_sdm_enc - nwell_enclosing
    #     nwell_xmax, nwell_ymax = c_inst_xmax + diff_tap_spacing + grw + tap_sdm_enc + nwell_enclosing, c_inst_ymax + poly_tap_spacing + grw + tap_sdm_enc + nwell_enclosing
    #     add_rect(nwell_xmin, nwell_ymin, nwell_xmax, nwell_ymax, nwell_layer)

    if type.endswith(("01v8_lvt", "03v3_nvt", "05v0_nvt")):
        add_rect(sd_l-gate_lvt_enc, -gate_lvt_enc, sd_l + ng*l+(ng-1)*inter_sd_l + gate_lvt_enc, w+gate_lvt_enc, lvtn_layer)
        if type.endswith("03v3_nvt"):
            for i in range(ng):
                add_rect(sd_l + i*(l+inter_sd_l) - areaid_lvn_enc, -areaid_lvn_enc, sd_l + i*(l+inter_sd_l) + l + areaid_lvn_enc, w + areaid_lvn_enc, areaid_lvn_layer)
    if type.endswith("01v8_hvt"):
        add_rect(sd_l-gate_hvt_enc, -gate_hvt_enc, sd_l + ng*l+(ng-1)*inter_sd_l + gate_hvt_enc, w+gate_hvt_enc, hvtp_layer)

    has_hvi = type in ["sky130_fd_pr__nfet_g5v0d10v5", "sky130_fd_pr__nfet_05v0_nvt", "sky130_fd_pr__nfet_03v3_nvt", "sky130_fd_pr__pfet_g5v0d10v5"]
    if has_hvi:
        hvi_xmin, hvi_ymin = c_inst_xmin - hv_enclosing, c_inst_ymin - hv_enclosing
        hvi_xmax, hvi_ymax = c_inst_xmax + hv_enclosing, c_inst_ymax + hv_enclosing
        
        add_rect(hvi_xmin, hvi_ymin, hvi_xmax, hvi_ymax, hvi_layer)
        if dev_type == 'nfet':
            add_rect(0-hv_enclosing, 0-hv_enclosing, l_d+hv_enclosing, w+hv_enclosing, hvntm_layer)

    # ---------------------------------------------------------
    # 5. GUARD RING INTEGRATION
    # ---------------------------------------------------------
    if bulk == "guard ring":
        activ_box = next(cell.shapes(cell.layout().layer(diff_layer[0], diff_layer[1])).each(), None).dbbox()
        
        xmax, xmin, ymax, ymin = activ_box.right, activ_box.left, activ_box.top, activ_box.bottom
        cell_center = activ_box.center()
        in_w = (xmax - xmin) + 2*diff_tap_spacing
        in_l = (ymax - ymin) + 2*poly_tap_spacing
        
        gr_cell_name = f"temp_gr_{cell.name}"
        gr_cell = cell.layout().create_cell(gr_cell_name)
        
        draw_gr(gr_cell, in_l=in_l, in_w=in_w, grw=grw, con_lev="li", implant_type="nsdm" if dev_type=='pfet' else "psdm", shape=gr_shape, origin="centerCenter")
        
        trans = kdb.DTrans(cell_center)
        
        for layer in gr_cell.layout().layer_indexes():
            for shape in gr_cell.shapes(layer).each():
                cell.shapes(layer).insert(shape, trans)
        
        cell.layout().delete_cell(gr_cell.cell_index())
        bbox = cell.dbbox()
        c_inst_xmin, c_inst_ymin = bbox.left, bbox.bottom
        c_inst_xmax, c_inst_ymax = bbox.right, bbox.top
        if has_nwell:
            cell.shapes(nwell_layer).clear()
            cell.shapes(hvi_layer).clear()
            cell.shapes(hvntm_layer).clear()
            add_rect(c_inst_xmin - nwell_enclosing, c_inst_ymin - nwell_enclosing, c_inst_xmax + nwell_enclosing, c_inst_ymax + nwell_enclosing, nwell_layer)
        if has_hvi:
            hvi_xmin, hvi_ymin = c_inst_xmin - hv_enclosing, c_inst_ymin - hv_enclosing
            hvi_xmax, hvi_ymax = c_inst_xmax + hv_enclosing, c_inst_ymax + hv_enclosing
            
            add_rect(hvi_xmin, hvi_ymin, hvi_xmax, hvi_ymax, hvi_layer)
            if dev_type == 'nfet':
                add_rect(0-hv_enclosing, 0-hv_enclosing, l_d+hv_enclosing, w+hv_enclosing, hvntm_layer)
    
