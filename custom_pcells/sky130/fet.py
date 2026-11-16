# Copyright 2022 Mabrains LLC
# ... (License header) ...

import pya
from .draw_fet import draw_fet
import math

# Constants
fet_01v8_l, fet_w = 0.15, 0.42
fet_g5v0_l = 0.5
fet_ld, fet_inter_ld = 0.3, 0.3
fet_01v8_grw, pfet_g5v0_grw = 0.17, 0.3
pfet_01v8_lvt_l, nfet_g5v0_nvt_l = 0.35, 0.9 

class BaseFet(pya.PCellDeclarationHelper):
    """Base class for shared FET properties and constraints."""
    
    def __init__(self):
        super().__init__()
        
        self.param("con_bet_fin", self.TypeBoolean, "Contact Between Fingers", default=1)
        
        # Base type choices (overridden by child classes)
        self.Type_handle = self.param("type", self.TypeString, "Device Type")
        
        self.bulk_handle = self.param("bulk", self.TypeString, "Bulk Type")
        for choice in ["None", "bulk tie", "guard ring"]:
            self.bulk_handle.add_choice(choice, choice)
        self.bulk_handle.default = "None"

        self.gate_pos = self.param("gate_con_pos", self.TypeString, "Gate Contact Position")
        for choice in ["none", "top", "bottom", "both", "alternating"]:
            self.gate_pos.add_choice(choice, choice)
        self.gate_pos.default = "alternating"

        self.param("l", self.TypeDouble, "Length", default=fet_01v8_l, unit="um")
        self.range_param(self.param("gatecont_l_ratio", self.TypeDouble, "Gate contact to length ratio", unit="%", default=80), 0, 100)
        gt_cont = self.param("gate_metal_level", self.TypeInt, "Gate metal contact level", default=1)
        for choice in range(6):
            gt_cont.add_choice(choice, choice)
        sd_cont = self.param("sd_metal_level", self.TypeInt, "S/D metal contact level", default=1)
        for choice in range(6):
            sd_cont.add_choice(choice, choice)
        self.param("w", self.TypeDouble, "Width", default=fet_w, unit="um")
        self.range_param(self.param("sd_w_ratio", self.TypeDouble, "S/D contacts to width ratio", unit="%", default=80), 0, 100)
        self.param("sd_con_col", self.TypeInt, "Diffusion Contacts Columns", default=1)
        self.param("inter_sd_l", self.TypeDouble, "Between Fingers Diffusion Length", default=fet_inter_ld, unit="um")
        self.param("nf", self.TypeInt, "Number of Fingers", default=1)
        self.param("area", self.TypeDouble,"Area", readonly=True, unit="um^2")
        self.param("perim", self.TypeDouble,"Perimeter", readonly=True, unit="um")
        self.param("interdig", self.TypeBoolean, "Interdigitation", default=0)
        self.param("patt", self.TypeString,"Pattern in case of Interdigitation", default= "")
        
        self.guard_ring_params = [
            self.param("north", self.TypeBoolean, "Guard Ring North Side", default=True),
            self.param("south", self.TypeBoolean, "Guard Ring South Side", default=True),
            self.param("east", self.TypeBoolean, "Guard Ring East Side", default=True),
            self.param("west", self.TypeBoolean, "Guard Ring West Side", default=True),
            self.param('gr_hspacing', self.TypeDouble, "Guard Ring Horizontal Spacing (diffusion-tap)", default=0.32, unit="um"),
            self.param('gr_vspacing', self.TypeDouble, "Guard Ring Vertical Spacing (diffusion-tap)", default=0.8, unit="um"),
            self.param("grw", self.TypeDouble, "Guard Ring Width", default=fet_01v8_grw, unit="um")
        ]
        #if self.bulk == 'guard ring':
        
        self.dev_type = 'nfet' # overridden by child

    
    def range_param(self, param, min_v, max_v):
        param.min_value = min_v
        param.max_value = max_v
    
    def display_text_impl(self):
        return f"{self.dev_type}(L={self.l:.3f},W={self.w:.3f})"
    
    
    def callback_impl(self, name):
        bulk_state = self._param_states.parameter("bulk")
        for g_param in self.guard_ring_params:
            gp_state = self._param_states.parameter(g_param.name)
            enabled = bulk_state.value == "guard ring"
            gp_state.enabled = enabled
            gp_state.visible = enabled
        
        return super().callback_impl(name)
    
    def coerce_parameters_impl(self):
        self.area  = self.w * self.l
        self.perim = 2*(self.w + self.l)

        
        # Apply global minimums
        if "g5v0d10v5" in self.type or "03v3_nvt" in self.type or "05v0_nvt" in self.type:
            self.l = max(self.l, fet_g5v0_l)
            self.w = max(self.w, fet_w)
            self.grw = max(self.grw, pfet_g5v0_grw)
            
            if "05v0_nvt" in self.type:
                self.l = max(self.l, nfet_g5v0_nvt_l)
        else:
            self.l = max(self.l, fet_01v8_l)
            self.w = max(self.w, fet_w)
            self.grw = max(self.grw, fet_01v8_grw)
            
            if "01v8_lvt" in self.type and self.dev_type == 'pfet':
                self.l = max(self.l, pfet_01v8_lvt_l)
                
        self.sd_con_col = max(self.sd_con_col, 1)
        
        if self.con_bet_fin == 1: 
            self.inter_sd_l = max(self.inter_sd_l, fet_inter_ld)
        else: 
            self.inter_sd_l = max(self.inter_sd_l, 0.21)

        if self.interdig == 1 and self.gate_con_pos != "alternating":
            self.inter_sd_l = 0.5 
        
        self.guard_ring_shape = ''.join(side[0] for side in ['north', 'south', 'east', 'west'] if getattr(self, side))

    def can_create_from_shape_impl(self):
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()

    def parameters_from_shape_impl(self):
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.l = self.layout.get_info(self.layer)
    
    def transformation_from_shape_impl(self):
        return pya.Trans(self.shape.bbox().center())
    
    def produce_impl(self):
        draw_fet(
            cell=self.cell, l=self.l, w=self.w, 
            sd_con_col=self.sd_con_col, inter_sd_l=self.inter_sd_l, nf=self.nf, 
            grw=self.grw, type=self.type, bulk=self.bulk, con_bet_fin=self.con_bet_fin,
            gate_con_pos=self.gate_con_pos, interdig=self.interdig, patt=self.patt, gr_shape = self.guard_ring_shape,
            gr_distances=(self.gr_hspacing, self.gr_vspacing),
            contacts_ratios=(self.sd_w_ratio, self.gatecont_l_ratio),
            contacts_levels=(self.sd_metal_level, self.gate_metal_level)
        )


