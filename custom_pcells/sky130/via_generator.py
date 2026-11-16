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
# via Generator for skywater130
########################################################################################################################

from math import ceil, floor
from .layers_def import *
import klayout.db as kdb

def add_native_rect(cell, xmin, ymin, xmax, ymax, layer_spec):
    """Bypasses gdsfactory validation and inserts fast native KLayout boxes."""
    layout = cell.layout() if hasattr(cell, 'layout') else cell.layout
    layer_idx = layout.layer(layer_spec[0], layer_spec[1])
    cell.shapes(layer_idx).insert(kdb.DBox(xmin, ymin, xmax, ymax))

class _VB:
    """Lightweight bounding box tracker to replace gf.Component references."""
    def __init__(self, x1, y1, x2, y2):
        self.xmin = x1; self.ymin = y1; self.xmax = x2; self.ymax = y2

def via_generator(
    cell,
    x_range = (0,1) ,
    y_range = (0,1) ,
    via_size = (0.17,0.17),
    via_layer = (66,44),
    via_enclosure = (0.06,0.06),
    via_spacing = (0.17,0.17)
):
    width = x_range[1] - x_range[0]
    length = y_range[1] - y_range[0]
    
    nr = floor(length / (via_size[1] + via_spacing[1]))
    if (length - nr*via_size[1] - (nr-1)*via_spacing[1])/2 < via_enclosure[1]: nr -= 1
    if nr < 1: nr = 1
    
    nc = ceil(width / (via_size[0]+via_spacing[0]))
    if (round(width - nc*via_size[0] - (nc-1)*via_spacing[0],2))/2 < via_enclosure[0]: nc -= 1
    if nc < 1: nc = 1 
    
    start_x = x_range[0] + (width - nc*via_size[0] - (nc-1)*via_spacing[0])/2
    start_y = y_range[0] + (length - nr*via_size[1] - (nr-1)*via_spacing[1])/2

    for i in range(nc):
        for j in range(nr):
            vx = start_x + i * (via_size[0] + via_spacing[0])
            vy = start_y + j * (via_size[1] + via_spacing[1])
            add_native_rect(cell, vx, vy, vx + via_size[0], vy + via_size[1], via_layer)

    end_x = start_x + (nc-1)*(via_size[0] + via_spacing[0]) + via_size[0]
    end_y = start_y + (nr-1)*(via_size[1] + via_spacing[1]) + via_size[1]
    return _VB(start_x, start_y, end_x, end_y)

