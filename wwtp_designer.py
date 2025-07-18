import streamlit as st
import pandas as pd
import numpy as np
import base64
from fpdf import FPDF

# ==============================================================================
# --- Page Configuration & Styling ---
# ==============================================================================
st.set_page_config(
    page_title="AquaGenius WWTP Designer",
    page_icon="🌊",
    layout="wide"
)

def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Create a dummy css file for styling
with open("style.css", "w") as f:
    f.write("""
    /* General App Styling */
    .stApp {
        background-color: #F0F2F6;
    }
    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E0E0E0;
    }
    /* Button Styling */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #0068C9;
        background-color: #0068C9;
        color: white;
        transition: all 0.2s ease-in-out;
    }
    .stButton>button:hover {
        background-color: #0055A4;
        border-color: #0055A4;
    }
    /* Metric Card Styling */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
    }
    /* Expander Styling */
    .streamlit-expanderHeader {
        font-weight: bold;
    }
    """)

local_css("style.css")


st.markdown("""
    <div style="display: flex; align-items: center; margin-bottom: 20px;">
        <span style="font-size: 40px; margin-right: 15px;">🌊</span>
        <div>
            <h1 style="margin: 0; padding: 0;">AquaGenius WWTP Designer</h1>
            <p style="margin: 0; padding: 0; color: #555;">A Preliminary Design & Simulation Tool for Wastewater Treatment</p>
        </div>
    </div>
""", unsafe_allow_html=True)


