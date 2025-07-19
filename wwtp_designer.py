import streamlit as st
import pandas as pd
import numpy as np

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
    'flow': {'MGD_to_m3_day': 3785.41, 'MLD_to_m3_day': 1000},
    'volume': {'m3_to_gal': 264.172},
    'area': {'m2_to_ft2': 10.7639},
    'sor': {'m3_m2_day_to_gpd_ft2': 24.54}
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
if 'simulation_results' not in st.session_state:
    st.session_state.simulation_results = None

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

    # Extract unit from selection for display
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
# --- Core Logic Functions (Translated from JS) ---
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
        'flow_unit_name': flow_unit_name,
        'flow_unit_short': flow_unit_short,
        'avg_flow_input': avg_flow_input,
        'avg_flow_m3_day': avg_flow_m3_day,
        'avg_bod': avg_bod,
        'avg_tss': avg_tss,
        'avg_tkn': avg_tkn,
        'avg_tp': avg_tp,
        'use_alum': use_alum,
        'use_methanol': use_methanol,
    }

def calculate_cas_sizing(inputs):
    srt = 10
    mlss = 3500
    effluent_bod = 10.0
    hrt = (srt * KINETIC_PARAMS['Y'] * (inputs['avg_bod'] - effluent_bod)) / (mlss * (1 + KINETIC_PARAMS['kd'] * srt)) * 24
    total_volume = inputs['avg_flow_m3_day'] * hrt / 24
    anoxic_fraction = 0.3
    anoxic_volume = total_volume * anoxic_fraction
    aerobic_volume = total_volume * (1 - anoxic_fraction)
    clarifier_sor = 24
    clarifier_area = inputs['avg_flow_m3_day'] / clarifier_sor
    return {
        'tech': 'CAS', 'srt': srt, 'mlss': mlss, 'hrt': hrt, 'total_volume': total_volume,
        'anoxic_volume': anoxic_volume, 'aerobic_volume': aerobic_volume,
        'clarifier_area': clarifier_area, 'clarifier_sor': clarifier_sor,
        'effluent_targets': {'bod': 10, 'tss': 12, 'tkn': 8, 'tp': 2.0}
    }

def calculate_ifas_sizing(inputs):
    srt = 8
    mlss = 3000
    media_fill = 0.4
    ssa = 500
    hrt = 6
    total_volume = inputs['avg_flow_m3_day'] * hrt / 24
    anoxic_volume = total_volume * 0.3
    aerobic_volume = total_volume * 0.7
    media_volume = aerobic_volume * media_fill
    clarifier_sor = 28
    clarifier_area = inputs['avg_flow_m3_day'] / clarifier_sor
    return {
        'tech': 'IFAS', 'srt': srt, 'mlss': mlss, 'hrt': hrt, 'total_volume': total_volume,
        'anoxic_volume': anoxic_volume, 'aerobic_volume': aerobic_volume,
        'clarifier_area': clarifier_area, 'clarifier_sor': clarifier_sor,
        'media_volume': media_volume, 'ssa': ssa,
        'effluent_targets': {'bod': 8, 'tss': 10, 'tkn': 5, 'tp': 1.5}
    }

def calculate_mbr_sizing(inputs):
    srt = 15
    mlss = 8000
    hrt = 5
    total_volume = inputs['avg_flow_m3_day'] * hrt / 24
    anoxic_volume = total_volume * 0.4
    aerobic_volume = total_volume * 0.6
    membrane_flux = 20
    membrane_area = (inputs['avg_flow_m3_day'] * 1000 / 24) / membrane_flux
    return {
        'tech': 'MBR', 'srt': srt, 'mlss': mlss, 'hrt': hrt, 'total_volume': total_volume,
        'anoxic_volume': anoxic_volume, 'aerobic_volume': aerobic_volume,
        'membrane_area': membrane_area, 'membrane_flux': membrane_flux,
        'effluent_targets': {'bod': 5, 'tss': 1, 'tkn': 4, 'tp': 1.0}
    }

def calculate_mbbr_sizing(inputs):
    hrt = 4
    total_volume = inputs['avg_flow_m3_day'] * hrt / 24
    aerobic_volume = total_volume
    media_fill = 0.5
    ssa = 500
    media_volume = aerobic_volume * media_fill
    bod_loading_rate = 5
    required_media_area = (inputs['avg_flow_m3_day'] * inputs['avg_bod'] / 1000) / bod_loading_rate
    required_media_volume = required_media_area / ssa
    final_aerobic_volume = required_media_volume / media_fill
    return {
        'tech': 'MBBR', 'hrt': hrt, 'total_volume': final_aerobic_volume,
        'aerobic_volume': final_aerobic_volume, 'media_volume': required_media_volume, 'ssa': ssa,
        'effluent_targets': {'bod': 15, 'tss': 20, 'tkn': 10, 'tp': 2.5}
    }

