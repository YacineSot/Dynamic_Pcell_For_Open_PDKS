# Dynamic PCell Generator

A highly configurable, Python-based Parameterized Cell (PCell) generator for automated analog and mixed-signal IC layout. This tool allows layout engineers to generate complex, routed transistor arrays, current mirrors, and differential pairs instantly using intuitive pattern strings and automated routing rules.

## ✨ Key Features

* **Pattern-Based Generation:** Define complex multi-row device arrays using simple string patterns (e.g., `4A3B2C*3`).
* **Automated Routing:** Automatically route horizontal and vertical connections, tie gates to diffusions, and group nets across multiple devices.
* **Smart Dummy Insertion:** Automatically place edge and internal dummies with options to overlap diffusions for area optimization.
* **Flexible Metal Stack:** Control your starting metal layer, define even/odd routing directions, and customize connection widths and spacings to meet DRC rules.
* **Integrated Guard Rings & Taps:** Automatically place well/substrate taps and route selected diffusions directly to the guard ring.

---

## 🛠️ Usage: Layout Pattern Syntax

The core of the dynamic generator is the layout pattern string, which dictates how devices are placed in the array.

* **Basic Placement:** Letters represent distinct devices (`A`, `B`, `C`).
* **Multiplication:** Prefix a letter with a number to repeat it consecutively (`4A` $\rightarrow$ `AAAA`).
* **Row Repetition:** Append `*N` to repeat the entire row `N` times.
* **Multiple Rows:** Separate rows with a space.

**Example:**
`4A3B2C*3 AABBCC`

1. Draws `AAAABBBCC` three times (3 rows).
2. Draws a final row of `AABBCC`.

---

## ⚙️ Parameter Reference

The PCell exposes a comprehensive set of CDF parameters to fine-tune the generated layout.

### 📐 Device Sizing & Technology

| Parameter | Description |
| --- | --- |
| `model_type` | Device model variant (e.g., High Voltage `HV` or Low Voltage `LV`). |
| `pmos_w` / `pmos_l` | Width and channel length of the PMOS core devices. |
| `nmos_w` / `nmos_l` | Width and channel length of the NMOS core devices. |

### ↔️ Spacing & Design Rules

| Parameter | Description |
| --- | --- |
| `horizontal_spacing` | Distance between adjacent devices horizontally within the same row. |
| `vertical_spacing` | Distance vertically between adjacent device rows in the array. |
| `pn_spacing` | Spacing between PMOS and NMOS blocks. Use a negative value to force diffusion merging. |
| `connection_spacing` | Minimum spacing between adjacent routing metal tracks to satisfy DRC rules. |

### 🔌 Automated Routing & Metal Stack

| Parameter | Description |
| --- | --- |
| `draw_horizontal_connections` | Automatically generate horizontal routing structures. |
| `draw_vertical_connections` | Automatically generate vertical routing structures. |
| `metal_level` | Minimum (starting) metal layer used for routing. Raising this value shifts the entire routing stack up, leaving lower metals untouched. |
| `odd_vertical` | If checked, odd-numbered metals route vertically and evens horizontally. Uncheck to invert. |
| `horizontal_connection_width` | Width of the horizontal routing metal tracks. |
| `vertical_connection_width` | Width of the vertical routing metal tracks. |
| `connect_gates_use_poly` | Enable to route gate connections using the Poly layer instead of the horizontal routing metal. |

### 🔗 Connectivity Mapping

*Format: Group devices sharing the same net into one block. Separate different nets with a space (e.g., `AB CD`).*

| Parameter | Description |
| --- | --- |
| `gates_connected_devices` | Devices whose gates are connected together. |
| `source_connected_devices` | Devices whose Source terminals are connected together. |
| `drain_connected_devices` | Devices whose Drain terminals are connected together. |
| `gate_connected_to_source_devices` | Device letter(s) whose gate is internally tied to its own Source terminal. |
| `gate_connected_to_drain_devices` | Device letter(s) whose gate is internally tied to its own Drain terminal. |
| `gate_connection_top_devices` | Device letters whose gates should be routed toward the top of the array row. |
| `gate_connection_bot_devices` | Device letters whose gates should be routed toward the bottom of the array row. |

### 🛡️ Dummies

| Parameter | Description |
| --- | --- |
| `dummies_count` | Number of dummy devices to place at the outer edges (left and right) of the row. |
| `inner_dummies_count` | Number of dummy devices to place internally between different core devices. |
| `dummy_pmos_l` / `dummy_nmos_l` | Channel length for the PMOS / NMOS dummy devices. |
| `dummies_spacing` | Distance between adjacent dummy devices. |
| `dummies_core_spacing` | Spacing between the core array and the dummy devices. Use a negative value to force diffusion merging. |
| `overlap_dummies_diffusions` | Overlap the Source/Drain diffusions of dummy devices to save layout area. |

### 🚰 Taps & Guard Rings

| Parameter | Description |
| --- | --- |
| `place_taps` | Generate substrate or well taps internally between the devices in the row. |
| `sources_to_tap_devices` | Device letters whose Source terminals should be tied directly to the well tap / guard ring. |
| `drains_to_tap_devices` | Device letters whose Drain terminals should be tied directly to the well tap / guard ring. |

## 🚀 Installation

The installation process depends on the open-source PDK you are targeting.

### For SkyWater (sky130) & GlobalFoundries (gf180mcu)
1. **Clone the repository:** Clone this dynamic PCell repository to your local machine.
2. **Add to KLayout:** 
   * Open KLayout and open the Macro Development environment by pressing `F5`.
   * Right-click in the Macro Tree and select **Add Directory...** 
   * Select the folder you just cloned.

### For IHP (sg13g2 / sg13cmos5l)
To use the dynamic PCell generator with the IHP PDK, you need to use a modified version of the PDK.
1. **Clone the fork:** Do not use the standard IHP open PDK repository. Instead, clone the full IHP repository directly from my fork which has the dynamic PCell integrated:
   ```bash
   git clone https://github.com/YacineSot/IHP-Open-PDK.git