# ==============================================================================
# --- Unit Conversion & Engineering Constants ---
# ==============================================================================
CONVERSION_FACTORS = {
    'flow': {'MGD_to_m3/day': 3785.41, 'MLD_to_m3/day': 1000},
    'concentration': {'g/L_to_mg/L': 1000},
    'volume': {'m3_to_gal': 264.172},
    'area': {'m2_to_ft2': 10.7639},
    'pump_rate': {'m3/hr_to_gpm': 4.40287},
    'length': {'m_to_ft': 3.28084},
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
for tech in ['cas', 'ifas', 'mbr', 'mbbr']:
    if f'{tech}_design_params' not in st.session_state:
        st.session_state[f'{tech}_design_params'] = {}
    if f'{tech}_results' not in st.session_state:
        st.session_state[f'{tech}_results'] = None
    if f'{tech}_sizing' not in st.session_state:
        st.session_state[f'{tech}_sizing'] = None

# ==============================================================================
# --- Core Logic Functions ---
# ==============================================================================
def generate_influent_data(flow_m3_day, bod_mg_l, tss_mg_l, tkn_mg_l, tp_mg_l):
    days = 365
    dates = pd.to_datetime(pd.date_range(start="2024-01-01", periods=days))
    flow = flow_m3_day + (flow_m3_day * 0.2 * np.sin(np.linspace(0, 2 * np.pi, days)))
    bod = bod_mg_l + (bod_mg_l * 0.3 * np.sin(np.linspace(0, 4 * np.pi, days)))
    tss = tss_mg_l + (tss_mg_l * 0.4 * np.sin(np.linspace(0, 3 * np.pi, days)))
    tkn = tkn_mg_l + (tkn_mg_l * 0.2 * np.sin(np.linspace(0, 2 * np.pi, days)))
    tp = tp_mg_l + (tp_mg_l * 0.5 * np.sin(np.linspace(0, 1 * np.pi, days)))
    
    df = pd.DataFrame({
        "Date": dates, "Flow_m3_day": flow.clip(min=0), "BOD_mg_l": bod.clip(min=0),
        "TSS_mg_l": tss.clip(min=0), "TKN_mg_l": tkn.clip(min=0), "TP_mg_l": tp.clip(min=0)
    })
    return df

def calculate_cas_design(avg_flow, avg_bod):
    design = {'srt': 10, 'mlss': 3500}
    effluent_bod_avg = 10.0
    hrt = design['srt'] * KINETIC_PARAMS['Y'] * (avg_bod - effluent_bod_avg) / (design['mlss'] * (1 + KINETIC_PARAMS['kd'] * design['srt'])) * 24
    design.update({'hrt': hrt, 'total_volume': avg_flow * hrt / 24, 'anoxic_volume': (avg_flow * hrt / 24) * 0.3})
    return design

def simulate_activated_sludge(params, influent_df, avg_flow, avg_bod, avg_tkn, avg_tp, flow_unit):
    srt, mlss, hrt, total_volume, anoxic_volume = params['srt'], params['mlss'], params['hrt'], params['total_volume'], params['anoxic_volume']
    num_rows = len(influent_df)

    effluent_bod = np.random.normal(loc=10.0, scale=1.5, size=num_rows).clip(min=5)
    effluent_tss = np.random.normal(loc=12.0, scale=2.0, size=num_rows).clip(min=5)
    effluent_tkn = np.random.normal(loc=3.0, scale=0.5, size=num_rows).clip(min=1)
    effluent_tp = np.random.normal(loc=0.8, scale=0.1, size=num_rows).clip(min=0.5)
    
    bod_removed_kg_day = (avg_bod - effluent_bod.mean()) * avg_flow / 1000
    vss_produced = (KINETIC_PARAMS['Y'] * bod_removed_kg_day) / (1 + KINETIC_PARAMS['kd'] * srt)
    tss_produced = vss_produced * KINETIC_PARAMS['TSS_VSS_ratio']
    
    was_flow_m3d = (tss_produced * 1000) / (0.8 * mlss)
    ras_flow_m3d = avg_flow * 0.75
    
    peak_flow = influent_df['Flow_m3_day'].max()
    clarifier_sor = 24 
    
    n_removed_kg_day = (avg_tkn - effluent_tkn.mean()) * avg_flow / 1000
    oxygen_demand_kg_day = (bod_removed_kg_day * AERATION_PARAMS['O2_demand_BOD']) + (n_removed_kg_day * AERATION_PARAMS['O2_demand_N'])
    required_air_m3_day = oxygen_demand_kg_day / (AERATION_PARAMS['SOTE'] * AERATION_PARAMS['O2_in_air_mass_fraction'] * AERATION_PARAMS['air_density_kg_m3'])
    
    sizing = {
        "EQ Tank Volume (m³)": avg_flow * 0.25, "EQ Peak Pump Capacity (m³/hr)": peak_flow / 24,
        "Total Basin Volume (m³)": total_volume, "Target DO (mg/L)": 2.0,
        "BOD Loading (kg/day)": avg_flow * avg_bod / 1000, "Required Airflow (m³/hr)": required_air_m3_day / 24,
        "Clarifier Area (m²)": avg_flow / clarifier_sor, "Clarifier SOR (m³/m²/day)": clarifier_sor,
        "SRT/CRT (days)": srt, "HRT (hours)": hrt,
        "Anoxic Zone Volume (m³)": anoxic_volume, "Aerobic Zone Volume (m³)": total_volume - anoxic_volume
    }
    
    p_to_remove = (influent_df['TP_mg_l'] - effluent_tp.mean()) * influent_df['Flow_m3_day'] / 1000
    alum_dose_kg = p_to_remove.clip(lower=0) * CHEMICAL_FACTORS['alum_to_p_ratio']
    n_to_remove = (influent_df['TKN_mg_l'] - effluent_tkn.mean()) * influent_df['Flow_m3_day'] / 1000
    methanol_dose_kg = n_to_remove.clip(lower=0) * CHEMICAL_FACTORS['methanol_to_n_ratio']
    chemical_sludge = (p_to_remove.clip(lower=0) * 4.5)
    total_sludge = tss_produced + chemical_sludge

    ras_flow_display, was_flow_display = (ras_flow_m3d, was_flow_m3d)
    flow_unit_label = 'm³/day'
    if 'MGD' in flow_unit:
        flow_unit_label = 'MGD'
        ras_flow_display /= CONVERSION_FACTORS['flow']['MGD_to_m3/day']
        was_flow_display /= CONVERSION_FACTORS['flow']['MGD_to_m3/day']
    elif 'MLD' in flow_unit:
        flow_unit_label = 'MLD'
        ras_flow_display /= CONVERSION_FACTORS['flow']['MLD_to_m3/day']
        was_flow_display /= CONVERSION_FACTORS['flow']['MLD_to_m3/day']

    results = pd.DataFrame({
        'Date': influent_df['Date'], 'Effluent_BOD (mg/L)': effluent_bod,
        'Effluent_TSS (mg/L)': effluent_tss, 'Effluent_TKN (mg/L)': effluent_tkn,
        'Effluent_TP (mg/L)': effluent_tp,
        f'RAS_Flow ({flow_unit_label})': ras_flow_display, 
        f'WAS_Flow ({flow_unit_label})': was_flow_display,
        'Alum_Dose (kg/day)': alum_dose_kg, 'Methanol_Dose (kg/day)': methanol_dose_kg,
        'Sludge_Production (kg TSS/day)': total_sludge
    })
    
    return results, sizing

# --- Download & Report Generation ---
def create_download_link_pdf(val, filename):
    b64 = base64.b64encode(val)
    return f'<a href="data:application/octet-stream;base64,{b64.decode()}" download="{filename}.pdf">Download Report as PDF</a>'

def generate_pdf_report(sizing, results, avg_in, unit_system):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(0, 10, 'Wastewater Treatment Plant Design Report', 0, 1, 'C')
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Sizing Summary', 0, 1, 'L')
    
    pdf.set_font('Arial', '', 10)
    for key, value in sizing.items():
        pdf.cell(0, 5, f"- {key}: {value:,.2f}", 0, 1)
        
    pdf.ln(10)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, 'Average Performance', 0, 1, 'L')
    
    pdf.set_font('Arial', '', 10)
    avg_results = results.mean(numeric_only=True)
    for idx, val in avg_results.items():
        pdf.cell(0, 5, f"- Average {idx}: {val:,.2f}", 0, 1)
        
    return pdf.output(dest='S')

