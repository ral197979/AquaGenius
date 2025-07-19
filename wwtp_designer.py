import streamlit as st
import pandas as pd
import numpy as np
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from graphviz import Source
import io
import os
import tempfile

# ==============================================================================
# --- Page Configuration & Styling ---
# ==============================================================================
st.set_page_config(
    page_title="AquaGenius WWTP Designer",
    page_icon="🌊",
    layout="wide"
)

st.markdown("""
    <style>
    .stButton>button {
        background-color: #0068C9;
        color: white;
        border-radius: 8px;
        border: 1px solid #0068C9;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #0055A4;
        border-color: #0055A4;
    }
    </style>
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
    'Y': 0.6, 'kd': 0.06, 'fd': 0.15, 'TSS_VSS_ratio': 1.25, 'VSS_TSS_ratio': 0.8
}

AERATION_PARAMS = {
    'O2_demand_BOD': 1.5, 'O2_demand_N': 4.57, 'SOTE': 0.30,
    'O2_in_air_mass_fraction': 0.232, 'air_density_kg_m3': 1.225
}

CHEMICAL_FACTORS = {
    'alum_to_p_ratio': 9.7, 'methanol_to_n_ratio': 2.86,
    'naoh_to_h2s_ratio': 2.5,
    'naocl_to_h2s_ratio': 4.5,
    'h2so4_to_nh3_ratio': 0.6
}

CHEMICAL_PROPERTIES = {
    'Sodium Hydroxide': {'mw': 40.0, 'density_kg_L': 1.52},
    'Sodium Hypochlorite': {'mw': 74.44, 'density_kg_L': 1.21},
    'Sulfuric Acid': {'mw': 98.07, 'density_kg_L': 1.84}
}

CONTAMINANT_PROPERTIES = {
    'H2S': {'mw': 34.08},
    'NH3': {'mw': 17.03}
}

SOLIDS_PARAMS = {
    'biogas_yield_m3_kg_vsr': 0.5,
    'methane_content_percent': 65,
    'polymer_dose_thickening_kg_ton': 4,
    'polymer_dose_dewatering_kg_ton': 8
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

    # --- CSV Upload Section ---
    uploaded_file = st.file_uploader("Upload Design Criteria CSV", type=['csv'])
    with st.expander("CSV Format Example"):
        st.code("""
Parameter,Value
Flow,10000
BOD,250
TSS,220
TKN,40
TP,7
        """)
        sample_csv = "Parameter,Value\nFlow,10000\nBOD,250\nTSS,220\nTKN,40\nTP,7"
        st.download_button(
           label="Download Sample CSV",
           data=sample_csv,
           file_name='sample_design_criteria.csv',
           mime='text/csv',
        )

    # --- Initialize default values ---
    default_values = {
        'Flow': 10000.0, 'BOD': 250, 'TSS': 220, 'TKN': 40, 'TP': 7
    }

    # --- Read from CSV if uploaded ---
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            # Create a dictionary from the CSV
            uploaded_values = pd.Series(df.Value.values, index=df.Parameter).to_dict()
            # Update default values with uploaded values
            default_values.update(uploaded_values)
            st.success("Data loaded from CSV!")
        except Exception as e:
            st.error(f"Error reading CSV file: {e}")
    
    flow_unit_name = st.selectbox(
        "Unit System",
        ('Metric (m³/day)', 'US Customary (MGD)', 'SI (MLD)'),
        key='flow_unit_select'
    )

    unit_display = flow_unit_name.split('(')[-1].replace(')', '')

    avg_flow_input = st.number_input(
        f"Average Influent Flow ({unit_display})",
        min_value=0.1, value=float(default_values['Flow']), step=100.0, format="%.2f"
    )
    
    st.markdown("---")
    
    avg_bod = st.number_input("Average Influent BOD (mg/L)", 50, value=int(default_values['BOD']), step=10)
    avg_tss = st.number_input("Average Influent TSS (mg/L)", 50, value=int(default_values['TSS']), step=10)
    avg_tkn = st.number_input("Average Influent TKN (mg/L)", 10, value=int(default_values['TKN']), step=5)
    avg_tp = st.number_input("Average Influent TP (mg/L)", 1, value=int(default_values['TP']), step=1)

    st.markdown("---")
    st.header("💨 Air Treatment Criteria")
    air_flow_m3_hr = st.number_input("Airflow to Treat (m³/hr)", min_value=100.0, value=5000.0, step=100.0)
    h2s_in_ppm = st.number_input("Inlet H2S Concentration (ppm)", min_value=0, value=50, step=5)
    nh3_in_ppm = st.number_input("Inlet NH3 Concentration (ppm)", min_value=0, value=20, step=5)
    
    st.subheader("Chemical Selection")
    acid_chemical = st.selectbox("Acid Stage Chemical (for NH3)", ['Sulfuric Acid'])
    acid_conc = st.number_input("Acid Concentration (%)", min_value=1.0, value=93.0, step=0.5)
    
    caustic_chemical = st.selectbox("Caustic/Oxidation Stage Chemical (for H2S)", ['Sodium Hydroxide', 'Sodium Hypochlorite'])
    caustic_conc = st.number_input("Caustic/Oxidation Conc. (%)", min_value=1.0, value=12.5, step=0.5)

    st.markdown("---")
    st.header("🧱 Solids Handling Criteria")
    target_thickened_solids = st.slider("Target Thickened Solids (%)", 2, 8, 4, 1)
    target_cake_solids = st.slider("Target Dewatering Cake Solids (%)", 15, 35, 25, 1)
    target_vsr = st.slider("Target Digester VSR (%)", 40, 70, 55, 1)


    st.markdown("---")
    st.header("🧪 Chemical Dosing (Liquid)")
    use_alum = st.checkbox("Use Alum for P Removal")
    use_methanol = st.checkbox("Use Carbon Source for N Removal")

    run_button = st.button("Generate Design & Simulate", use_container_width=True)

# ==============================================================================
# --- PDF Generation Class ---
# ==============================================================================
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'AquaGenius - WWTP Design Report', border=0, ln=1, align='C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', border=0, ln=0, align='C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 6, title, border=0, ln=1, align='L')
        self.ln(4)

    def chapter_body(self, data):
        self.set_font('Arial', '', 10)
        key_width = 70
        value_width = self.w - self.r_margin - self.l_margin - key_width
        
        for k, v in data.items():
            self.set_font('Arial', 'B', 10)
            self.cell(key_width, 5, f"- {k}:", align='L')
            self.set_font('Arial', '', 10)
            self.multi_cell(value_width, 5, str(v), align='L')
            
        self.ln()

    def create_table(self, header, data, col_widths):
        self.set_font('Arial', 'B', 9)
        self.set_fill_color(220, 220, 220)
        for i, h in enumerate(header):
            self.cell(col_widths[i], 7, h, border=1, ln=0, align='C', fill=1)
        self.ln()
        self.set_font('Arial', '', 9)
        for row in data:
            for i, item in enumerate(row):
                self.cell(col_widths[i], 6, str(item), border=1, ln=0)
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
        'air_flow_m3_hr': air_flow_m3_hr, 'h2s_in_ppm': h2s_in_ppm, 'nh3_in_ppm': nh3_in_ppm,
        'acid_chemical': acid_chemical, 'acid_conc': acid_conc,
        'caustic_chemical': caustic_chemical, 'caustic_conc': caustic_conc,
        'target_thickened_solids': target_thickened_solids,
        'target_cake_solids': target_cake_solids, 'target_vsr': target_vsr,
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

def calculate_scrubber_sizing(inputs):
    sizing = {'tech': 'Scrubber'}
    ebrt_s = 30 # Empty Bed Residence Time in seconds
    gas_velocity_m_s = 0.5
    
    air_flow_m3_s = inputs['air_flow_m3_hr'] / 3600
    sizing['media_volume'] = air_flow_m3_s * ebrt_s
    vessel_area = air_flow_m3_s / gas_velocity_m_s
    vessel_diameter = (4 * vessel_area / np.pi) ** 0.5
    media_height = sizing['media_volume'] / vessel_area
    
    sizing['dimensions'] = {
        'Scrubber Vessel': calculate_tank_dimensions(vessel_area, shape='circ', depth=media_height)
    }
    sizing['recirculation_flow_m3_hr'] = inputs['air_flow_m3_hr'] * 0.01 # Heuristic
    sizing['effluent_targets'] = {'removal_eff': 99.0}
    return sizing

def calculate_solids_sizing(inputs):
    # Use CAS sludge production as basis for solids handling design
    cas_sizing = calculate_cas_sizing(inputs)
    cas_results = simulate_process(inputs, cas_sizing)
    total_sludge_kg_day = cas_results['Total Sludge Production (kg TSS/day)']
    
    sizing = {'tech': 'Solids'}
    # Thickener Sizing
    gbt_loading_kg_hr_m = 500 # kg/hr/m
    gbt_width_m = (total_sludge_kg_day / 24) / gbt_loading_kg_hr_m
    sizing['gbt_width_m'] = gbt_width_m

    # Anaerobic Digester Sizing
    thickened_sludge_volume_m3_day = total_sludge_kg_day / (inputs['target_thickened_solids'] / 100 * 1000)
    vs_loading_kg_day = total_sludge_kg_day * KINETIC_PARAMS['VSS_TSS_ratio']
    vs_loading_rate_kg_m3_d = 2.4 # kg VS/m3/d
    digester_volume = vs_loading_kg_day / vs_loading_rate_kg_m3_d
    
    sizing['dimensions'] = {
        'Anaerobic Digester': calculate_tank_dimensions(digester_volume, shape='circ', depth=10)
    }
    sizing['effluent_targets'] = {
        'cake_solids': inputs['target_cake_solids'],
        'vsr': inputs['target_vsr']
    }
    return sizing

def simulate_process(inputs, sizing, adjustments=None):
    tech = sizing['tech']
    
    if tech == 'Scrubber':
        results = {}
        # H2S Removal
        h2s_props = CONTAMINANT_PROPERTIES['H2S']
        h2s_in_mg_m3 = inputs['h2s_in_ppm'] * (h2s_props['mw'] / 24.45)
        h2s_loading_kg_day = (inputs['air_flow_m3_hr'] * 24 * h2s_in_mg_m3) / 1_000_000
        
        # NH3 Removal
        nh3_props = CONTAMINANT_PROPERTIES['NH3']
        nh3_in_mg_m3 = inputs['nh3_in_ppm'] * (nh3_props['mw'] / 24.45)
        nh3_loading_kg_day = (inputs['air_flow_m3_hr'] * 24 * nh3_in_mg_m3) / 1_000_000
        
        design_removal_eff = sizing['effluent_targets']['removal_eff']
        
        if adjustments:
            fan_factor = adjustments['fan_speed_slider'] / 100
            acid_pump_factor = adjustments['acid_pump_slider'] / 100
            caustic_pump_factor = adjustments['caustic_pump_slider'] / 100
            
            h2s_removal_eff = min(design_removal_eff * caustic_pump_factor * (1/fan_factor if fan_factor > 0 else 1), 99.9)
            nh3_removal_eff = min(design_removal_eff * acid_pump_factor * (1/fan_factor if fan_factor > 0 else 1), 99.9)
        else:
            h2s_removal_eff = design_removal_eff
            nh3_removal_eff = design_removal_eff
        
        # H2S Results
        h2s_removed_kg_day = h2s_loading_kg_day * (h2s_removal_eff / 100)
        results['Outlet H2S (ppm)'] = inputs['h2s_in_ppm'] * (1 - h2s_removal_eff / 100)
        results['H2S Removal Efficiency (%)'] = h2s_removal_eff
        
        # NH3 Results
        nh3_removed_kg_day = nh3_loading_kg_day * (nh3_removal_eff / 100)
        results['Outlet NH3 (ppm)'] = inputs['nh3_in_ppm'] * (1 - nh3_removal_eff / 100)
        results['NH3 Removal Efficiency (%)'] = nh3_removal_eff

        # Caustic/Oxidation Chemical Consumption
        caustic_chem_props = CHEMICAL_PROPERTIES[inputs['caustic_chemical']]
        if inputs['caustic_chemical'] == 'Sodium Hydroxide':
            caustic_stoich_ratio = CHEMICAL_FACTORS['naoh_to_h2s_ratio'] * (caustic_chem_props['mw'] / h2s_props['mw'])
        else: # Sodium Hypochlorite
            caustic_stoich_ratio = CHEMICAL_FACTORS['naocl_to_h2s_ratio'] * (caustic_chem_props['mw'] / h2s_props['mw'])
        
        pure_caustic_kg_day = h2s_removed_kg_day * caustic_stoich_ratio
        solution_caustic_kg_day = pure_caustic_kg_day / (inputs['caustic_conc'] / 100)
        solution_caustic_L_day = solution_caustic_kg_day / caustic_chem_props['density_kg_L']
        
        results[f"{inputs['caustic_chemical']} Consumption (kg/day)"] = solution_caustic_kg_day
        results[f"{inputs['caustic_chemical']} Dosing Rate (L/day)"] = solution_caustic_L_day
        results['Caustic Dosing Pump Capacity (L/hr)'] = (solution_caustic_L_day / 24) * 1.25

        # Acid Chemical Consumption
        acid_chem_props = CHEMICAL_PROPERTIES[inputs['acid_chemical']]
        acid_stoich_ratio = CHEMICAL_FACTORS['h2so4_to_nh3_ratio'] * (acid_chem_props['mw'] / nh3_props['mw'])
        pure_acid_kg_day = nh3_removed_kg_day * acid_stoich_ratio
        solution_acid_kg_day = pure_acid_kg_day / (inputs['acid_conc'] / 100)
        solution_acid_L_day = solution_acid_kg_day / acid_chem_props['density_kg_L']

        results[f"{inputs['acid_chemical']} Consumption (kg/day)"] = solution_acid_kg_day
        results[f"{inputs['acid_chemical']} Dosing Rate (L/day)"] = solution_acid_L_day
        results['Acid Dosing Pump Capacity (L/hr)'] = (solution_acid_L_day / 24) * 1.25
        
        results['Recirculation Pump Flow (m³/hr)'] = sizing['recirculation_flow_m3_hr']
        return results

    if tech == 'Solids':
        cas_sizing = calculate_cas_sizing(inputs)
        cas_results = simulate_process(inputs, cas_sizing)
        total_sludge_kg_day = cas_results['Total Sludge Production (kg TSS/day)']
        
        thickening_polymer_kg_day = (total_sludge_kg_day / 1000) * SOLIDS_PARAMS['polymer_dose_thickening_kg_ton']

        vs_in_kg_day = total_sludge_kg_day * KINETIC_PARAMS['VSS_TSS_ratio']
        
        vsr_eff = sizing['effluent_targets']['vsr']
        if adjustments:
            vsr_eff *= adjustments['digester_mixing_slider'] / 100

        vs_destroyed_kg_day = vs_in_kg_day * (vsr_eff / 100)
        biogas_m3_day = vs_destroyed_kg_day * SOLIDS_PARAMS['biogas_yield_m3_kg_vsr']
        
        digested_sludge_kg_day = total_sludge_kg_day - vs_destroyed_kg_day
        
        cake_solids_pct = sizing['effluent_targets']['cake_solids']
        if adjustments:
            cake_solids_pct *= adjustments['dewatering_polymer_slider'] / 100
        
        cake_solids_pct = min(cake_solids_pct, 40)
        final_cake_kg_day = digested_sludge_kg_day / (cake_solids_pct / 100)
        dewatering_polymer_kg_day = (digested_sludge_kg_day / 1000) * SOLIDS_PARAMS['polymer_dose_dewatering_kg_ton']

        return {
            "Biogas Production (m³/day)": biogas_m3_day,
            "Methane Production (m³/day)": biogas_m3_day * (SOLIDS_PARAMS['methane_content_percent'] / 100),
            "Volatile Solids Reduction (%)": vsr_eff,
            "Dewatered Cake Production (kg/day)": final_cake_kg_day,
            "Thickening Polymer Consumption (kg/day)": thickening_polymer_kg_day,
            "Dewatering Polymer Consumption (kg/day)": dewatering_polymer_kg_day
        }

    # --- Wastewater Simulation ---
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

    was_flow_m3d_design = (total_sludge * 1000) / (0.8 * sizing.get('mlss', 3500)) if sizing['tech'] != 'MBBR' else 0
    ras_flow_m3d_design = inputs['avg_flow_m3_day'] * 0.75 if sizing['tech'] != 'MBBR' else 0
    peak_flow_m3_hr_design = (inputs['avg_flow_m3_day'] * 2.5) / 24

    if adjustments:
        current_mlss = adjustments.get('adj_mlss', sizing.get('mlss', 3500))
        was_flow_m3d_design = (total_sludge * 1000) / (0.8 * current_mlss)
        was_flow_m3d = was_flow_m3d_design * (adjustments['was_flow_slider'] / 100)
        ras_flow_m3d = ras_flow_m3d_design * (adjustments['ras_flow_slider'] / 100)
    else:
        was_flow_m3d = was_flow_m3d_design
        ras_flow_m3d = ras_flow_m3d_design

    n_removed_bio_kg_day = (inputs['avg_tkn'] - effluent_tkn) * inputs['avg_flow_m3_day'] / 1000
    
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
        'RAS Design Flow (m³/hr)': ras_flow_m3d_design / 24,
        'WAS Design Flow (m³/hr)': was_flow_m3d_design / 24,
        'EQ Valve Cv': calculate_valve_cv(peak_flow_m3_hr_design),
        'RAS Valve Cv': calculate_valve_cv(ras_flow_m3d_design / 24),
        'WAS Valve Cv': calculate_valve_cv(was_flow_m3d_design / 24)
    }

def generate_pfd_dot(inputs, sizing, results):
    """Generates a DOT string for the process flow diagram."""
    tech = sizing['tech']
    
    if tech == 'Scrubber':
        inlet_label = f"Inlet Air\\n{inputs['air_flow_m3_hr']:.0f} m³/hr\\n{inputs['h2s_in_ppm']} ppm H2S\\n{inputs['nh3_in_ppm']} ppm NH3"
        outlet_label = f"Treated Air\\n{results['Outlet H2S (ppm)']:.1f} ppm H2S\\n{results['Outlet NH3 (ppm)']:.1f} ppm NH3"
        acid_rate_key = f"{inputs['acid_chemical']} Dosing Rate (L/day)"
        caustic_rate_key = f"{inputs['caustic_chemical']} Dosing Rate (L/day)"
        dot = f"""
        digraph G {{
            rankdir=LR;
            graph [fontname="Inter"];
            node [shape=box, style="rounded,filled", fillcolor="#EBF4FF", fontname="Inter"];
            edge [fontname="Inter", fontsize=10];
            
            InletAir [label="{inlet_label}"];
            Scrubber [label="2-Stage Scrubber Vessel"];
            TreatedAir [label="{outlet_label}"];
            AcidChem [shape=oval, fillcolor="#D1FAE5", label="{inputs['acid_chemical']}\\n{results[acid_rate_key]:.1f} L/day"];
            CausticChem [shape=oval, fillcolor="#FEF3C7", label="{inputs['caustic_chemical']}\\n{results[caustic_rate_key]:.1f} L/day"];
            
            InletAir -> Scrubber;
            Scrubber -> TreatedAir;
            AcidChem -> Scrubber;
            CausticChem -> Scrubber;
        }}
        """
        return dot
    
    if tech == 'Solids':
        dot = f"""
        digraph G {{
            rankdir=LR;
            graph [fontname="Inter"];
            node [shape=box, style="rounded,filled", fillcolor="#EBF4FF", fontname="Inter"];
            edge [fontname="Inter", fontsize=10];
            
            SludgeIn [label="Sludge from WWTP"];
            Thickener [label="Sludge Thickener"];
            Digester [label="Anaerobic Digester"];
            Dewatering [label="Dewatering"];
            Biosolids [label="Final Biosolids\\n{results['Dewatered Cake Production (kg/day)']:.0f} kg/day"];
            Biogas [shape=oval, fillcolor="#FEF3C7", label="Biogas\\n{results['Biogas Production (m³/day)']:.0f} m³/day"];
            ThickeningPolymer [shape=oval, fillcolor="#D1FAE5", label="Polymer\\n{results['Thickening Polymer Consumption (kg/day)']:.1f} kg/day"];
            DewateringPolymer [shape=oval, fillcolor="#D1FAE5", label="Polymer\\n{results['Dewatering Polymer Consumption (kg/day)']:.1f} kg/day"];

            SludgeIn -> Thickener;
            Thickener -> Digester;
            Digester -> Dewatering;
            Dewatering -> Biosolids;
            Digester -> Biogas;
            ThickeningPolymer -> Thickener;
            DewateringPolymer -> Dewatering;
        }}
        """
        return dot

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
    criteria_data = {
        f"Average Influent Flow": f"{inputs['avg_flow_input']:.2f} {inputs['flow_unit_short']}",
        "Average Influent BOD": f"{inputs['avg_bod']} mg/L", "Average Influent TSS": f"{inputs['avg_tss']} mg/L",
        "Average Influent TKN": f"{inputs['avg_tkn']} mg/L", "Average Influent TP": f"{inputs['avg_tp']} mg/L",
    }
    if sizing['tech'] == 'Scrubber':
        criteria_data = {
            "Airflow to Treat": f"{inputs['air_flow_m3_hr']:.0f} m³/hr",
            "Inlet H2S Concentration": f"{inputs['h2s_in_ppm']} ppm",
            "Inlet NH3 Concentration": f"{inputs['nh3_in_ppm']} ppm",
            "Acid Stage Chemical": inputs['acid_chemical'],
            "Acid Concentration": f"{inputs['acid_conc']} %",
            "Caustic Stage Chemical": inputs['caustic_chemical'],
            "Caustic Concentration": f"{inputs['caustic_conc']} %"
        }
    pdf.chapter_body(criteria_data)

    pdf.chapter_title("2. Equipment Sizing and Dimensions")
    sizing_header = ["Unit", "Parameter", "Value", "Units"]
    sizing_data = []
    if sizing['tech'] != 'Scrubber' and sizing['tech'] != 'Solids':
        sizing_data.extend([
            ["Equalization", "Peak Pump Rate", f"{results['EQ Peak Pump Rate (m³/hr)']:.1f}", "m³/hr"],
            ["Equalization", "Control Valve Cv", f"{results['EQ Valve Cv']:.1f}", ""],
            ["RAS", "Design Flow", f"{results['RAS Design Flow (m³/hr)']:.1f}", "m³/hr"],
            ["RAS", "Control Valve Cv", f"{results['RAS Valve Cv']:.1f}", ""],
            ["WAS", "Design Flow", f"{results['WAS Design Flow (m³/hr)']:.1f}", "m³/hr"],
            ["WAS", "Control Valve Cv", f"{results['WAS Valve Cv']:.1f}", ""],
        ])
    if sizing['tech'] == 'Scrubber':
        sizing_data.extend([
            ["Acid Dosing Pump", "Capacity", f"{results['Acid Dosing Pump Capacity (L/hr)']:.2f}", "L/hr"],
            ["Caustic Dosing Pump", "Capacity", f"{results['Caustic Dosing Pump Capacity (L/hr)']:.2f}", "L/hr"]
        ])
    if sizing['tech'] == 'Solids':
        sizing_data.extend([
            ["Thickener", "GBT Width", f"{sizing['gbt_width_m']:.1f}", "m"]
        ])
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
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
        s.render(os.path.splitext(tmp_file.name)[0], cleanup=True)
        image_path = tmp_file.name
    
    pdf.image(image_path, x=10, w=pdf.w - 20)
    os.remove(image_path)
    
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
    
    is_us = 'US Customary' in inputs['flow_unit_name']
    vol_unit = 'gal' if is_us else 'm³'
    vol_factor = CONVERSION_FACTORS['volume']['m3_to_gal'] if is_us else 1
    
    col1, col2, col3, col4 = st.columns(4)
    if tech_name == 'Air Scrubber':
        col1.metric("Vessel Diameter", f"{sizing['dimensions']['Scrubber Vessel']['Diameter (m)']}", "m")
        col2.metric("Media Height", f"{sizing['dimensions']['Scrubber Vessel']['SWD (m)']}", "m")
        col3.metric("H2S Removal", f"{results['H2S Removal Efficiency (%)']:.1f}", "%")
        col4.metric("NH3 Removal", f"{results['NH3 Removal Efficiency (%)']:.1f}", "%")
    elif tech_name == 'Solids Handling':
        col1.metric("Digester Diameter", f"{sizing['dimensions']['Anaerobic Digester']['Diameter (m)']}", "m")
        col2.metric("Biogas Production", f"{results['Biogas Production (m³/day)']:.0f}", "m³/day")
        col3.metric("VSR", f"{results['Volatile Solids Reduction (%)']:.1f}", "%")
        col4.metric("Biosolids", f"{results['Dewatered Cake Production (kg/day)']:.0f}", "kg/day")
    else:
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

        if tech_name in ['Solids Handling', 'Air Scrubber']:
            st.subheader("Equipment Dimensions")
            dims_data = []
            for tank, dims in sizing['dimensions'].items():
                row = {'Unit': tank}
                row.update(dims)
                dims_data.append(row)
            st.dataframe(pd.DataFrame(dims_data).set_index('Unit'))
        
        if tech_name not in ['Air Scrubber', 'Solids Handling', 'MBBR']:
            st.subheader("Tank Dimensions")
            dims_data = []
            for tank, dims in sizing['dimensions'].items():
                row = {'Tank': tank}
                row.update(dims)
                dims_data.append(row)
            st.dataframe(pd.DataFrame(dims_data).set_index('Tank'))

            st.subheader("Pump & Blower Sizing")
            pump_data = {
                "EQ Pump": {"Design Flow (m³/hr)": results['EQ Peak Pump Rate (m³/hr)'], "Design Pressure (psi)": 20, "Valve Cv": results['EQ Valve Cv']},
                "RAS Pump": {"Design Flow (m³/hr)": results['RAS Design Flow (m³/hr)'], "Design Pressure (psi)": 20, "Valve Cv": results['RAS Valve Cv']},
                "WAS Pump": {"Design Flow (m³/hr)": results['WAS Design Flow (m³/hr)'], "Design Pressure (psi)": 20, "Valve Cv": results['WAS Valve Cv']}
            }
            st.dataframe(pd.DataFrame(pump_data).T.style.format("{:.2f}"))
        elif tech_name == 'Air Scrubber':
            st.subheader("Chemical Dosing System")
            acid_rate_key = f"{inputs['acid_chemical']} Dosing Rate (L/day)"
            caustic_rate_key = f"{inputs['caustic_chemical']} Dosing Rate (L/day)"
            chem_data = {
                "Acid Dosing Pump": {
                    "Chemical": inputs['acid_chemical'],
                    "Concentration (%)": inputs['acid_conc'],
                    "Design Rate (L/day)": results[acid_rate_key],
                    "Pump Capacity (L/hr)": results['Acid Dosing Pump Capacity (L/hr)']
                },
                "Caustic Dosing Pump": {
                    "Chemical": inputs['caustic_chemical'],
                    "Concentration (%)": inputs['caustic_conc'],
                    "Design Rate (L/day)": results[caustic_rate_key],
                    "Pump Capacity (L/hr)": results['Caustic Dosing Pump Capacity (L/hr)']
                }
            }
            st.dataframe(pd.DataFrame(chem_data).T)


        st.subheader("Performance & Operational Summary (Initial Design)")
        results_df = pd.DataFrame.from_dict(results, orient='index', columns=['Value'])
        results_df = results_df[results_df.apply(lambda x: isinstance(x.iloc[0], (int, float)) and x.iloc[0] > 0.01, axis=1)]
        st.dataframe(results_df.style.format("{:,.2f}"))

        pdf_data = generate_detailed_pdf_report(inputs, sizing, results)
        st.download_button(
            label="⬇️ Download Initial Design Report (PDF)",
            data=pdf_data,
            file_name=f"AquaGenius_{tech_name.replace(' ', '_')}_Initial_Report.pdf",
            mime="application/pdf"
        )
    
    st.markdown("---")
    st.header("Operational Adjustments & Re-run")
    
    if tech_name == 'Air Scrubber':
        fan_key = f"{rerun_key_prefix}_fan_slider"
        acid_pump_key = f"{rerun_key_prefix}_acid_pump_slider"
        caustic_pump_key = f"{rerun_key_prefix}_caustic_pump_slider"
        adj_fan_speed = st.slider("Fan Speed (% of Design)", 0, 150, 100, 5, key=fan_key)
        adj_acid_pump = st.slider("Acid Dosing Pump Rate (% of Design)", 0, 150, 100, 5, key=acid_pump_key)
        adj_caustic_pump = st.slider("Caustic Dosing Pump Rate (% of Design)", 0, 150, 100, 5, key=caustic_pump_key)
        
        if st.button("Re-run Scrubber Simulation", key=f"rerun_{rerun_key_prefix}"):
            adjustments = {'fan_speed_slider': adj_fan_speed, 'acid_pump_slider': adj_acid_pump, 'caustic_pump_slider': adj_caustic_pump}
            rerun_results = simulate_process(inputs, sizing, adjustments)
            st.session_state.rerun_results[rerun_key_prefix] = rerun_results
    elif tech_name == 'Solids Handling':
        thickening_polymer_key = f"{rerun_key_prefix}_thickening_polymer_slider"
        mixing_key = f"{rerun_key_prefix}_mixing_slider"
        dewatering_polymer_key = f"{rerun_key_prefix}_dewatering_polymer_slider"
        adj_thickening_polymer = st.slider("Thickening Polymer Dose (% of Design)", 0, 150, 100, 5, key=thickening_polymer_key)
        adj_mixing = st.slider("Digester Mixing (% of Design)", 0, 150, 100, 5, key=mixing_key)
        adj_dewatering_polymer = st.slider("Dewatering Polymer Dose (% of Design)", 0, 150, 100, 5, key=dewatering_polymer_key)

        if st.button("Re-run Solids Simulation", key=f"rerun_{rerun_key_prefix}"):
            adjustments = {'digester_mixing_slider': adj_mixing, 'dewatering_polymer_slider': adj_dewatering_polymer}
            rerun_results = simulate_process(inputs, sizing, adjustments)
            st.session_state.rerun_results[rerun_key_prefix] = rerun_results
    else: # CAS, IFAS, MBR
        eq_key = f"{rerun_key_prefix}_eq_slider"
        ras_key = f"{rerun_key_prefix}_ras_slider"
        was_key = f"{rerun_key_prefix}_was_slider"
        air_key = f"{rerun_key_prefix}_air_slider"
        mlss_key = f"{rerun_key_prefix}_mlss_slider"
        mlvss_key = f"{rerun_key_prefix}_mlvss_slider"

        def update_mlvss():
            st.session_state[mlvss_key] = st.session_state[mlss_key] * KINETIC_PARAMS['VSS_TSS_ratio']
        def update_mlss():
            st.session_state[mlss_key] = st.session_state[mlvss_key] / KINETIC_PARAMS['VSS_TSS_ratio']

        adj_eq_flow = st.slider("EQ Pump Flow (% of Design)", 0, 150, 100, 5, key=eq_key)
        adj_ras_flow = st.slider("RAS Pump Flow (% of Design)", 0, 150, 100, 5, key=ras_key)
        adj_was_flow = st.slider("WAS Pump Flow (% of Design)", 0, 150, 100, 5, key=was_key)
        adj_air_flow = st.slider("Air Blower Flow (% of Design)", 0, 150, 100, 5, key=air_key)
        
        # MLSS/MLVSS Sliders
        if tech_name in ['CAS', 'IFAS', 'MBR']:
            adj_mlss = st.slider("MLSS (mg/L)", 1500, 12000, sizing['mlss'], 100, key=mlss_key, on_change=update_mlvss)
            adj_mlvss = st.slider("MLVSS (mg/L)", 1000, 10000, int(sizing['mlss'] * KINETIC_PARAMS['VSS_TSS_ratio']), 100, key=mlvss_key, on_change=update_mlss)

        if st.button("Re-run Simulation with Adjustments", key=f"rerun_{rerun_key_prefix}"):
            adjustments = {
                'eq_flow_slider': adj_eq_flow, 'ras_flow_slider': adj_ras_flow,
                'was_flow_slider': adj_was_flow, 'air_flow_slider': adj_air_flow
            }
            if tech_name in ['CAS', 'IFAS', 'MBR']:
                adjustments['adj_mlss'] = st.session_state[mlss_key]

            rerun_results = simulate_process(inputs, sizing, adjustments)
            st.session_state.rerun_results[rerun_key_prefix] = rerun_results

    if rerun_key_prefix in st.session_state.rerun_results:
        rerun_data = st.session_state.rerun_results[rerun_key_prefix]
        st.subheader("Adjusted Performance Summary")
        rerun_df = pd.DataFrame.from_dict(rerun_data, orient='index', columns=['Value'])
        rerun_df = rerun_df[rerun_df.apply(lambda x: isinstance(x.iloc[0], (int, float)) and x.iloc[0] > 0.01, axis=1)]
        st.dataframe(rerun_df.style.format("{:,.2f}"))

        st.subheader("Adjusted Process Flow Diagram")
        adjusted_pfd_dot = generate_pfd_dot(inputs, sizing, rerun_data)
        st.graphviz_chart(adjusted_pfd_dot)


# ==============================================================================
# --- Main App Flow ---
# ==============================================================================
if run_button:
    inputs = get_inputs()
    results_by_tech = {}
    for tech in ['cas', 'ifas', 'mbr', 'mbbr', 'scrubber', 'solids']:
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
    
    cas_tab, ifas_tab, mbr_tab, mbbr_tab, scrubber_tab, solids_tab = st.tabs([
        "🔹 CAS", "🔸 IFAS", "🟢 MBR", "🔺 MBBR", "💨 Air Scrubber", "🧱 Solids Handling"
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

    with scrubber_tab:
        data = results_by_tech['scrubber']
        display_output('Air Scrubber', inputs, data['sizing'], data['results'], 'scrubber')
    
    with solids_tab:
        data = results_by_tech['solids']
        display_output('Solids Handling', inputs, data['sizing'], data['results'], 'solids')
else:
    st.info("Please configure your influent criteria in the sidebar and click 'Generate Design & Simulate'")
