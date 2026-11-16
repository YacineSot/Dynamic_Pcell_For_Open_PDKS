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
## Guard Ring Pcells Generators for Klayout of skywater130
########################################################################################################################


from .via_generator import *
from .globals import *
from .layers_def import *
import gdsfactory as gf
from .pdk import open_component, take_component
import klayout.db as kdb

def draw_gr (
    cell,
    in_l : float = 1,
    in_w : float = 1,
    grw : float = 0.17,
    con_lev = "li",
    implant_type = "None",
    shape="nsew", 
    origin="centerCenter"
) :

    '''
    cell : kdb.Cell cell to place layout into
    in_l : float of the inner length of the ring
    in_w : float of the inner width of the ring 
    grw : float of the guard ring width 
    con_lev : connection level of (li, metal1)
    shape: shape of the guard ring (nsew, ns, ew)
    '''

    con_size = (0.17,0.17)
    con_spacing = (0.19, 0.19)
    con_enc = (0.12, 0.12)

    tap_nsdm_enc : float = 0.125
    tap_psdm_enc : float = 0.125

    c = open_component("sky_ring_gen")
    
    # temp_store and boolean A-B logic have been removed for efficiency and side-selectability.
    ## fix shape to include at least bottom side
    if not shape:
        shape='s'

    # Choose the implant
    if implant_type == 'nsdm':
        implant_layer = nsdm_layer
    if implant_type == 'psdm':
        implant_layer = psdm_layer
    
    imp_out_xmin = left = -grw - tap_nsdm_enc
    imp_out_xmax = right = in_w + grw + tap_nsdm_enc
    imp_out_ymin = bottom = -grw - tap_nsdm_enc
    imp_out_ymax = top = in_l + grw + tap_nsdm_enc
    
    imp_in_xmin = tap_nsdm_enc
    imp_in_xmax = in_w - tap_nsdm_enc
    imp_in_ymin = tap_nsdm_enc
    imp_in_ymax = in_l - tap_nsdm_enc
    
    calculated_width = imp_out_xmax - imp_out_xmin
    calculated_height = imp_out_ymax- imp_out_ymin
    
    # ---------------------------------------------------------
    # 1. IMPLANT LAYER
    # ---------------------------------------------------------
    if implant_type != 'None':
        # Calculate explicit inner and outer boundaries for the implant
        
        # Draw explicitly selected sides directly to `c`
        if 'w' in shape:
            w_rect = c.add_ref(gf.components.rectangle(size=(imp_in_xmin - imp_out_xmin, imp_out_ymax - imp_out_ymin), layer=implant_layer))
            w_rect.move((imp_out_xmin, imp_out_ymin))
        if 'e' in shape:
            e_rect = c.add_ref(gf.components.rectangle(size=(imp_out_xmax - imp_in_xmax, imp_out_ymax - imp_out_ymin), layer=implant_layer))
            e_rect.move((imp_in_xmax, imp_out_ymin))
        if 's' in shape:
            s_rect = c.add_ref(gf.components.rectangle(size=(imp_out_xmax - imp_out_xmin, imp_in_ymin - imp_out_ymin), layer=implant_layer))
            s_rect.move((imp_out_xmin, imp_out_ymin))
        if 'n' in shape:
            n_rect = c.add_ref(gf.components.rectangle(size=(imp_out_xmax - imp_out_xmin, imp_out_ymax - imp_in_ymax), layer=implant_layer))
            n_rect.move((imp_out_xmin, imp_in_ymax))

    # ---------------------------------------------------------
    # BASE BOUNDARIES (Used for Tap, LI, and Metal1 layers)
    # ---------------------------------------------------------
    out_xmin = -grw
    out_xmax = in_w + grw
    out_ymin = -grw
    out_ymax = in_l + grw
    
    in_xmin = 0
    in_xmax = in_w
    in_ymin = 0
    in_ymax = in_l

    # ---------------------------------------------------------
    # 2. TAP LAYER
    # ---------------------------------------------------------
    if 'w' in shape:
        c.add_ref(gf.components.rectangle(size=(in_xmin - out_xmin, out_ymax - out_ymin), layer=tap_layer)).move((out_xmin, out_ymin))
    if 'e' in shape:
        c.add_ref(gf.components.rectangle(size=(out_xmax - in_xmax, out_ymax - out_ymin), layer=tap_layer)).move((in_xmax, out_ymin))
    if 's' in shape:
        c.add_ref(gf.components.rectangle(size=(out_xmax - out_xmin, in_ymin - out_ymin), layer=tap_layer)).move((out_xmin, out_ymin))
    if 'n' in shape:
        c.add_ref(gf.components.rectangle(size=(out_xmax - out_xmin, out_ymax - in_ymax), layer=tap_layer)).move((out_xmin, in_ymax))

    # ---------------------------------------------------------
    # 3. LI LAYER & LICON CONTACTS
    # ---------------------------------------------------------
    if con_lev == "li" or con_lev == "metal1":
        # Draw LI Layer Rectangles
        if 'w' in shape:
            c.add_ref(gf.components.rectangle(size=(in_xmin - out_xmin, out_ymax - out_ymin), layer=li_layer)).move((out_xmin, out_ymin))
        if 'e' in shape:
            c.add_ref(gf.components.rectangle(size=(out_xmax - in_xmax, out_ymax - out_ymin), layer=li_layer)).move((in_xmax, out_ymin))
        if 's' in shape:
            c.add_ref(gf.components.rectangle(size=(out_xmax - out_xmin, in_ymin - out_ymin), layer=li_layer)).move((out_xmin, out_ymin))
        if 'n' in shape:
            c.add_ref(gf.components.rectangle(size=(out_xmax - out_xmin, out_ymax - in_ymax), layer=li_layer)).move((out_xmin, in_ymax))

        # Determine contact range limits
        if grw < con_size[0] + 2*con_enc[0]:
            con_range = (in_xmin, in_xmax)
        else: 
            con_range = (out_xmin, out_xmax)
            
        # Draw LICON Vias (Fixed orientation: w=Left, e=Right, n=Top, s=Bottom)
        if 'w' in shape:
            via_generator(cell, x_range=(out_xmin, in_xmin), y_range=(in_ymin + 0.17 , in_ymax - 0.17), via_enclosure=con_enc, via_layer=licon_layer, via_size=con_size, via_spacing=con_spacing)
        if 'e' in shape:
            via_generator(cell, x_range=(in_xmax, out_xmax), y_range=(in_ymin + 0.17 , in_ymax - 0.17), via_enclosure=con_enc, via_layer=licon_layer, via_size=con_size, via_spacing=con_spacing)
        if 'n' in shape:
            via_generator(cell, x_range=con_range, y_range=(in_ymax, out_ymax), via_enclosure=con_enc, via_layer=licon_layer, via_size=con_size, via_spacing=con_spacing)
        if 's' in shape:
            via_generator(cell, x_range=con_range, y_range=(out_ymin, in_ymin), via_enclosure=con_enc, via_layer=licon_layer, via_size=con_size, via_spacing=con_spacing)

    # ---------------------------------------------------------
    # 4. METAL 1 LAYER & MCON CONTACTS
    # ---------------------------------------------------------
    if con_lev == "metal1" :
        # Draw M1 Layer Rectangles
        if 'w' in shape:
            c.add_ref(gf.components.rectangle(size=(in_xmin - out_xmin, out_ymax - out_ymin), layer=m1_layer)).move((out_xmin, out_ymin))
        if 'e' in shape:
            c.add_ref(gf.components.rectangle(size=(out_xmax - in_xmax, out_ymax - out_ymin), layer=m1_layer)).move((in_xmax, out_ymin))
        if 's' in shape:
            c.add_ref(gf.components.rectangle(size=(out_xmax - out_xmin, in_ymin - out_ymin), layer=m1_layer)).move((out_xmin, out_ymin))
        if 'n' in shape:
            c.add_ref(gf.components.rectangle(size=(out_xmax - out_xmin, out_ymax - in_ymax), layer=m1_layer)).move((out_xmin, in_ymax))

        # Draw MCON Vias (Fixed orientation: w=Left, e=Right, n=Top, s=Bottom)
        if 'w' in shape:
            via_generator(cell, x_range=(out_xmin, in_xmin), y_range=(in_ymin + 0.17 , in_ymax - 0.17), via_enclosure=con_enc, via_layer=mcon_layer, via_size=con_size, via_spacing=con_spacing)
        if 'e' in shape:
            via_generator(cell, x_range=(in_xmax, out_xmax), y_range=(in_ymin + 0.17 , in_ymax - 0.17), via_enclosure=con_enc, via_layer=mcon_layer, via_size=con_size, via_spacing=con_spacing)
        if 'n' in shape:
            via_generator(cell, x_range=con_range, y_range=(in_ymax, out_ymax), via_enclosure=con_enc, via_layer=mcon_layer, via_size=con_size, via_spacing=con_spacing)
        if 's' in shape:
            via_generator(cell, x_range=con_range, y_range=(out_ymin, in_ymin), via_enclosure=con_enc, via_layer=mcon_layer, via_size=con_size, via_spacing=con_spacing)
    c.flatten()
    take_component(c, cell)
    bbox = cell.dbbox()
    final_w = right - left
    final_h = top - bottom
    origin_lower = origin.lower()

    # Determine X-axis shift
    if 'left' in origin_lower:
        shift_x = -left
    elif 'right' in origin_lower:
        shift_x = -right
    else: # Default to center X
        shift_x = -(left + final_w / 2)

    # Determine Y-axis shift
    if 'bottom' in origin_lower:
        shift_y = -bottom
    elif 'top' in origin_lower:
        shift_y = -top
    else: # Default to center Y
        shift_y = -(bottom + final_h / 2)

    # Apply the calculated transformation
    trans = kdb.DTrans(shift_x, shift_y)

    for layer in cell.layout().layer_indexes():
        cell.shapes(layer).transform(trans)
        
    # for inst in cell.each_inst():
        # inst.transform(trans)