# ==============================================================================
# --- UI Layout ---
# ==============================================================================
with st.sidebar:
    st.header("⚙️ Influent Design Criteria")
    flow_col1, flow_col2 = st.columns([3, 2])
    with flow_col1:
        avg_flow_input = st.number_input("Average Influent Flow", min_value=0.1, value=10000.0, step=100.0, format="%.2f")
    with flow_col2:
        flow_unit = st.selectbox("Unit System", ('Metric (m³/day)', 'US Customary (MGD)', 'SI (MLD)'), key='flow_unit_select')
    
    if 'MGD' in flow_unit:
        avg_flow = avg_flow_input * CONVERSION_FACTORS['flow']['MGD_to_m3/day']
    elif 'MLD' in flow_unit:
        avg_flow = avg_flow_input * CONVERSION_FACTORS['flow']['MLD_to_m3/day']
    else: 
        avg_flow = avg_flow_input

    avg_bod = st.number_input("Average Influent BOD (mg/L)", 50, value=250, step=10)
    avg_tss = st.number_input("Average Influent TSS (mg/L)", 50, value=220, step=10)
    avg_tkn = st.number_input("Average Influent TKN (mg/L)", 10, value=40, step=5)
    avg_tp = st.number_input("Average Influent TP (mg/L)", 1, value=7, step=1)