def via_stack (
    cell,
    x_range = (0,1),
    y_range = (0,1),
    base_layer = diff_layer,
    slotted_licon = 0,
    metal_level = 1,
    li_enc_dir = "V"
):
    if slotted_licon == 1: licon_size = (0.19,2)
    else: licon_size = (0.17,0.17)
    
    mcon_size = (0.17,0.17)
    
    if base_layer == diff_layer or base_layer == tap_layer:
        con_enc = (0.06,0.06)
    elif base_layer == poly_layer:
        con_enc = (0.05,0.08)
        npc_enc = 0.01 
        add_native_rect(cell, x_range[0]-npc_enc, y_range[0]-npc_enc, x_range[1]+npc_enc, y_range[1]+npc_enc, npc_layer)
    else: 
        pass 

    if li_enc_dir == "H": li_enc, m1_enc = (0.08,0), (0.06,0.03)
    elif li_enc_dir == "V": li_enc, m1_enc = (0,0.08), (0.03,0.06)

    con_spacing = (0.19,0.19)
    via1_size, via1_spacing, via1_enc = (0.15,0.15), (0.17,0.17), (0.055,0.085)
    via2_size, via2_spacing, via2_enc = (0.2,0.2), (0.2,0.2), (0.04,0.085)
    via3_size, via3_spacing, via3_enc = (0.2,0.2), (0.2,0.2), (0.06,0.09)
    via4_size, via4_spacing, via4_enc = (0.8,0.8), (0.8,0.8), (0.19,0.19)

    if metal_level >= 0:
        licon = via_generator(cell, x_range=x_range,y_range=y_range,via_size=licon_size,via_enclosure=con_enc,via_layer=licon_layer,via_spacing=con_spacing)
        add_native_rect(cell, licon.xmin-li_enc[0], licon.ymin-li_enc[1], licon.xmax+li_enc[0], licon.ymax+li_enc[1], li_layer)

    if metal_level >= 1:
        mcon = via_generator(cell, x_range=x_range,y_range=y_range,via_size=mcon_size,via_enclosure=con_enc,via_layer=mcon_layer,via_spacing=con_spacing)
        
        m1_x = via1_size[0] + 2*via1_enc[0] if (mcon.xmax-mcon.xmin + 2*m1_enc[0]) < (via1_size[0] + 2*via1_enc[0]) and metal_level >=2 else mcon.xmax-mcon.xmin + 2*m1_enc[0]
        m1_y = via1_size[1] + 2*via1_enc[1] if (mcon.ymax-mcon.ymin + 2*m1_enc[1]) < (via1_size[1] + 2*via1_enc[1]) and metal_level >=2 else mcon.ymax-mcon.ymin + 2*m1_enc[1]
        
        m1_a = 0.084
        if (m1_x*m1_y) < m1_a: m1_x = m1_a/m1_y
        
        m1_mx = (m1_x - (mcon.xmax - mcon.xmin))/2
        m1_my = (m1_y - (mcon.ymax - mcon.ymin))/2

        m1_xmin, m1_ymin = mcon.xmin - m1_mx, mcon.ymin - m1_my
        m1_xmax, m1_ymax = m1_xmin + m1_x, m1_ymin + m1_y
        add_native_rect(cell, m1_xmin, m1_ymin, m1_xmax, m1_ymax, m1_layer)

    if metal_level >= 2:
        via1 = via_generator(cell, x_range=(m1_xmin, m1_xmax), y_range=(m1_ymin, m1_ymax),via_size=via1_size,via_enclosure=via1_enc,via_layer=via1_layer,via_spacing=via1_spacing)

        m2_enc = (0.055,0.085) if (via1.xmax-via1.xmin) > (via1.ymax - via1.ymin) else (0.085,0.055)
        m2_x = via2_size[0] + 2*via2_enc[0] if (via1.xmax-via1.xmin + 2*m2_enc[0]) < (via2_size[0] + 2*via2_enc[0]) and metal_level >=3 else via1.xmax-via1.xmin + 2*m2_enc[0]
        m2_y = via2_size[1] + 2*via2_enc[1] if (via1.ymax-via1.ymin + 2*m2_enc[1]) < (via2_size[1] + 2*via2_enc[1]) and metal_level >=3 else via1.ymax-via1.ymin + 2*m2_enc[1]
            
        m2_mx = (m2_x - (via1.xmax - via1.xmin))/2
        m2_my = (m2_y - (via1.ymax - via1.ymin))/2

        m2_xmin, m2_ymin = via1.xmin - m2_mx, via1.ymin - m2_my
        m2_xmax, m2_ymax = m2_xmin + m2_x, m2_ymin + m2_y
        add_native_rect(cell, m2_xmin, m2_ymin, m2_xmax, m2_ymax, m2_layer)
    
    if metal_level >= 3: 
        via2 = via_generator(cell, x_range=(m2_xmin, m2_xmax), y_range=(m2_ymin, m2_ymax),via_size=via2_size,via_enclosure=via2_enc,via_layer=via2_layer,via_spacing=via2_spacing)

        m3_enc = (0.065,0.065)
        m3_x = via3_size[0] + 2*via3_enc[0] if (via2.xmax-via2.xmin + 2*m3_enc[0]) < (via3_size[0] + 2*via3_enc[0]) and metal_level >= 4 else via2.xmax-via2.xmin + 2*m3_enc[0]
        m3_y = via3_size[1] + 2*via3_enc[1] if (via2.ymax-via2.ymin + 2*m3_enc[1]) < (via3_size[1] + 2*via3_enc[1]) and metal_level >= 4 else via2.ymax-via2.ymin + 2*m3_enc[1]
            
        m3_mx = (m3_x - (via2.xmax - via2.xmin))/2
        m3_my = (m3_y - (via2.ymax - via2.ymin))/2
        
        m3_xmin, m3_ymin = via2.xmin - m3_mx, via2.ymin - m3_my
        m3_xmax, m3_ymax = m3_xmin + m3_x, m3_ymin + m3_y
        add_native_rect(cell, m3_xmin, m3_ymin, m3_xmax, m3_ymax, m3_layer)

    if metal_level >= 4: 
        via3 = via_generator(cell, x_range=(m3_xmin, m3_xmax), y_range=(m3_ymin, m3_ymax),via_size=via3_size,via_enclosure=via3_enc,via_layer=via3_layer,via_spacing=via3_spacing)

        m4_enc = (0.065,0.065)
        m4_x = via4_size[0] + 2*via4_enc[0] if (via3.xmax-via3.xmin + 2*m4_enc[0]) < (via4_size[0] + 2*via4_enc[0]) and metal_level >=5 else via3.xmax-via3.xmin + 2*m4_enc[0]
        m4_y = via4_size[1] + 2*via4_enc[1] if (via3.ymax-via3.ymin + 2*m4_enc[1]) < (via4_size[1] + 2*via4_enc[1]) and metal_level >=5 else via3.ymax-via3.ymin + 2*m4_enc[1]
            
        m4_mx =  (m4_x- (via3.xmax - via3.xmin))/2
        m4_my =  (m4_y- (via3.ymax - via3.ymin))/2
        
        m4_xmin, m4_ymin = via3.xmin-m4_mx, via3.ymin- m4_my
        m4_xmax, m4_ymax = m4_xmin + m4_x, m4_ymin + m4_y
        add_native_rect(cell, m4_xmin, m4_ymin, m4_xmax, m4_ymax, m4_layer)

    if metal_level >= 5: 
        via4 = via_generator(cell, x_range=(m4_xmin, m4_xmax), y_range=(m4_ymin, m4_ymax),via_size=via4_size,via_enclosure=via4_enc,via_layer=via4_layer,via_spacing=via4_spacing)

        m5_enc, m5_min_w = (0.31,0.31), 1.6 
        m5_x = m5_min_w if (via4.xmax-via4.xmin + 2*m5_enc[0]) < m5_min_w else via4.xmax-via4.xmin + 2*m5_enc[0]
        m5_y = m5_min_w if (via4.ymax-via4.ymin + 2*m5_enc[1]) < m5_min_w else via4.ymax-via4.ymin + 2*m5_enc[1]

        m5_a = 4 
        if (m5_x*m5_y) < m5_a: m5_x = m5_a/m5_y
        
        m5_mx = (m5_x - (via4.xmax - via4.xmin))/2
        m5_my =  (m5_y - (via4.ymax - via4.ymin))/2

        add_native_rect(cell, via4.xmin - m5_mx, via4.ymin - m5_my, via4.xmin - m5_mx + m5_x, via4.ymin - m5_my + m5_y, m5_layer)


