import pya

from ..dynamic_pcell_base import dynamic_pcell_base
from .sky_base_definitions import sky_base_definitions
import cProfile
import pstats
import io
import sys


class dynamic_pcell(dynamic_pcell_base, pya.PCellDeclarationHelper, sky_base_definitions):
    """
    This is a dynamic PCell that can be used to generate different types of devices
    """

    def __init__(self):
        super(dynamic_pcell, self).__init__()
        specs = self.specs
        descriptions = self.read_description_file("./dynamic_pcell_descriptions.json")
        self.add_separation( specs, 'Devices Sizing')
        specs('pmos_w', 5.0, 'PMOS Width', unit='um', tooltip=descriptions['pmos_w'])
        specs('pmos_l', 3.0, 'PMOS Length', unit='um', tooltip=descriptions['pmos_l'])
        specs('nmos_w', 5.0, 'NMOS Width', unit='um', tooltip=descriptions['nmos_w'])
        specs('nmos_l' , 3.0, 'NMOS Length', unit='um', tooltip=descriptions['nmos_l'])
    
        self.add_separation( specs, 'Model Type')
        specs('model_type', '01v8', 'Model Type', ['01v8', 
                                                 '01v8_lvt', 
                                                 '01v8_hvt',
                                                 'g5v0d10v5'], tooltip=descriptions['model_type'])
        
        self.add_separation( specs, 'Internal connections & patterns settings')
        specs('horizontal_spacing', 0.26, 'Horizental Spacing', unit='um', tooltip=descriptions['horizontal_spacing'])
        specs('vertical_spacing', 0.3, 'Vertical Spacing', unit='um', tooltip=descriptions['vertical_spacing'])
        specs('connect_gates_use_poly', True, 'Connect gates using poly', tooltip=descriptions['connect_gates_use_poly'])
        specs('horizontal_connection_width', 0.5, 'Horizontal Connection metal width', unit='um', tooltip=descriptions['horizontal_connection_width'])
        specs('vertical_connection_width', 0.5, 'Vertical Connection metal width', unit='um', tooltip=descriptions['vertical_connection_width'])
        specs('connection_spacing', 0.5, 'Connection metal spacing', unit='um', tooltip=descriptions['connection_spacing'])
        specs('pn_spacing', 0.0, 'Additional spacing between PMOS and NMOS', unit='um', tooltip=descriptions['pn_spacing'])
        specs('nmos_layout_pattern', '3A4B3A', 'NMOS Layout Pattern', tooltip=descriptions['nmos_layout_pattern'])
        specs('pmos_layout_pattern', '3C4D3C', 'PMOS Layout Pattern', tooltip=descriptions['pmos_layout_pattern'])
        specs('gate_connection_top_devices', 'AC', 'Gate Connection On Top', tooltip=descriptions['gate_connection_top_devices'])
        specs('gate_connection_bot_devices', 'BD', 'Gate Connection On Bottom', tooltip=descriptions['gate_connection_bot_devices'])
        specs('gate_connected_to_source_devices', '', 'Devices which gate linked to source', tooltip=descriptions['gate_connected_to_source_devices'])
        specs('gate_connected_to_drain_devices', 'A', 'Devices which gate linked to drain', tooltip=descriptions['gate_connected_to_drain_devices'])
        specs('gates_connected_devices', 'AB', 'Devices which gates connected together', tooltip=descriptions['gates_connected_devices'])
        specs('source_connected_devices', 'AB CD', 'Devices which sources connected together', tooltip=descriptions['source_connected_devices'])
        specs('drain_connected_devices', '', 'Devices which drains connected together', tooltip=descriptions['drain_connected_devices'])
        # specs('drains_to_tap_devices', 'TBD', 'Devices which drains connected to tap',ReadOnlyConstraint(), tooltip=descriptions['drains_to_tap_devices'])
        # specs('sources_to_tap_devices', 'TBD', 'Devices which sources connected to tap',ReadOnlyConstraint(), tooltip=descriptions['sources_to_tap_devices'])
        specs('draw_vertical_connections', True, 'Draw Vertical Connections', tooltip=descriptions['draw_vertical_connections'])
        specs('draw_horizontal_connections', False, 'Draw Horizontal Connections', tooltip=descriptions['draw_horizontal_connections'])
        self.additionnal_specs(specs, descriptions)
        
        self.add_separation( specs, 'Dummies settings')
        specs('dummies_count', 2, 'Number of dummies', tooltip=descriptions['dummies_count'])
        specs('inner_dummies_count',0,'Number of dummies between devices', tooltip=descriptions['inner_dummies_count'])
        specs('dummy_pmos_l', 0.5, 'Dummy PMOS length', unit='um', tooltip=descriptions['dummy_pmos_l'])
        specs('dummy_nmos_l', 0.5, 'Dummy NMOS length', unit='um', tooltip=descriptions['dummy_nmos_l'])
        specs('dummies_core_spacing', -0.3, 'Distance between core and dummy', unit='um', tooltip=descriptions['dummies_core_spacing'])
        specs('dummies_spacing', 0.2, 'Distance between dummies', unit='um', tooltip=descriptions['dummies_spacing'])
        specs('overlap_dummies_diffusions', True, 'Overlap Dummies S/D diffusions', tooltip=descriptions['overlap_dummies_diffusions'])
        specs('place_taps', False, 'Place taps between devices', tooltip=descriptions['place_taps'])
        
        specs('guardRingDistance_X', 0.5, 'Guard Ring Horizontal Distance')
        specs('guardRingDistance_Y', 0.5, 'Guard Ring Vertical Distance')
        specs('guardRingWidth', 0.3, 'Guard Ring Width')
        self.enable_warnings = False
    
    def parse_param_type_from_type(self, dtype):
        if dtype == bool:
            param_type = self.TypeBoolean
        elif dtype == int:
            param_type = self.TypeInt
        elif dtype == float:
            param_type = self.TypeDouble
        else:
            param_type = self.TypeString

        return param_type
    def specs(self, param_name, default_value, description, ptype=None, unit=None, tooltip=None ,readonly=False):
        """
        Helper function to add a parameter to the PCell
        """
        param_type = None
        choises = []
        if ptype is None:
            dtype = type(default_value)
            param_type = self.parse_param_type_from_type(dtype)
        elif isinstance(ptype, (list, tuple)):
            param_type = self.parse_param_type_from_type(ptype[0])
            choises = list(ptype)
        print(description)
        param = self.param(name = param_name, value_type = param_type, default=default_value, description=description, unit=unit, tooltip=tooltip)
        
        for choice in choises:
            param.add_choice(choice, choice)
        
        param.readonly = readonly
    
    def display_text_impl(self):
        # Provide a descriptive text for the cell
        return f"dynamic_pcell(P={self.nmos_layout_pattern},\n N={self.pmos_layout_pattern})"
    
    def coerce_parameters_impl(self):
        self.set_devices(self.model_type)
        # This method is called to coerce parameters before the cell is created

    def can_create_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we can use any shape which
        # has a finite bounding box
        return self.shape.is_box() or self.shape.is_polygon() or self.shape.is_path()
    
    def parameters_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we set r and l from the shape's
        # bounding box width and layer
        self.r = self.shape.bbox().width() * self.layout.dbu / 2
        self.l = self.layout.get_info(self.layer)
    
    def wants_lazy_evaluation(self):
        return True 
    
    def transformation_from_shape_impl(self):
        # Implement the "Create PCell from shape" protocol: we use the center of the shape's
        # bounding box to determine the transformation
        return pya.Trans(self.shape.bbox().center())
    
    def produce_impl(self):
        self.use_deep_nwell = False
        # if sys.monitoring.get_tool(sys.monitoring.PROFILER_ID) is not None:
        #     sys.monitoring.free_tool_id(sys.monitoring.PROFILER_ID)
        # pr = cProfile.Profile()
        
        # with pr:        
        self.gen_dynamic_array()
        self.cell.flatten(True)
        
        # # 2. Stop the profiler
        # pr.disable()
        
        # # 3. Format and print the results to the KLayout console
        # s = io.StringIO()
        # ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
        # ps.print_stats(20) # Print the top 20 slowest functions
        # print(s.getvalue())

