import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
from graphviz import Source
import io

# ==============================================================================
# --- Page Configuration & Styling ---
# ==============================================================================
st.set_page_config(
    page_title="AquaGenius WWTP Designer",
    page_icon="🌊",
    layout="wide"
)

st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
        <span style="font-size: 40px; margin-right: 15px;">🌊</span>
        <div>
            <h1 style="margin: 0; padding: 0; color: #1F2937;">AquaGenius WWTP Designer</h1>
            <p style="margin: 0; padding: 0; color: #555;">A Preliminary Design & Simulation Tool for Wastewater Treatment</p>
        </div>
    </div>
""", unsafe_allow_html=True)


# ==============================================================================
# --- Engineering Constants & Conversion Factors ---
# ==============================================================================
CONVERSION_FACTORS = {
    'flow': {'MGD_to_m3_day': 3785.41, 'MLD_to_m3_day': 1000, 'm3_hr_to_gpm': 4.40287},
    'volume': {'m3_to_gal': 264.172},
    'area': {'m2_to_ft2': 10.7639},
    'sor': {'m3_m2_day_to_gpd_ft2': 24.54},
    'pressure': {'psi_to_pa': 6894.76}
}

KINETIC_PARAMS = {
    'Y': 0.6, 'kd': 0.06, 'fd': 0.15, 'TSS_VSS_ratio': 1.25
}

AERATION_PARAMS = {
    'O2_demand_BOD': 1.5, 'O2_demand_N': 4.57, 'SOTE': 0.30,
    'O2_in_air_mass_fraction': 0.232, 'air_density_kg_m3': 1.225
}

CHEMICAL_FACTORS = {
    'alum_to_p_ratio': 9.7, 'methanol_to_n_ratio': 2.86
}

# ==============================================================================
# --- Session State Initialization ---
# ==============================================================================
if 'simulation_data' not in st.session_state:
    st.session_state.simulation_data = None
if 'rerun_results' not in st.session_state:
    st.session_state.rerun_results = {}


# ==============================================================================
# --- Sidebar for User Inputs ---
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Influent Design Criteria")
    
    flow_unit_name = st.selectbox(
        "Unit System",
        ('Metric (m³/day)', 'US Customary (MGD)', 'SI (MLD)'),
        key='flow_unit_select'
    )

    unit_display = flow_unit_name.split('(')[-1].replace(')', '')

    avg_flow_input = st.number_input(
        f"Average Influent Flow ({unit_display})",
        min_value=0.1, value=10000.0, step=100.0, format="%.2f"
    )
    
    st.markdown("---")
    
    avg_bod = st.number_input("Average Influent BOD (mg/L)", 50, value=250, step=10)
    avg_tss = st.number_input("Average Influent TSS (mg/L)", 50, value=220, step=10)
    avg_tkn = st.number_input("Average Influent TKN (mg/L)", 10, value=40, step=5)
    avg_tp = st.number_input("Average Influent TP (mg/L)", 1, value=7, step=1)

    st.markdown("---")
    st.header("🧪 Chemical Dosing")
    use_alum = st.checkbox("Use Alum for P Removal")
    use_methanol = st.checkbox("Use Carbon Source for N Removal")

    run_button = st.button("Generate Design & Simulate", use_container_width=True)

# ==============================================================================
# --- PDF Generation Class ---
# ==============================================================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'AquaGenius - WWTP Design Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, title, 0, 1, 'L')
        self.ln(4)

    def chapter_body(self, data):
        self.set_font('Arial', '', 10)
        for k, v in data.items():
            self.multi_cell(0, 5, f"- {k}: {v}")
        self.ln()

    def create_table(self, header, data, col_widths):
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(220, 220, 220)
        for i, h in enumerate(header):
            self.cell(col_widths[i], 7, h, 1, 0, 'C', 1)
        self.ln()
        self.set_font('Arial', '', 9)
        for row in data:
            for i, item in enumerate(row):
                self.cell(col_widths[i], 6, str(item), 1)
            self.ln()
        self.ln(5)

# ==============================================================================
# --- Core Logic Functions ---
# ==============================================================================
def get_inputs():
    """Gathers and processes all inputs from the sidebar."""
    if 'MGD' in flow_unit_name:
        avg_flow_m3_day = avg_flow_input * CONVERSION_FACTORS['flow']['MGD_to_m3_day']
        flow_unit_short = 'MGD'
    elif 'MLD' in flow_unit_name:
        avg_flow_m3_day = avg_flow_input * CONVERSION_FACTORS['flow']['MLD_to_m3_day']
        flow_unit_short = 'MLD'
    else:
        avg_flow_m3_day = avg_flow_input
        flow_unit_short = 'm³/day'

    return {
        'flow_unit_name': flow_unit_name, 'flow_unit_short': flow_unit_short,
        'avg_flow_input': avg_flow_input, 'avg_flow_m3_day': avg_flow_m3_day,
        'avg_bod': avg_bod, 'avg_tss': avg_tss, 'avg_tkn': avg_tkn, 'avg_tp': avg_tp,
        'use_alum': use_alum, 'use_methanol': use_methanol,
    }

def calculate_tank_dimensions(volume, shape='rect', depth=4.5):
    """Calculates tank dimensions based on volume or area."""
    if volume <= 0: return {}
    if shape == 'rect':
        area = volume / depth
        width = (area / 3) ** 0.5 if area > 0 else 0
        length = 3 * width
        return {'Length (m)': f"{length:.1f}", 'Width (m)': f"{width:.1f}", 'Depth (m)': f"{depth:.1f}"}
    elif shape == 'circ':
        diameter = (4 * volume / np.pi) ** 0.5
        return {'Diameter (m)': f"{diameter:.1f}", 'SWD (m)': f"{depth:.1f}"}
    return {}

def calculate_valve_cv(flow_m3_hr, delta_p_psi=5):
    """Calculates a required valve Cv."""
    flow_gpm = flow_m3_hr * CONVERSION_FACTORS['flow']['m3_hr_to_gpm']
    # Cv = Q * sqrt(SG / dP) where SG of water is 1
    cv = flow_gpm * (1 / delta_p_psi) ** 0.5
    return cv

def calculate_cas_sizing(inputs):
    sizing = {'tech': 'CAS'}
    sizing['srt'] = 10
    sizing['mlss'] = 3500
    effluent_bod = 10.0
    sizing['hrt'] = (sizing['srt'] * KINETIC_PARAMS['Y'] * (inputs['avg_bod'] - effluent_bod)) / (sizing['mlss'] * (1 + KINETIC_PARAMS['kd'] * sizing['srt'])) * 24
    sizing['total_volume'] = inputs['avg_flow_m3_day'] * sizing['hrt'] / 24
    sizing['anoxic_volume'] = sizing['total_volume'] * 0.3
    sizing['aerobic_volume'] = sizing['total_volume'] * 0.7
    sizing['clarifier_sor'] = 24
    sizing['clarifier_area'] = inputs['avg_flow_m3_day'] / sizing['clarifier_sor']
    sizing['dimensions'] = {
        'Anoxic Basin': calculate_tank_dimensions(sizing['anoxic_volume']),
        'Aerobic Basin': calculate_tank_dimensions(sizing['aerobic_volume']),
        'Clarifier': calculate_tank_dimensions(sizing['clarifier_area'], shape='circ')
    }
    sizing['effluent_targets'] = {'bod': 10, 'tss': 12, 'tkn': 8, 'tp': 2.0}
    return sizing

def calculate_ifas_sizing(inputs):
    sizing = {'tech': 'IFAS'}
    sizing['srt'] = 8
    sizing['mlss'] = 3000
    sizing['hrt'] = 6
    sizing['total_volume'] = inputs['avg_flow_m3_day'] * sizing['hrt'] / 24
    sizing['anoxic_volume'] = sizing['total_volume'] * 0.3
    sizing['aerobic_volume'] = sizing['total_volume'] * 0.7
    sizing['media_volume'] = sizing['aerobic_volume'] * 0.4
    sizing['clarifier_sor'] = 28
    sizing['clarifier_area'] = inputs['avg_flow_m3_day'] / sizing['clarifier_sor']
    sizing['dimensions'] = {
        'Anoxic Basin': calculate_tank_dimensions(sizing['anoxic_volume']),
        'IFAS Basin': calculate_tank_dimensions(sizing['aerobic_volume']),
        'Clarifier': calculate_tank_dimensions(sizing['clarifier_area'], shape='circ')
    }
    sizing['effluent_targets'] = {'bod': 8, 'tss': 10, 'tkn': 5, 'tp': 1.5}
    return sizing

def calculate_mbr_sizing(inputs):
    sizing = {'tech': 'MBR'}
    sizing['srt'] = 15
    sizing['mlss'] = 8000
    sizing['hrt'] = 5
    sizing['total_volume'] = inputs['avg_flow_m3_day'] * sizing['hrt'] / 24
    sizing['anoxic_volume'] = sizing['total_volume'] * 0.4
    sizing['aerobic_volume'] = sizing['total_volume'] * 0.6
    sizing['membrane_flux'] = 20
    sizing['membrane_area'] = (inputs['avg_flow_m3_day'] * 1000 / 24) / sizing['membrane_flux']
    sizing['dimensions'] = {
        'Anoxic Tank': calculate_tank_dimensions(sizing['anoxic_volume']),
        'MBR Tank': calculate_tank_dimensions(sizing['aerobic_volume'])
    }
    sizing['effluent_targets'] = {'bod': 5, 'tss': 1, 'tkn': 4, 'tp': 1.0}
    return sizing

def calculate_mbbr_sizing(inputs):
    sizing = {'tech': 'MBBR'}
    sizing['hrt'] = 4
    sizing['total_volume'] = inputs['avg_flow_m3_day'] * sizing['hrt'] / 24
    sizing['aerobic_volume'] = sizing['total_volume']
    sizing['media_volume'] = sizing['aerobic_volume'] * 0.5
    sizing['dimensions'] = {
        'MBBR Basin': calculate_tank_dimensions(sizing['aerobic_volume'])
    }
    sizing['effluent_targets'] = {'bod': 15, 'tss': 20, 'tkn': 10, 'tp': 2.5}
    return sizing

def simulate_process(inputs, sizing, adjustments=None):
    effluent_targets = sizing['effluent_targets']
    effluent_tkn = effluent_targets['tkn'] + (np.random.random() - 0.5) * 1
    effluent_tp = effluent_targets['tp'] + (np.random.random() - 0.5) * 0.2
    methanol_dose_kg = 0
    alum_dose_kg = 0

    if inputs['use_methanol']:
        target_tkn = 2.0 if sizing['tech'] in ['MBR', 'IFAS'] else 3.0
        n_to_remove = (effluent_tkn - target_tkn) * inputs['avg_flow_m3_day'] / 1000
        if n_to_remove > 0:
            methanol_dose_kg = n_to_remove * CHEMICAL_FACTORS['methanol_to_n_ratio']
            effluent_tkn = target_tkn
    
    if inputs['use_alum']:
        target_tp = 0.5 if sizing['tech'] == 'MBR' else 0.8
        p_to_remove = (effluent_tp - target_tp) * inputs['avg_flow_m3_day'] / 1000
        if p_to_remove > 0:
            alum_dose_kg = p_to_remove * CHEMICAL_FACTORS['alum_to_p_ratio']
            effluent_tp = target_tp
            
    effluent_bod = max(0, effluent_targets['bod'] + (np.random.random() - 0.5) * 3)
    effluent_tss = max(0, effluent_targets['tss'] + (np.random.random() - 0.5) * 4)

    bod_removed_kg_day = (inputs['avg_bod'] - effluent_bod) * inputs['avg_flow_m3_day'] / 1000
    vss_produced = (KINETIC_PARAMS['Y'] * bod_removed_kg_day) / (1 + KINETIC_PARAMS['kd'] * sizing.get('srt', 10))
    tss_produced = vss_produced * KINETIC_PARAMS['TSS_VSS_ratio']
    
    p_removed_chemically_kg_day = alum_dose_kg / CHEMICAL_FACTORS['alum_to_p_ratio'] if alum_dose_kg > 0 else 0
    chemical_sludge = p_removed_chemically_kg_day * 4.5
    total_sludge = tss_produced + chemical_sludge

    # --- Flow Calculations ---
    was_flow_m3d_design = (total_sludge * 1000) / (0.8 * sizing.get('mlss', 3500)) if sizing['tech'] != 'MBBR' else 0
    ras_flow_m3d_design = inputs['avg_flow_m3_day'] * 0.75 if sizing['tech'] != 'MBBR' else 0
    peak_flow_m3_hr_design = (inputs['avg_flow_m3_day'] * 2.5) / 24

    # Use adjusted values if provided
    if adjustments:
        was_flow_m3d = was_flow_m3d_design * (adjustments['was_flow_slider'] / 100)
        ras_flow_m3d = ras_flow_m3d_design * (adjustments['ras_flow_slider'] / 100)
    else:
        was_flow_m3d = was_flow_m3d_design
        ras_flow_m3d = ras_flow_m3d_design

    n_removed_bio_kg_day = (inputs['avg_tkn'] - effluent_tkn) * inputs['avg_flow_m3_day'] / 1000
    
    # --- Airflow Calculations ---
    oxygen_demand_kg_day = (bod_removed_kg_day * AERATION_PARAMS['O2_demand_BOD']) + (n_removed_bio_kg_day * AERATION_PARAMS['O2_demand_N'])
    required_air_m3_day_design = oxygen_demand_kg_day / (AERATION_PARAMS['SOTE'] * AERATION_PARAMS['O2_in_air_mass_fraction'] * AERATION_PARAMS['air_density_kg_m3'])
    
    if adjustments:
        required_air_m3_day = required_air_m3_day_design * (adjustments['air_flow_slider'] / 100)
    else:
        required_air_m3_day = required_air_m3_day_design

    flow_conv_factor = (CONVERSION_FACTORS['flow'].get(f"{inputs['flow_unit_short']}_to_m3_day", 1) or 1)
    
    return {
        'Effluent BOD (mg/L)': effluent_bod, 'Effluent TSS (mg/L)': effluent_tss,
        'Effluent TKN (mg/L)': effluent_tkn, 'Effluent TP (mg/L)': effluent_tp,
        f'RAS Flow ({inputs["flow_unit_short"]})': ras_flow_m3d / flow_conv_factor,
        f'WAS Flow ({inputs["flow_unit_short"]})': was_flow_m3d / flow_conv_factor,
        'Alum Dose (kg/day)': alum_dose_kg, 'Carbon Source Dose (kg/day)': methanol_dose_kg,
        'Total Sludge Production (kg TSS/day)': total_sludge,
        'Required Airflow (m³/hr)': required_air_m3_day / 24,
        'EQ Peak Pump Rate (m³/hr)': peak_flow_m3_hr_design,
        'EQ Valve Cv': calculate_valve_cv(peak_flow_m3_hr_design),
        'RAS Valve Cv': calculate_valve_cv(ras_flow_m3d_design / 24),
        'WAS Valve Cv': calculate_valve_cv(was_flow_m3d_design / 24)
    }

def generate_pfd_dot(inputs, sizing, results):
    """Generates a DOT string for the process flow diagram."""
    tech = sizing['tech']
    flow_unit_label = inputs['flow_unit_short']
    
    influent_label = (f"Influent\\nQ={inputs['avg_flow_input']:.1f} {flow_unit_label}")
    effluent_label = (f"Effluent\\nQ={inputs['avg_flow_input']:.1f} {flow_unit_label}")

    dot = f"""
    digraph G {{
        rankdir=LR;
        graph [fontname="Inter"];
        node [shape=box, style="rounded,filled", fillcolor="#EBF4FF", fontname="Inter"];
        edge [fontname="Inter", fontsize=10];
        
        Influent [label="{influent_label}"];
    """
    
    process_train = "EQ -> Anoxic -> Aerobic;" if tech != 'MBBR' else "EQ -> Aerobic;"
    
    dot += f"""
        subgraph cluster_main {{
            label = "{tech.upper()} Process";
            style=filled;
            color=lightgrey;
            {process_train}
        }}
    """
    
    separator = "Clarifier" if tech != 'MBR' else "Membrane Tank"
    
    if tech != 'MBBR':
        ras_flow = results[f'RAS Flow ({flow_unit_label})']
        was_flow = results[f'WAS Flow ({flow_unit_label})']
        dot += f'Aerobic -> {separator};'
        dot += f'{separator} -> Effluent [label="{effluent_label}"];'
        dot += f'{separator} -> WAS [style=dashed, label="WAS\\n{was_flow:.2f} {flow_unit_label}"];'
        dot += f'{separator} -> RAS [style=dashed]; RAS -> Anoxic [style=dashed, label="RAS\\n{ras_flow:.1f} {flow_unit_label}"];'
    else:
        dot += f'Aerobic -> {separator}; {separator} -> Effluent [label="{effluent_label}"];'

    if inputs['use_alum'] and results['Alum Dose (kg/day)'] > 0:
        alum_dose = results['Alum Dose (kg/day)']
        dot += f'Alum [shape=oval, fillcolor="#FEF3C7", label="Alum Dose\\n{alum_dose:.1f} kg/d"]; Alum -> Aerobic;'
    
    if inputs['use_methanol'] and results['Carbon Source Dose (kg/day)'] > 0:
        methanol_dose = results['Carbon Source Dose (kg/day)']
        dot += f'Methanol [shape=oval, fillcolor="#D1FAE5", label="Carbon Dose\\n{methanol_dose:.1f} kg/d"]; Methanol -> Anoxic;'
        
    dot += f"Influent -> EQ [label=\"Q={inputs['avg_flow_input']:.1f} {flow_unit_label}\"];"
    dot += "}}"
    return dot

def generate_detailed_pdf_report(inputs, sizing, results):
    pdf = PDF()
    pdf.add_page()

    pdf.chapter_title("1. Influent Design Criteria")
    pdf.chapter_body({
        f"Average Influent Flow": f"{inputs['avg_flow_input']:.2f} {inputs['flow_unit_short']}",
        "Average Influent BOD": f"{inputs['avg_bod']} mg/L", "Average Influent TSS": f"{inputs['avg_tss']} mg/L",
        "Average Influent TKN": f"{inputs['avg_tkn']} mg/L", "Average Influent TP": f"{inputs['avg_tp']} mg/L",
    })

    pdf.chapter_title("2. Equipment Sizing and Dimensions")
    sizing_header = ["Unit", "Parameter", "Value", "Units"]
    sizing_data = [
        ["Equalization", "Peak Pump Rate", f"{results['EQ Peak Pump Rate (m³/hr)']:.1f}", "m³/hr"],
        ["Equalization", "Control Valve Cv", f"{results['EQ Valve Cv']:.1f}", ""],
        ["RAS", "Control Valve Cv", f"{results['RAS Valve Cv']:.1f}", ""],
        ["WAS", "Control Valve Cv", f"{results['WAS Valve Cv']:.1f}", ""],
    ]
    for tank_name, dims in sizing['dimensions'].items():
        vol_key = [k for k in sizing if tank_name.split(' ')[0].lower() in k and 'volume' in k]
        if vol_key:
            sizing_data.append([tank_name, "Volume", f"{sizing[vol_key[0]]:,.0f}", "m³"])
        for dim_name, dim_val in dims.items():
            sizing_data.append([tank_name, dim_name.split(' ')[0], dim_val, dim_name.split(' ')[1].replace('(', '').replace(')', '')])
    pdf.create_table(sizing_header, sizing_data, col_widths=[45, 45, 45, 45])

    pdf.chapter_title("3. Process Flow Diagram")
    dot_string = generate_pfd_dot(inputs, sizing, results)
    s = Source(dot_string, format="png")
    png_data = s.pipe()
    with io.BytesIO(png_data) as png_file:
        pdf.image(png_file, x=10, w=pdf.w - 20)
    pdf.ln(5)

    pdf.chapter_title("4. Performance & Operational Summary")
    perf_header = ["Parameter", "Value", "Units"]
    perf_data = []
    for key, val in results.items():
        if isinstance(val, (int, float)) and val > 0.01:
            unit = key.split('(')[-1].replace(')', '') if '(' in key else 'kg/day'
            param = key.split('(')[0].strip()
            perf_data.append([param, f"{val:.2f}", unit])
    pdf.create_table(perf_header, perf_data, col_widths=[90, 45, 45])

    return pdf.output(dest='S').encode('latin-1')

def display_output(tech_name, inputs, sizing, results, rerun_key_prefix):
    """Renders the output for a single technology tab."""
    st.header(f"{tech_name} Design Summary")
    
    # --- Initial Design Display ---
    is_us = 'US Customary' in inputs['flow_unit_name']
    vol_unit = 'gal' if is_us else 'm³'
    vol_factor = CONVERSION_FACTORS['volume']['m3_to_gal'] if is_us else 1
    
    col1, col2, col3, col4 = st.columns(4)
    if 'total_volume' in sizing:
        col1.metric("Total Basin Volume", f"{sizing['total_volume'] * vol_factor:,.0f} {vol_unit}")
    if 'hrt' in sizing:
        col2.metric("HRT", f"{sizing['hrt']:.1f} hours")
    if 'srt' in sizing:
        col3.metric("SRT", f"{sizing['srt']:.1f} days")
    if 'Required Airflow (m³/hr)' in results:
        col4.metric("Design Airflow", f"{results['Required Airflow (m³/hr)']:.0f} m³/hr")

    with st.expander("View Initial Design Details"):
        st.subheader("Process Flow Diagram (Initial Design)")
        pfd_dot_string = generate_pfd_dot(inputs, sizing, results)
        st.graphviz_chart(pfd_dot_string)

        st.subheader("Performance & Operational Summary (Initial Design)")
        results_df = pd.DataFrame.from_dict(results, orient='index', columns=['Value'])
        results_df = results_df[results_df.apply(lambda x: isinstance(x[0], (int, float)) and x[0] > 0.01, axis=1)]
        st.dataframe(results_df.style.format("{:,.2f}"))

        pdf_data = generate_detailed_pdf_report(inputs, sizing, results)
        st.download_button(
            label="⬇️ Download Initial Design Report (PDF)",
            data=pdf_data,
            file_name=f"AquaGenius_{tech_name}_Initial_Report.pdf",
            mime="application/pdf"
        )
    
    st.markdown("---")
    # --- Re-run Simulation Section ---
    st.header("Operational Adjustments & Re-run")
    
    # Use unique keys for each technology's sliders
    eq_key = f"{rerun_key_prefix}_eq_slider"
    ras_key = f"{rerun_key_prefix}_ras_slider"
    was_key = f"{rerun_key_prefix}_was_slider"
    air_key = f"{rerun_key_prefix}_air_slider"

    adj_eq_flow = st.slider("EQ Pump Flow (% of Design)", 0, 150, 100, 5, key=eq_key)
    adj_ras_flow = st.slider("RAS Pump Flow (% of Design)", 0, 150, 100, 5, key=ras_key)
    adj_was_flow = st.slider("WAS Pump Flow (% of Design)", 0, 150, 100, 5, key=was_key)
    adj_air_flow = st.slider("Air Blower Flow (% of Design)", 0, 150, 100, 5, key=air_key)

    if st.button("Re-run Simulation with Adjustments", key=f"rerun_{rerun_key_prefix}"):
        adjustments = {
            'eq_flow_slider': adj_eq_flow, 'ras_flow_slider': adj_ras_flow,
            'was_flow_slider': adj_was_flow, 'air_flow_slider': adj_air_flow
        }
        rerun_results = simulate_process(inputs, sizing, adjustments)
        st.session_state.rerun_results[rerun_key_prefix] = rerun_results

    if rerun_key_prefix in st.session_state.rerun_results:
        st.subheader("Adjusted Performance Summary")
        rerun_df = pd.DataFrame.from_dict(st.session_state.rerun_results[rerun_key_prefix], orient='index', columns=['Value'])
        rerun_df = rerun_df[rerun_df.apply(lambda x: isinstance(x[0], (int, float)) and x[0] > 0.01, axis=1)]
        st.dataframe(rerun_df.style.format("{:,.2f}"))


# ==============================================================================
# --- Main App Flow ---
# ==============================================================================
if run_button:
    inputs = get_inputs()
    results_by_tech = {}
    for tech in ['cas', 'ifas', 'mbr', 'mbbr']:
        sizing_func = globals()[f"calculate_{tech}_sizing"]
        sizing = sizing_func(inputs)
        results = simulate_process(inputs, sizing)
        results_by_tech[tech] = {'sizing': sizing, 'results': results}
    
    st.session_state.simulation_data = {
        'inputs': inputs, 'results_by_tech': results_by_tech
    }
    st.session_state.rerun_results = {} # Clear re-run results on new simulation

if st.session_state.simulation_data:
    stored_data = st.session_state.simulation_data
    inputs = stored_data['inputs']
    results_by_tech = stored_data['results_by_tech']
    
    cas_tab, ifas_tab, mbr_tab, mbbr_tab = st.tabs([
        "🔹 CAS", "🔸 IFAS", "🟢 MBR", "🔺 MBBR"
    ])

    with cas_tab:
        data = results_by_tech['cas']
        display_output('CAS', inputs, data['sizing'], data['results'], 'cas')
    
    with ifas_tab:
        data = results_by_tech['ifas']
        display_output('IFAS', inputs, data['sizing'], data['results'], 'ifas')

    with mbr_tab:
        data = results_by_tech['mbr']
        display_output('MBR', inputs, data['sizing'], data['results'], 'mbr')
        
    with mbbr_tab:
        data = results_by_tech['mbbr']
        display_output('MBBR', inputs, data['sizing'], data['results'], 'mbbr')
else:
    st.info("Please configure your influent criteria in the sidebar and click 'Generate Design & Simulate'.")