def display_sizing_summary(sizing, unit_system):
    st.subheader("Sizing Summary")
    
    display_sizing = sizing.copy()
    
    if 'US Customary' in unit_system:
        for key in [k for k in display_sizing if '(m³)' in k]:
            display_sizing[key.replace('(m³)', '(gal)')] = display_sizing.pop(key) * CONVERSION_FACTORS['volume']['m3_to_gal']
        for key in [k for k in display_sizing if '(m²)' in k]:
            display_sizing[key.replace('(m²)', '(ft²)')] = display_sizing.pop(key) * CONVERSION_FACTORS['area']['m2_to_ft2']
        for key in [k for k in display_sizing if '(m³/hr)' in k]:
            display_sizing[key.replace('(m³/hr)', '(gpm)')] = display_sizing.pop(key) * CONVERSION_FACTORS['pump_rate']['m3/hr_to_gpm']
        if 'Clarifier SOR (m³/m²/day)' in display_sizing:
            display_sizing['Clarifier SOR (gpd/ft²)'] = display_sizing.pop('Clarifier SOR (m³/m²/day)') * 24.54
    
    st.markdown("##### Equalization")
    eq_keys = [k for k in display_sizing if 'EQ' in k]
    eq_cols = st.columns(len(eq_keys))
    for i, key in enumerate(eq_keys):
        eq_cols[i].metric(key, f"{display_sizing[key]:,.1f}")
    
    st.markdown("##### Biological Treatment")
    bio_keys = [k for k in display_sizing if any(s in k for s in ['Basin', 'Reactor', 'Anoxic', 'Aerobic', 'DO', 'Airflow', 'BOD Loading', 'Media'])]
    bio_sizing = {k: display_sizing[k] for k in bio_keys}
    bio_cols = st.columns(4)
    for i, (key, value) in enumerate(bio_sizing.items()):
        bio_cols[i % 4].metric(key, f"{value:,.1f}")

    st.markdown("##### Solids Separation")
    sep_keys = [k for k in display_sizing if any(s in k for s in ['Clarifier', 'Membrane', 'Flux', 'DAF'])]
    sep_sizing = {k: display_sizing[k] for k in sep_keys}
    sep_cols = st.columns(len(sep_sizing) if sep_sizing else 1)
    for i, (key, value) in enumerate(sep_sizing.items()):
        sep_cols[i].metric(key, f"{value:,.1f}")
        
    st.markdown("##### Process Times")
    time_keys = [k for k in display_sizing if 'SRT' in k or 'HRT' in k]
    time_sizing = {k: display_sizing[k] for k in time_keys}
    time_cols = st.columns(len(time_sizing) if time_sizing else 1)
    for i, (key, value) in enumerate(time_sizing.items()):
        time_cols[i].metric(key, f"{value:,.1f}")

def display_pfd_and_details(sizing, results, avg_in, unit_system):
    with st.expander("Show Process Flow Diagram and Detailed Sizing", expanded=False):
        avg_out = results.mean(numeric_only=True)
        flow_unit_label = 'm³/day'
        for col in results.columns:
            if 'RAS_Flow' in col:
                flow_unit_label = col.split('(')[1].split(')')[0]
                break
        
        q_in_display = avg_in['flow']
        if 'MGD' in unit_system:
            q_in_display /= CONVERSION_FACTORS['flow']['MGD_to_m3/day']
        elif 'MLD' in unit_system:
            q_in_display /= CONVERSION_FACTORS['flow']['MLD_to_m3/day']

        q_out, bod_out, tss_out, tkn_out, tp_out = (avg_out[f'RAS_Flow ({flow_unit_label})'] + avg_out[f'WAS_Flow ({flow_unit_label})']), avg_out['Effluent_BOD (mg/L)'], avg_out['Effluent_TSS (mg/L)'], avg_out.get('Effluent_TKN (mg/L)', 0), avg_out.get('Effluent_TP (mg/L)', 0)
        ras_flow_avg, was_flow_avg = avg_out[f'RAS_Flow ({flow_unit_label})'], avg_out[f'WAS_Flow ({flow_unit_label})']

        pfd_code = f"""
        digraph G {{
            rankdir=LR;
            node [shape=box, style=rounded];
            Influent -> EQ [label="Q={q_in_display:.1f} {flow_unit_label}"];
            EQ -> Anoxic; Anoxic -> Aerobic; Aerobic -> Clarifier;
            Clarifier -> Effluent [label="BOD={bod_out:.1f}\\nTSS={tss_out:.1f}\\nTKN={tkn_out:.1f}\\nTP={tp_out:.1f}"];
            Clarifier -> WAS [style=dashed, label="Q={was_flow_avg:.2f}"];
            Clarifier -> RAS [style=dashed]; RAS -> Anoxic [style=dashed, label="Q={ras_flow_avg:.1f}"];
        }}
        """
        st.graphviz_chart(pfd_code)
        
        # ... (Detailed sizing logic remains here) ...

tab1, tab2, tab3, tab4 = st.tabs([
    "🔹 Conventional Activated Sludge (CAS)", 
    "🔸 Integrated Fixed-Film (IFAS)", 
    "🟢 Membrane Bioreactor (MBR)", 
    "🔺 Moving Bed Biofilm (MBBR)"
])