def vias_gen_draw(
    cell,
    l : float = 1.0,
    w : float = 1.0,
    start_layer = "poly",
    end_layer = "metal5"
):
    base_layers = ["poly","n_diff","p_diff","n_tap","p_tap"]
    metal_layers = ["li","metal1","metal2","metal3","metal4","metal5"]

    level_1 = -1 if start_layer in base_layers else metal_layers.index(start_layer) if start_layer in metal_layers else -1
    level_2 = -1 if end_layer in base_layers else metal_layers.index(end_layer) if end_layer in metal_layers else -1
    
    if level_1 <= -1 and level_2 >= -1:
        if start_layer == "poly" or end_layer == "poly":
            npc_enc = 0.05
            add_native_rect(cell, 0, 0, l, w, poly_layer)
            add_native_rect(cell, -npc_enc, -npc_enc, l+npc_enc, w+npc_enc, npc_layer)
        if "diff" in start_layer or "diff" in end_layer:
            n_p_enc, nwell_enc = 0.125, 0.18
            add_native_rect(cell, 0, 0, l, w, diff_layer)
            if "n_" in start_layer or "n_" in end_layer:
                add_native_rect(cell, -n_p_enc, -n_p_enc, l+n_p_enc, w+n_p_enc, nsdm_layer)
            else:
                add_native_rect(cell, -n_p_enc, -n_p_enc, l+n_p_enc, w+n_p_enc, psdm_layer)
                add_native_rect(cell, -nwell_enc, -nwell_enc, l+nwell_enc, w+nwell_enc, nwell_layer)
        if "tap" in start_layer or "tap" in end_layer:
            n_p_enc, nwell_enc = 0.125, 0.18
            add_native_rect(cell, 0, 0, l, w, tap_layer)
            if "n_" in start_layer or "n_" in end_layer:
                add_native_rect(cell, -n_p_enc, -n_p_enc, l+n_p_enc, w+n_p_enc, nsdm_layer)
                add_native_rect(cell, -nwell_enc, -nwell_enc, l+nwell_enc, w+nwell_enc, nwell_layer)
            else:
                add_native_rect(cell, -n_p_enc, -n_p_enc, l+n_p_enc, w+n_p_enc, psdm_layer)

    if level_1 <= 0 and level_2 >= 0: add_native_rect(cell, 0, 0, l, w, li_layer)
    if level_1 <= 1 and level_2 >= 1: add_native_rect(cell, 0, 0, l, w, m1_layer)
    if level_1 <= 2 and level_2 >= 2: add_native_rect(cell, 0, 0, l, w, m2_layer)
    if level_1 <= 3 and level_2 >= 3: add_native_rect(cell, 0, 0, l, w, m3_layer)
    if level_1 <= 4 and level_2 >= 4: add_native_rect(cell, 0, 0, l, w, m4_layer)
    if level_1 <= 5 and level_2 >= 5: add_native_rect(cell, 0, 0, l, w, m5_layer)

    if level_1 <= -1 and level_2 > -1:
        licon_size, licon_spacing = (0.17,0.17), (0.17,0.17)
        if start_layer == "poly": licon_enc = (0.08,0.05)
        else: licon_enc = (0.12,0.06)
        via_generator(cell, x_range=(0,l),y_range=(0,w),via_size=licon_size,via_layer=licon_layer,via_enclosure=licon_enc,via_spacing=licon_spacing)
 
    if level_1 <= 0 and level_2 > 0:
        mcon_size, mcon_enc, mcon_spacing = (0.17,0.17), (0.06,0.03), (0.19,0.19)
        via_generator(cell, x_range=(0,l),y_range=(0,w),via_size=mcon_size,via_layer=mcon_layer,via_enclosure=mcon_enc,via_spacing=mcon_spacing)

    if level_1 <= 1 and level_2 > 1:
        via1_size, via1_enc, via1_spacing = (0.15,0.15), (0.085,0.055), (0.17,0.17)
        via_generator(cell, x_range=(0,l),y_range=(0,w),via_size=via1_size,via_layer=via1_layer,via_enclosure=via1_enc,via_spacing=via1_spacing)

    if level_1 <= 2 and level_2 > 2:
        via2_size, via2_enc, via2_spacing = (0.2,0.2), (0.085,0.065), (0.2,0.2)
        via_generator(cell, x_range=(0,l),y_range=(0,w),via_size=via2_size,via_layer=via2_layer,via_enclosure=via2_enc,via_spacing=via2_spacing)

    if level_1 <= 3 and level_2 > 3:
        via3_size, via3_enc, via3_spacing = (0.2,0.2), (0.09,0.065), (0.2,0.2)
        via_generator(cell, x_range=(0,l),y_range=(0,w),via_size=via3_size,via_layer=via3_layer,via_enclosure=via3_enc,via_spacing=via3_spacing)

    if level_1 <= 4 and level_2 > 4:
        via4_size, via4_enc, via4_spacing = (0.8,0.8), (0.31,0.31), (0.8,0.8)
        via_generator(cell, x_range=(0,l),y_range=(0,w),via_size=via4_size,via_layer=via4_layer,via_enclosure=via4_enc,via_spacing=via4_spacing)