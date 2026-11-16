import os
import sys

import klayout.db as kdb

# 1. Dynamically append the current macro directory to the Python path
macro_dir = os.path.dirname(os.path.abspath(__file__))
if macro_dir not in sys.path:
    sys.path.append(macro_dir)

# 2. Use standard absolute imports (no dots!)
from ..base_definitions import base_definitions
from .draw_fet import draw_fet
from .draw_guard_ring import draw_gr
from .layers_def import *
from .via_generator import vias_gen_draw


class sky_base_definitions(base_definitions):
    def add_separation(self, specs, separator = 'Separator'):
        count = len(self.get_parameters())
        specs(f'_{self.fix_only_chars_string(separator)}{count}', f'----- {separator} -----','='*20, readonly=True)
        
    def additionnal_specs(self, specs, descriptions):
        #self.init_metal_stacks(self)
        specs("start_level", 2, "First connection metal", [1,2,3,4], tooltip=descriptions['metal_level'])
        specs("odd_vertical", True, "Vertical Metal ODD",tooltip=descriptions['odd_vertical'])
    
    def set_devices(self, model_type):
        """
        Set up the SKY130 PMOS/NMOS models and map the metal stack layers.
        """
        self.layout = kdb.Layout()
        
        
        self.pmos = "sky130_fd_pr__pfet_"+model_type
        self.nmos = "sky130_fd_pr__nfet_"+model_type
            
        self.poly_layer = poly_layer
        
        # SKY130 Standard Metal Stack (li, m1, m2, m3, m4, m5)
        self.metal_layers = (li_layer, m1_layer, m2_layer, m3_layer, m4_layer, m5_layer)
        self.horizontal_layers = []
        self.vertical_layers = []
        for i,metal in enumerate(self.metal_layers):
            if i+1 < self.start_level: continue
            if (i%2 == 0 and self.odd_vertical) or (i%2 != 0 and not self.odd_vertical): self.horizontal_layers.append(metal)
            else: self.vertical_layers.append(metal)
        
    def get_mos_dimensions(self, w, l, ng, gate_connection, device_model, connection_params={}):
        """
        Calculates device Width and Height analytically without drawing it.
        """
        # licon_size, licon_spacing, licon_dt_enc = 0.17, 0.19, 0.04
        # sd_con_col = connection_params.get('sd_con_col', 1)
        # inter_sd_l = connection_params.get('inter_sd_l', 0.3)
        
        # sd_l_con = (sd_con_col * licon_size) + ((sd_con_col - 1) * licon_spacing) + 2 * licon_dt_enc
        # sd_l = sd_l_con + 0.05
        
        # width = sd_l + ng * l + (ng - 1) * inter_sd_l + sd_l
        
        # # Height estimation (including standard end_caps and M2 routing bounds)
        # end_cap = 0.2
        # pc_y = 0.08 + 0.17 + 0.08
        # height = w + (2 * end_cap) + (2 * pc_y)
        
        # 1. Parameter Mapping
        gate_map = {'T': 'top', 'B': 'bottom', 'T-B': 'both', 'none': 'none'}
        gate_pos = gate_map.get(gate_connection, 'both')
        
        inter_sd_l = connection_params.get('inter_sd_l', 0.3)
        sd_con_col = connection_params.get('sd_con_col', 1)
        
        # 2. Invoke the generator into a temporary cell
        temp_cell = self.layout.create_cell(f"{device_model}_temp_{w}/{l}")
        draw_fet(
            cell=temp_cell, 
            l=l, w=w, nf=ng, 
            sd_con_col=sd_con_col, 
            inter_sd_l=inter_sd_l, 
            type=device_model, 
            gate_con_pos=gate_pos,
            interdig=1 if ng > 1 else 0
        )
        width = next(temp_cell.shapes(diff_layer).each(), None).dbbox().width()
        poly_region = kdb.Region(temp_cell.shapes(poly_layer))
        bbox = poly_region.merged().bbox()
        height = bbox.to_dtype(temp_cell.layout().dbu).height()
        temp_cell.delete()
        return {'Width': width, 'Height': height}

    def gen_mos(self, w, l, ng, gate_connection, device_model, x, y, device_name="", connection_params={}, start_diffusion="Source"):
        """
        Generates the MOSFET using `draw_fet`, places it at (x,y), and returns all physical 
        contact bounding boxes (DBox) for the automated routing engine.
        """
        # 1. Parameter Mapping
        gate_map = {'T': 'top', 'B': 'bottom', 'T-B': 'both', 'none': 'none'}
        gate_pos = gate_map.get(gate_connection, 'both')
        
        inter_sd_l = connection_params.get('inter_sd_l', 0.3)
        sd_con_col = connection_params.get('sd_con_col', 1)
        
        # 2. Invoke the generator into a temporary cell
        temp_cell = self.layout.create_cell(f"{device_model}_temp_{device_name}")
        draw_fet(
            cell=temp_cell, 
            l=l, w=w, nf=ng, 
            sd_con_col=sd_con_col, 
            inter_sd_l=inter_sd_l, 
            type=device_model, 
            gate_con_pos=gate_pos,
            interdig=1 if ng > 1 else 0
        )
        region = kdb.Region(temp_cell.shapes(poly_layer))
        region.merge()
        temp_cell.shapes(poly_layer).clear()
        temp_cell.shapes(poly_layer).insert(region)
        
        # 3. Instantiate into the active layout at (x,y)
        trans = kdb.DTrans(x, y)
        self.cell.insert(kdb.DCellInstArray(temp_cell.cell_index(), trans))
        
        gates = [s.dbbox().transformed(trans) for s in temp_cell.shapes(poly_layer)]
        activ_box = next(temp_cell.shapes(diff_layer).each(), None).dbbox().transformed(trans)
        # Build dictionary of DBoxes offset by (x, y)
        diff_contacts = [s.dbbox().transformed(trans) for s in temp_cell.shapes(self.metal_layers[0]) if s.dbbox().transformed(trans).inside(activ_box)]
        diff_contacts = sorted(diff_contacts, key = lambda a: a.left)
        sources = []
        drains = []
        for i, contact in enumerate(diff_contacts):
            if (i%2 == 0 and start_diffusion == "Source") or (i%2 != 0 and start_diffusion != "Source"): sources.append(contact)
            else: drains.append(contact)
        
        
        gates_contacts = [s.dbbox().transformed(trans) for s in temp_cell.shapes(self.metal_layers[0]) if not s.dbbox().transformed(trans).inside(activ_box)]
        gates_top_contacts = []
        gates_bottom_contacts = []
        for gate in gates_contacts:
            if gate.center().y > activ_box.center().y:
                gates_top_contacts.append(gate)
            else:
                gates_bottom_contacts.append(gate)
                
        contacts = {
            'active_box': activ_box,
            'source_contact': diff_contacts[0],
            'drain_contact': diff_contacts[-1],
            'gates': gates,
            'gate': gates[0],
            'gates_t': gates_top_contacts,
            'gates_b': gates_bottom_contacts,
            'gate_top_contact': gates_top_contacts[0] if len(gates_top_contacts) > 0 else None,
            'gate_bottom_contact': gates_bottom_contacts[0] if len(gates_bottom_contacts) > 0 else None,
            'sources': sources,
            'drains': drains,
            'name': device_name
        }
        
        # Optional: Label the device
        if device_name:
            for box in gates:
                self.draw_label(box, device_name, m1_layer)
            
        return contacts

    def gen_tap(self, box, tap_type, tap_shape, tap_width, tap_name=""):
        """
        Generates Guard Rings / Taps using the dedicated `draw_gr` script.
        """
        implant_type = 'nsdm' if 'well' in tap_type.lower() else 'psdm'
        
        # The external draw_gr handles the boolean construction inherently.
        temp_cell = self.layout.create_cell(f"tap_{tap_name}_{tap_type}")
        draw_gr(
            cell=temp_cell, 
            in_l=box.height(), 
            in_w=box.width(), 
            grw=tap_width, 
            implant_type=implant_type, 
            shape=tap_shape, 
            origin="centerCenter"
        )
        
        trans = kdb.DTrans(box.center().x, box.center().y)
        self.cell.insert(kdb.DCellInstArray(temp_cell.cell_index(), trans))
        if implant_type == 'nsdm':
            well_box = temp_cell.dbbox().transformed(trans)
            self.draw_rect(well_box, nwell_layer)

    def draw_rect(self, box, layer, net_name=""):
        """
        Draws a pure rectangle on the specified layer.
        """
        # Ensure we are using klayout db indices from layers_def
        layer_idx = self.layout.layer(layer[0], layer[1]) if isinstance(layer, tuple) else layer
        self.cell.shapes(layer_idx).insert(kdb.DBox(box.left, box.bottom, box.right, box.top))
        
        if net_name:
            self.draw_label(box, net_name, layer)
        return box

    def draw_label(self, box, text, layer, size=0):
        """
        Places a text label at the center of a given box.
        """
        layer_idx = self.layout.layer(layer[0], layer[1]) if isinstance(layer, tuple) else layer
        auto_size = min(box.width(), box.height()) * 0.5 if size == 0 else size
        auto_size = min(auto_size, 0.2) 
        auto_rotate = kdb.DTrans.R0 if box.width() > box.height() else kdb.DTrans.R90
        center = box.center()
        text_obj = kdb.DText(text, kdb.DTrans(auto_rotate, center.x, center.y))
        text_obj.size = auto_size
        text_obj.font = 2
        text_obj.halign = kdb.DText.HAlignCenter
        text_obj.valign = kdb.DText.VAlignCenter
        
        self.cell.shapes(layer_idx).insert(text_obj)
        return text_obj

    def gen_via(self, box, b_layer, t_layer):
        """
        Places standard vias across intersecting metal layers.
        """
        layer_map = {
            poly_layer: "poly",
            diff_layer: "n_diff", # Note: vias_gen_draw treats n_diff/p_diff identically for enclosures
            tap_layer: "n_tap",
            li_layer: "li",
            m1_layer: "metal1",
            m2_layer: "metal2",
            m3_layer: "metal3",
            m4_layer: "metal4",
            m5_layer: "metal5"
        }
        temp_cell = self.layout.create_cell("via_transition")
        
        temp_blayer = b_layer;
        if b_layer[0] > t_layer[0]:
            b_layer = t_layer
            t_layer = temp_blayer

        start_str = layer_map.get(b_layer, "metal1")
        end_str = layer_map.get(t_layer, "metal2")
        
        # Route to native Sky130 via_stack generator
        vias_gen_draw(
            cell=temp_cell, 
            l=self.fix_grid(box.width()), 
            w=max(self.fix_grid(box.height()), 0.23), 
            start_layer=start_str, 
            end_layer=end_str
        )
        
        # 4. Instantiate the generated via array at the exact routing box coordinates
        trans = kdb.DTrans(self.fix_grid(box.left), self.fix_grid(box.bottom))
        self.cell.insert(kdb.DCellInstArray(temp_cell.cell_index(), trans))
        return box

    def connect_boxes(self, box1, box2, b_layer, t_layer):
        """
        Automatically places a via wherever two defined routing boxes overlap.
        """
        intersection_box = box1 & box2
        if intersection_box.area() == 0:
            return None
            
        return self.gen_via(intersection_box, b_layer, t_layer)

    def fix_grid(self, size):
        """
        Forces a dimension to snap to the Sky130 0.005µm manufacturing grid.
        """
        grid = 0.005
        return round(size / grid) * grid

    def fix_min_met_area(self, box, direction):
        """
        Expands the box to meet minimum area design rules for Sky130 M1/M2.
        """
        min_area = 0.083  # standard SKY130 M1 min area
        width = box.width()
        height = box.height()
        
        if width * height < min_area:
            if direction == 'v':
                vertical_size = self.fix_grid((min_area / width) - height) / 2
                box.bottom -= vertical_size
                box.top += vertical_size
            else:
                horizontal_size = self.fix_grid((min_area / height) - width) / 2
                box.left -= horizontal_size
                box.right += horizontal_size
                
            self.draw_rect(box, self.metal_layers[1]) # default fixing on M1
        return box