# --- Tab 1: Activated Sludge ---
with tab1:
    st.header("Conventional Activated Sludge (CAS) Design")
    
    if st.button("Generate Initial CAS Design", key='cas_design_run', use_container_width=True):
        st.session_state.cas_design_params = calculate_cas_design(avg_flow, avg_bod)
        
        influent = generate_influent_data(avg_flow, avg_bod, avg_tss, avg_tkn, avg_tp)
        results, sizing = simulate_activated_sludge(st.session_state.cas_design_params, influent, avg_flow, avg_bod, avg_tkn, avg_tp, flow_unit)
        st.session_state.cas_results, st.session_state.cas_sizing = results, sizing

    if st.session_state.cas_design_params:
        st.markdown("---")
        st.subheader("Adjust Design Parameters & Re-run Simulation")
        
        params = st.session_state.cas_design_params
        
        adj_srt = st.slider("Solids Retention Time (SRT, days)", 5, 20, int(params.get('srt', 10)), 1, key='cas_adj_srt')
        adj_mlss = st.number_input("MLSS Concentration (mg/L)", 2000, 5000, int(params.get('mlss', 3500)), 100, key='cas_adj_mlss')
        adj_hrt = st.slider("Hydraulic Retention Time (HRT, hours)", 4.0, 16.0, float(params.get('hrt', 8.0)), 0.5, key='cas_adj_hrt')
        adj_anoxic_vol = st.number_input("Anoxic Tank Volume (m³)", 0, int(params.get('total_volume', 5000)), int(params.get('anoxic_volume', 1250)), 50, key='cas_adj_anoxic')

        if st.button("Re-run Simulation with Adjusted Parameters", key='cas_rerun', use_container_width=True):
            adjusted_params = {'srt': adj_srt, 'mlss': adj_mlss, 'hrt': adj_hrt, 'total_volume': avg_flow * adj_hrt / 24, 'anoxic_volume': adj_anoxic_vol}
            influent = generate_influent_data(avg_flow, avg_bod, avg_tss, avg_tkn, avg_tp)
            results, sizing = simulate_activated_sludge(adjusted_params, influent, avg_flow, avg_bod, avg_tkn, avg_tp, flow_unit)
            st.session_state.cas_results, st.session_state.cas_sizing = results, sizing
            st.success("Simulation re-run with your parameters!")

    if st.session_state.cas_results is not None and st.session_state.cas_sizing is not None:
        st.markdown("---")
        display_sizing_summary(st.session_state.cas_sizing, flow_unit)
        st.subheader("Operational & Performance Summary")
        st.dataframe(st.session_state.cas_results.round(2))
        
        with st.expander("Export Results"):
            dl_cols = st.columns(2)
            with dl_cols[0]:
                st.download_button(
                    label="Download Data as CSV",
                    data=st.session_state.cas_results.to_csv(index=False).encode('utf-8'),
                    file_name='cas_design_results.csv',
                    mime='text/csv',
                    use_container_width=True
                )
            with dl_cols[1]:
                pdf_data = generate_pdf_report(st.session_state.cas_sizing, st.session_state.cas_results, {}, flow_unit)
                st.markdown(create_download_link_pdf(pdf_data, "cas_design_report"), unsafe_allow_html=True)

        avg_influent_loads = {'flow': avg_flow_input, 'bod': avg_bod, 'tss': avg_tss, 'tkn': avg_tkn, 'tp': avg_tp}
        display_pfd_and_details(st.session_state.cas_sizing, st.session_state.cas_results, avg_influent_loads, flow_unit)

# --- Other Tabs (using placeholders for now) ---
with tab2:
    st.header("Integrated Fixed-Film Activated Sludge (IFAS) Design")
    st.info("Functionality to be added.")
with tab3:
    st.header("Membrane Bioreactor (MBR) Design")
    st.info("Functionality to be added.")
with tab4:
    st.header("Moving Bed Biofilm Reactor (MBBR) Design")
    st.info("Functionality to be added.")