def simulate_process(inputs, sizing):
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

    was_flow_m3d = (total_sludge * 1000) / (0.8 * sizing.get('mlss', 3500)) if sizing['tech'] != 'MBBR' else 0
    ras_flow_m3d = inputs['avg_flow_m3_day'] * 0.75 if sizing['tech'] != 'MBBR' else 0

    n_removed_bio_kg_day = (inputs['avg_tkn'] - effluent_tkn) * inputs['avg_flow_m3_day'] / 1000
    oxygen_demand_kg_day = (bod_removed_kg_day * AERATION_PARAMS['O2_demand_BOD']) + (n_removed_bio_kg_day * AERATION_PARAMS['O2_demand_N'])
    required_air_m3_day = oxygen_demand_kg_day / (AERATION_PARAMS['SOTE'] * AERATION_PARAMS['O2_in_air_mass_fraction'] * AERATION_PARAMS['air_density_kg_m3'])
    
    return {
        'Effluent BOD (mg/L)': effluent_bod, 'Effluent TSS (mg/L)': effluent_tss,
        'Effluent TKN (mg/L)': effluent_tkn, 'Effluent TP (mg/L)': effluent_tp,
        f'RAS Flow ({inputs["flow_unit_short"]})': ras_flow_m3d / (CONVERSION_FACTORS['flow'].get(f"{inputs['flow_unit_short']}_to_m3_day", 1) or 1),
        f'WAS Flow ({inputs["flow_unit_short"]})': was_flow_m3d / (CONVERSION_FACTORS['flow'].get(f"{inputs['flow_unit_short']}_to_m3_day", 1) or 1),
        'Alum Dose (kg/day)': alum_dose_kg, 'Carbon Source Dose (kg/day)': methanol_dose_kg,
        'Total Sludge Production (kg TSS/day)': total_sludge,
        'Required Airflow (m³/hr)': required_air_m3_day / 24
    }

def generate_pfd_dot(inputs, sizing, results):
    """Generates a DOT string for the process flow diagram."""
    tech = sizing['tech']
    flow_unit_label = inputs['flow_unit_short']
    
    influent_label = (f"Influent\\nQ={inputs['avg_flow_input']:.1f} {flow_unit_label}\\n"
                      f"BOD={inputs['avg_bod']} mg/L\\nTSS={inputs['avg_tss']} mg/L\\n"
                      f"TKN={inputs['avg_tkn']} mg/L\\nTP={inputs['avg_tp']} mg/L")
    
    effluent_label = (f"Effluent\\nQ={inputs['avg_flow_input']:.1f} {flow_unit_label}\\n"
                      f"BOD={results['Effluent BOD (mg/L)']:.1f} mg/L\\n"
                      f"TSS={results['Effluent TSS (mg/L)']:.1f} mg/L\\n"
                      f"TKN={results['Effluent TKN (mg/L)']:.1f} mg/L\\n"
                      f"TP={results['Effluent TP (mg/L)']:.1f} mg/L")

    dot = f"""
    digraph G {{
        rankdir=LR;
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
        
    dot += "Influent -> EQ; }"
    return dot

def display_output(tech_name, inputs, sizing, results):
    """Renders the output for a single technology tab."""
    st.header(f"{tech_name} Design Summary")
    
    # Sizing Metrics
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
        col4.metric("Required Airflow", f"{results['Required Airflow (m³/hr)']:.0f} m³/hr")

    # Process Flow Diagram
    with st.container():
        st.subheader("Process Flow Diagram")
        pfd_dot_string = generate_pfd_dot(inputs, sizing, results)
        st.graphviz_chart(pfd_dot_string)

    # Performance Table
    with st.container():
        st.subheader("Performance & Operational Summary")
        results_df = pd.DataFrame.from_dict(results, orient='index', columns=['Value'])
        results_df = results_df[results_df['Value'] > 0.01] # Hide zero values
        st.dataframe(results_df.style.format("{:,.2f}"))

# ==============================================================================
# --- Main App Flow ---
# ==============================================================================
if run_button:
    inputs = get_inputs()
    all_results = {}
    for tech in ['cas', 'ifas', 'mbr', 'mbbr']:
        sizing_func = globals()[f"calculate_{tech}_sizing"]
        sizing = sizing_func(inputs)
        results = simulate_process(inputs, sizing)
        all_results[tech] = {'sizing': sizing, 'results': results}
    st.session_state.simulation_results = all_results

if st.session_state.simulation_results:
    inputs = get_inputs() # Re-get inputs to ensure units are current for display
    
    cas_tab, ifas_tab, mbr_tab, mbbr_tab = st.tabs([
        "🔹 Conventional Activated Sludge (CAS)", 
        "🔸 Integrated Fixed-Film (IFAS)", 
        "🟢 Membrane Bioreactor (MBR)", 
        "🔺 Moving Bed Biofilm (MBBR)"
    ])

    with cas_tab:
        data = st.session_state.simulation_results['cas']
        display_output('CAS', inputs, data['sizing'], data['results'])
    
    with ifas_tab:
        data = st.session_state.simulation_results['ifas']
        display_output('IFAS', inputs, data['sizing'], data['results'])

    with mbr_tab:
        data = st.session_state.simulation_results['mbr']
        display_output('MBR', inputs, data['sizing'], data['results'])
        
    with mbbr_tab:
        data = st.session_state.simulation_results['mbbr']
        display_output('MBBR', inputs, data['sizing'], data['results'])
else:
    st.info("Please configure your influent criteria in the sidebar and click 'Generate Design & Simulate'.")