class pfet(BaseFet):
    """PMOS Generator for Skywater130"""
    def __init__(self):
        super().__init__()
        self.dev_type = 'pfet'
        self.Type_handle.add_choice("sky130_fd_pr__pfet_01v8", "sky130_fd_pr__pfet_01v8")
        self.Type_handle.add_choice("sky130_fd_pr__pfet_01v8_lvt", "sky130_fd_pr__pfet_01v8_lvt")
        self.Type_handle.add_choice("sky130_fd_pr__pfet_01v8_hvt", "sky130_fd_pr__pfet_01v8_hvt")
        self.Type_handle.add_choice("sky130_fd_pr__pfet_g5v0d10v5", "sky130_fd_pr__pfet_g5v0d10v5")
        self.Type_handle.default = self.Type_handle.choice_values()[0]

class nfet(BaseFet):
    """NMOS Generator for Skywater130"""
    def __init__(self):
        super().__init__()
        self.dev_type = 'nfet'
        self.Type_handle.add_choice("sky130_fd_pr__nfet_01v8", "sky130_fd_pr__nfet_01v8")
        self.Type_handle.add_choice("sky130_fd_pr__nfet_01v8_lvt", "sky130_fd_pr__nfet_01v8_lvt")
        self.Type_handle.add_choice("sky130_fd_pr__nfet_03v3_nvt","sky130_fd_pr__nfet_03v3_nvt")
        self.Type_handle.add_choice("sky130_fd_pr__nfet_05v0_nvt","sky130_fd_pr__nfet_05v0_nvt")
        self.Type_handle.add_choice("sky130_fd_pr__nfet_g5v0d10v5","sky130_fd_pr__nfet_g5v0d10v5")
        self.Type_handle.default = self.Type_handle.choice_values()[0]