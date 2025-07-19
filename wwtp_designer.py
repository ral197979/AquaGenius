<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AquaGenius WWTP Designer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.5.23/jspdf.plugin.autotable.min.js"></script>
    <script src="https://d3js.org/d3.v5.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/d3-graphviz@3.1.0/build/d3-graphviz.js"></script>

    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #F0F2F6;
        }
        .tab-button {
            padding: 10px 20px;
            cursor: pointer;
            border-bottom: 3px solid transparent;
            transition: all 0.3s ease;
            font-weight: 500;
            color: #4B5563;
        }
        .tab-button.active {
            color: #0068C9;
            border-bottom-color: #0068C9;
        }
        .metric-card {
            background-color: white;
            border-radius: 8px;
            padding: 1.5rem;
            border: 1px solid #E5E7EB;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
        }
        .metric-title {
            font-size: 0.875rem;
            font-weight: 500;
            color: #6B7280;
        }
        .metric-value {
            font-size: 1.875rem;
            font-weight: 700;
            color: #1F2937;
        }
        .btn-primary {
            background-color: #0068C9;
            color: white;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            font-weight: 600;
            transition: background-color 0.2s ease-in-out;
        }
        .btn-primary:hover {
            background-color: #0055A4;
        }
        .btn-secondary {
            background-color: #E5E7EB;
            color: #1F2937;
            border-radius: 8px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: background-color 0.2s ease-in-out;
        }
        .btn-secondary:hover {
            background-color: #D1D5DB;
        }
        .loader {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #0068C9;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 20px auto;
        }
        .form-checkbox {
            appearance: none;
            background-color: #fff;
            border: 1px solid #d1d5db;
            padding: 9px;
            border-radius: 4px;
            display: inline-block;
            position: relative;
        }
        .form-checkbox:checked {
            background-color: #0068C9;
            border-color: #0068C9;
        }
        .form-checkbox:checked:after {
            content: '\\2714';
            font-size: 14px;
            position: absolute;
            top: 0px;
            left: 3px;
            color: white;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body class="flex flex-col lg:flex-row h-screen">

    <!-- Sidebar -->
    <aside class="w-full lg:w-1/4 bg-white p-6 border-r border-gray-200 overflow-y-auto">
        <div class="flex items-center mb-6">
            <span class="text-4xl mr-3">🌊</span>
            <div>
                <h1 class="text-xl font-bold text-gray-800">AquaGenius</h1>
                <p class="text-sm text-gray-500">WWTP Designer</p>
            </div>
        </div>
        
        <h2 class="text-lg font-semibold text-gray-700 mb-4">⚙️ Influent Design Criteria</h2>

        <div class="mb-4">
            <label for="flow_unit" class="block text-sm font-medium text-gray-700 mb-1">Unit System</label>
            <select id="flow_unit" class="w-full p-2 border border-gray-300 rounded-md shadow-sm">
                <option value="m3_day">Metric (m³/day)</option>
                <option value="MGD">US Customary (MGD)</option>
                <option value="MLD">SI (MLD)</option>
            </select>
        </div>
        
        <div class="mb-4">
            <div class="flex justify-between items-baseline mb-1">
                <label for="avg_flow" class="block text-sm font-medium text-gray-700">Average Influent Flow</label>
                <span id="flow_unit_display" class="text-sm text-gray-500"></span>
            </div>
            <input type="number" id="avg_flow" value="10000" class="w-full p-2 border border-gray-300 rounded-md shadow-sm">
        </div>

        <div class="mb-4">
             <div class="flex justify-between items-baseline mb-1">
                <label for="avg_bod" class="block text-sm font-medium text-gray-700">Average Influent BOD</label>
                <span class="text-sm text-gray-500">(mg/L)</span>
            </div>
            <input type="number" id="avg_bod" value="250" class="w-full p-2 border border-gray-300 rounded-md shadow-sm">
        </div>

        <div class="mb-4">
            <div class="flex justify-between items-baseline mb-1">
                <label for="avg_tss" class="block text-sm font-medium text-gray-700">Average Influent TSS</label>
                <span class="text-sm text-gray-500">(mg/L)</span>
            </div>
            <input type="number" id="avg_tss" value="220" class="w-full p-2 border border-gray-300 rounded-md shadow-sm">
        </div>
        
        <div class="mb-4">
            <div class="flex justify-between items-baseline mb-1">
                <label for="avg_tkn" class="block text-sm font-medium text-gray-700">Average Influent TKN</label>
                <span class="text-sm text-gray-500">(mg/L)</span>
            </div>
            <input type="number" id="avg_tkn" value="40" class="w-full p-2 border border-gray-300 rounded-md shadow-sm">
        </div>

        <div class="mb-4">
            <div class="flex justify-between items-baseline mb-1">
                <label for="avg_tp" class="block text-sm font-medium text-gray-700">Average Influent TP</label>
                <span class="text-sm text-gray-500">(mg/L)</span>
            </div>
            <input type="number" id="avg_tp" value="7" class="w-full p-2 border border-gray-300 rounded-md shadow-sm">
        </div>

        <h2 class="text-lg font-semibold text-gray-700 my-4">🧪 Chemical Dosing</h2>
        <div class="space-y-3">
            <label class="flex items-center">
                <input type="checkbox" id="use_alum" class="form-checkbox mr-2">
                <span class="text-sm font-medium text-gray-700">Use Alum for P Removal</span>
            </label>
            <label class="flex items-center">
                <input type="checkbox" id="use_methanol" class="form-checkbox mr-2">
                <span class="text-sm font-medium text-gray-700">Use Carbon Source for N Removal</span>
            </label>
        </div>
        
        <button id="run_simulation_button" class="btn-primary w-full mt-6">Generate Design & Simulate</button>
    </aside>

    <!-- Main Content -->
    <main class="w-full lg:w-3/4 p-6 overflow-y-auto">
        <div class="tabs flex border-b border-gray-200 mb-6">
            <button class="tab-button active" data-tab="cas">🔹 CAS</button>
            <button class="tab-button" data-tab="ifas">🔸 IFAS</button>
            <button class="tab-button" data-tab="mbr">🟢 MBR</button>
            <button class="tab-button" data-tab="mbbr">🔺 MBBR</button>
        </div>

        <div id="cas_content" class="tab-content"></div>
        <div id="ifas_content" class="tab-content hidden"></div>
        <div id="mbr_content" class="tab-content hidden"></div>
        <div id="mbbr_content" class="tab-content hidden"></div>

    </main>
    
    <script>
        // --- Constants and Global State ---
        const CONVERSION_FACTORS = {
            flow: { 'MGD_to_m3_day': 3785.41, 'MLD_to_m3_day': 1000 },
            volume: { 'm3_to_gal': 264.172 },
            area: { 'm2_to_ft2': 10.7639 },
            pump_rate: { 'm3_hr_to_gpm': 4.40287 },
            sor: { 'm3_m2_day_to_gpd_ft2': 24.54 }
        };

        const KINETIC_PARAMS = {
            'Y': 0.6, 'kd': 0.06, 'fd': 0.15, 'TSS_VSS_ratio': 1.25
        };

        const AERATION_PARAMS = {
            'O2_demand_BOD': 1.5, 'O2_demand_N': 4.57, 'SOTE': 0.30,
            'O2_in_air_mass_fraction': 0.232, 'air_density_kg_m3': 1.225
        };
        
        const CHEMICAL_FACTORS = {
            'alum_to_p_ratio': 9.7, 'methanol_to_n_ratio': 2.86
        };
        
        let state = {
            results: {},
            sizing: {}
        };

        // --- UI Element References ---
        const runButton = document.getElementById('run_simulation_button');
        const tabs = document.querySelectorAll('.tab-button');
        const tabContents = document.querySelectorAll('.tab-content');
        const flowUnitSelect = document.getElementById('flow_unit');
        const flowUnitDisplay = document.getElementById('flow_unit_display');

        // --- Event Listeners ---
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                tabContents.forEach(content => content.classList.add('hidden'));
                document.getElementById(`${tab.dataset.tab}_content`).classList.remove('hidden');
            });
        });

        runButton.addEventListener('click', runFullSimulation);
        flowUnitSelect.addEventListener('change', updateFlowUnitDisplay);

        // --- UI Helper Functions ---
        function updateFlowUnitDisplay() {
            const selectedOption = flowUnitSelect.options[flowUnitSelect.selectedIndex].text;
            const unit = selectedOption.match(/\(([^)]+)\)/)[1]; // Extracts text in parentheses
            flowUnitDisplay.textContent = `(${unit})`;
        }

        // --- Core Simulation Logic ---
        function getInputs() {
            const flowUnit = flowUnitSelect.value;
            const avgFlowInput = parseFloat(document.getElementById('avg_flow').value);
            
            let avgFlowM3Day;
            if (flowUnit === 'MGD') {
                avgFlowM3Day = avgFlowInput * CONVERSION_FACTORS.flow.MGD_to_m3_day;
            } else if (flowUnit === 'MLD') {
                avgFlowM3Day = avgFlowInput * CONVERSION_FACTORS.flow.MLD_to_m3_day;
            } else {
                avgFlowM3Day = avgFlowInput;
            }
            
            return {
                flowUnit,
                avgFlowInput,
                avgFlowM3Day,
                avgBod: parseFloat(document.getElementById('avg_bod').value),
                avgTss: parseFloat(document.getElementById('avg_tss').value),
                avgTkn: parseFloat(document.getElementById('avg_tkn').value),
                avgTp: parseFloat(document.getElementById('avg_tp').value),
                useAlum: document.getElementById('use_alum').checked,
                useMethanol: document.getElementById('use_methanol').checked,
            };
        }

        function runFullSimulation() {
            const inputs = getInputs();
            if (Object.values(inputs).some(val => typeof val === 'number' && isNaN(val))) {
                alert("Please ensure all inputs are valid numbers.");
                return;
            }
            
            tabContents.forEach(tc => tc.innerHTML = '<div class="loader"></div>');

            setTimeout(() => {
                ['cas', 'ifas', 'mbr', 'mbbr'].forEach(tech => {
                    const sizingFunc = window[`calculate${tech.toUpperCase()}Sizing`];
                    state.sizing[tech] = sizingFunc(inputs);
                    state.results[tech] = simulateProcess(inputs, state.sizing[tech], tech);
                    renderOutput(tech, inputs, state.sizing[tech], state.results[tech]);
                });
            }, 500);
        }

        // --- Technology-Specific Sizing Calculations ---
        function calculateCASSizing(inputs) {
            const srt = 10; 
            const mlss = 3500; 
            const effluentBod = 10.0;
            const hrt = (srt * KINETIC_PARAMS.Y * (inputs.avgBod - effluentBod)) / (mlss * (1 + KINETIC_PARAMS.kd * srt)) * 24;
            const totalVolume = inputs.avgFlowM3Day * hrt / 24;
            const anoxicFraction = 0.3;
            const anoxicVolume = totalVolume * anoxicFraction;
            const aerobicVolume = totalVolume * (1 - anoxicFraction);
            const clarifierSor = 24;
            const clarifierArea = inputs.avgFlowM3Day / clarifierSor;
            
            return {
                tech: 'CAS', srt, mlss, hrt, totalVolume, anoxicVolume, aerobicVolume, clarifierArea, clarifierSor,
                effluentTargets: { bod: 10, tss: 12, tkn: 8, tp: 2.0 } // Base targets without chemicals
            };
        }
        
        function calculateIFASSizing(inputs) {
            const srt = 8;
            const mlss = 3000;
            const mediaFill = 0.4;
            const ssa = 500;
            const hrt = 6;
            const totalVolume = inputs.avgFlowM3Day * hrt / 24;
            const anoxicVolume = totalVolume * 0.3;
            const aerobicVolume = totalVolume * 0.7;
            const mediaVolume = aerobicVolume * mediaFill;
            const clarifierSor = 28;
            const clarifierArea = inputs.avgFlowM3Day / clarifierSor;

            return {
                tech: 'IFAS', srt, mlss, hrt, totalVolume, anoxicVolume, aerobicVolume, clarifierArea, clarifierSor, mediaVolume, ssa,
                effluentTargets: { bod: 8, tss: 10, tkn: 5, tp: 1.5 }
            };
        }

        function calculateMBRSizing(inputs) {
            const srt = 15;
            const mlss = 8000;
            const hrt = 5;
            const totalVolume = inputs.avgFlowM3Day * hrt / 24;
            const anoxicVolume = totalVolume * 0.4;
            const aerobicVolume = totalVolume * 0.6;
            const membraneFlux = 20;
            const membraneArea = (inputs.avgFlowM3Day * 1000 / 24) / membraneFlux;

            return {
                tech: 'MBR', srt, mlss, hrt, totalVolume, anoxicVolume, aerobicVolume, membraneArea, membraneFlux,
                effluentTargets: { bod: 5, tss: 1, tkn: 4, tp: 1.0 }
            };
        }

        function calculateMBBRSizing(inputs) {
            const hrt = 4;
            const totalVolume = inputs.avgFlowM3Day * hrt / 24;
            const aerobicVolume = totalVolume;
            const mediaFill = 0.5;
            const ssa = 500;
            const mediaVolume = aerobicVolume * mediaFill;
            const bodLoadingRate = 5;
            const requiredMediaArea = (inputs.avgFlowM3Day * inputs.avgBod / 1000) / bodLoadingRate;
            const requiredMediaVolume = requiredMediaArea / ssa;
            const finalAerobicVolume = requiredMediaVolume / mediaFill;

            return {
                tech: 'MBBR', hrt, totalVolume: finalAerobicVolume, aerobicVolume: finalAerobicVolume, mediaVolume: requiredMediaVolume, ssa,
                effluentTargets: { bod: 15, tss: 20, tkn: 10, tp: 2.5 }
            };
        }

        // --- Generic Simulation & Rendering ---
        function simulateProcess(inputs, sizing, tech) {
            const { avgFlowM3Day, avgBod, avgTkn, avgTp, useAlum, useMethanol } = inputs;
            const { srt, mlss, effluentTargets } = sizing;

            let effluentTkn = effluentTargets.tkn + (Math.random() - 0.5) * 1;
            let effluentTp = effluentTargets.tp + (Math.random() - 0.5) * 0.2;
            let methanolDoseKg = 0;
            let alumDoseKg = 0;

            if (useMethanol) {
                const targetTkn = (tech === 'MBR' || tech === 'IFAS') ? 2.0 : 3.0;
                const nToRemove = (effluentTkn - targetTkn) * avgFlowM3Day / 1000;
                if (nToRemove > 0) {
                    methanolDoseKg = nToRemove * CHEMICAL_FACTORS.methanol_to_n_ratio;
                    effluentTkn = targetTkn;
                }
            }
            if (useAlum) {
                const targetTp = (tech === 'MBR') ? 0.5 : 0.8;
                const pToRemove = (effluentTp - targetTp) * avgFlowM3Day / 1000;
                if (pToRemove > 0) {
                    alumDoseKg = pToRemove * CHEMICAL_FACTORS.alum_to_p_ratio;
                    effluentTp = targetTp;
                }
            }
            
            const effluentBod = Math.max(0, effluentTargets.bod + (Math.random() - 0.5) * 3);
            const effluentTss = Math.max(0, effluentTargets.tss + (Math.random() - 0.5) * 4);

            const bodRemovedKgDay = (avgBod - effluentBod) * avgFlowM3Day / 1000;
            const vssProduced = (KINETIC_PARAMS.Y * bodRemovedKgDay) / (1 + KINETIC_PARAMS.kd * (srt || 10));
            const tssProduced = vssProduced * KINETIC_PARAMS.TSS_VSS_ratio;
            
            const pRemovedChemicallyKgDay = (alumDoseKg > 0) ? alumDoseKg / CHEMICAL_FACTORS.alum_to_p_ratio : 0;
            const chemicalSludge = pRemovedChemicallyKgDay * 4.5;
            const totalSludge = tssProduced + chemicalSludge;

            const wasFlowM3d = (tech !== 'mbbr') ? (totalSludge * 1000) / (0.8 * (mlss || 3500)) : 0;
            const rasFlowM3d = (tech !== 'mbbr') ? avgFlowM3Day * 0.75 : 0;

            const nRemovedBioKgDay = (avgTkn - effluentTkn) * avgFlowM3Day / 1000;
            const oxygenDemandKgDay = (bodRemovedKgDay * AERATION_PARAMS.O2_demand_BOD) + (nRemovedBioKgDay * AERATION_PARAMS.O2_demand_N);
            const requiredAirM3Day = oxygenDemandKgDay / (AERATION_PARAMS.SOTE * AERATION_PARAMS.O2_in_air_mass_fraction * AERATION_PARAMS.air_density_kg_m3);
            
            return {
                effluentBod, effluentTss, effluentTkn, effluentTp,
                wasFlowM3d, rasFlowM3d, alumDoseKg, methanolDoseKg, totalSludge,
                oxygenDemandKgDay, requiredAirM3Day
            };
        }

        function renderOutput(tech, inputs, sizing, results) {
            const container = document.getElementById(`${tech}_content`);
            const { flowUnit } = inputs;

            // --- Convert units for display ---
            const displaySizing = {};
            const displayResults = {};
            const isUS = flowUnit === 'MGD';
            const flowDivisor = isUS ? CONVERSION_FACTORS.flow.MGD_to_m3_day : (flowUnit === 'MLD' ? CONVERSION_FACTORS.flow.MLD_to_m3_day : 1);

            for (const [key, value] of Object.entries(sizing)) {
                let newKey = key;
                let newValue = value;
                if (isUS) {
                    if (key.includes('Volume')) { newKey = key.replace('m³', 'gal'); newValue *= CONVERSION_FACTORS.volume.m3_to_gal; }
                    if (key.includes('Area')) { newKey = key.replace('m²', 'ft²'); newValue *= CONVERSION_FACTORS.area.m2_to_ft2; }
                    if (key.includes('Sor')) { newKey = key.replace('m³/m²/day', 'gpd/ft²'); newValue *= CONVERSION_FACTORS.sor.m3_m2_day_to_gpd_ft2; }
                }
                displaySizing[newKey] = newValue;
            }

            for (const [key, value] of Object.entries(results)) {
                 let newKey = key;
                 let newValue = value;
                 if(key.includes('Flow')){
                     newValue /= flowDivisor;
                 }
                 displayResults[newKey] = newValue;
            }

            const flowUnitLabel = isUS ? 'MGD' : (flowUnit === 'MLD' ? 'MLD' : 'm³/day');
            
            // --- Generate HTML ---
            let html = `<h2 class="text-2xl font-bold text-gray-800 mb-4">${tech.toUpperCase()} Design Summary</h2>`;
            
            // Sizing Cards
            html += '<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">';
            const sizingMetrics = {
                'Total Basin Volume': { value: displaySizing.totalVolume, unit: isUS ? 'gal' : 'm³' },
                'HRT': { value: displaySizing.hrt, unit: 'hours' },
                'SRT': { value: displaySizing.srt, unit: 'days' },
                'Required Airflow': { value: results.requiredAirM3Day / 24, unit: 'm³/hr' },
            };
             for(const [key, val] of Object.entries(sizingMetrics)){
                if(val.value !== undefined) {
                    html += `<div class="metric-card"><div class="metric-title">${key}</div><div class="metric-value">${val.value.toLocaleString(undefined, {maximumFractionDigits: 1})} <span class="text-lg font-medium">${val.unit}</span></div></div>`;
                }
            }
            html += '</div>';

            // PFD
            html += `<div class="bg-white p-4 rounded-lg shadow-sm border mb-6"><h3 class="font-semibold text-lg mb-2">Process Flow Diagram</h3><div id="pfd_${tech}" class="w-full h-96"></div></div>`;
            
            // Results Table
            html += `<div class="bg-white p-4 rounded-lg shadow-sm border"><h3 class="font-semibold text-lg mb-2">Performance & Operational Summary</h3>
                        <table class="w-full text-sm text-left text-gray-500">
                            <thead class="text-xs text-gray-700 uppercase bg-gray-50">
                                <tr><th class="px-6 py-3">Parameter</th><th class="px-6 py-3">Value</th><th class="px-6 py-3">Units</th></tr>
                            </thead><tbody>`;
            const tableRows = {
                'Effluent BOD': { value: results.effluentBod, unit: 'mg/L' },
                'Effluent TSS': { value: results.effluentTss, unit: 'mg/L' },
                'Effluent TKN': { value: results.effluentTkn, unit: 'mg/L' },
                'Effluent TP': { value: results.effluentTp, unit: 'mg/L' },
                'RAS Flow': { value: displayResults.rasFlowM3d, unit: flowUnitLabel },
                'WAS Flow': { value: displayResults.wasFlowM3d, unit: flowUnitLabel },
                'Alum Dose': { value: results.alumDoseKg, unit: 'kg/day' },
                'Carbon Source Dose': { value: results.methanolDoseKg, unit: 'kg/day' },
                'Total Sludge Production': { value: results.totalSludge, unit: 'kg TSS/day' },
            };
            for(const [key, val] of Object.entries(tableRows)){
                 if(val.value > 0.01) { // Only show relevant rows
                    html += `<tr class="bg-white border-b"><td class="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">${key}</td><td class="px-6 py-4">${val.value.toFixed(2)}</td><td class="px-6 py-4">${val.unit}</td></tr>`;
                 }
            }
            html += `</tbody></table></div>`;
            
            container.innerHTML = html;

            // --- Render PFD ---
            const pfdDot = generatePfdDot(tech, inputs, displaySizing, displayResults, flowUnitLabel);
            d3.select(`#pfd_${tech}`).graphviz().renderDot(pfdDot);
        }

        function generatePfdDot(tech, inputs, sizing, results, flowUnitLabel) {
            const { avgFlowInput, avgBod, avgTss, avgTkn, avgTp, useAlum, useMethanol } = inputs;
            const { effluentBod, effluentTss, effluentTkn, effluentTp, rasFlowM3d, wasFlowM3d, alumDoseKg, methanolDoseKg } = results;

            let dot = `digraph G {
                rankdir=LR;
                node [shape=box, style="rounded,filled", fillcolor="#EBF4FF", fontname="Inter"];
                edge [fontname="Inter", fontsize=10];
                
                Influent [label="Influent\\nQ=${avgFlowInput.toFixed(1)} ${flowUnitLabel}\\nBOD=${avgBod} mg/L\\nTSS=${avgTss} mg/L\\nTKN=${avgTkn} mg/L\\nTP=${avgTp} mg/L"];
            `;
            
            const effluentLabel = `Effluent\\nQ=${avgFlowInput.toFixed(1)} ${flowUnitLabel}\\nBOD=${effluentBod.toFixed(1)} mg/L\\nTSS=${effluentTss.toFixed(1)} mg/L\\nTKN=${effluentTkn.toFixed(1)} mg/L\\nTP=${effluentTp.toFixed(1)} mg/L`;
            
            let processTrain = `EQ -> Anoxic -> Aerobic;`;
            if (tech === 'mbbr') processTrain = `EQ -> Aerobic;`;

            dot += `
                subgraph cluster_main {
                    label = "${tech.toUpperCase()} Process";
                    style=filled;
                    color=lightgrey;
                    ${processTrain}
                }
            `;

            if (tech !== 'mbbr') {
                dot += `Aerobic -> Clarifier;`;
                dot += `Clarifier -> Effluent [label="${effluentLabel}"];`;
                dot += `Clarifier -> WAS [style=dashed, label="WAS\\n${wasFlowM3d.toFixed(2)} ${flowUnitLabel}"];`;
                dot += `Clarifier -> RAS [style=dashed]; RAS -> Anoxic [style=dashed, label="RAS\\n${rasFlowM3d.toFixed(1)} ${flowUnitLabel}"];`;
            } else {
                 dot += `Aerobic -> Clarifier; Clarifier -> Effluent [label="${effluentLabel}"];`;
            }

            if (useAlum && alumDoseKg > 0) {
                dot += `Alum [shape=oval, fillcolor="#FEF3C7", label="Alum Dose\\n${alumDoseKg.toFixed(1)} kg/d"]; Alum -> Aerobic;`;
            }
            if (useMethanol && methanolDoseKg > 0) {
                dot += `Methanol [shape=oval, fillcolor="#D1FAE5", label="Carbon Dose\\n${methanolDoseKg.toFixed(1)} kg/d"]; Methanol -> Anoxic;`;
            }
            
            dot += `Influent -> EQ; }`;
            return dot;
        }

        // --- Initial UI Setup ---
        updateFlowUnitDisplay();

    </script>
</body>
</html>
