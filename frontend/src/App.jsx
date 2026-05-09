/**
 * Main App Component
 * Chervonohrad BESS Simulator - главное приложение
 */

import React, { useState, useRef } from 'react';
import { Zap, Settings, BarChart3, Loader } from 'lucide-react';
import axios from 'axios';

import BESSConstructor from './components/BESSConstructor';
import ScenarioSelector from './components/ScenarioSelector';
import OutputDashboard from './components/OutputDashboard';

function App() {
  const [currentStep, setCurrentStep] = useState('bess'); // 'bess' -> 'scenario' -> 'output'
  const [selectedBESS, setSelectedBESS] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [simulationData, setSimulationData] = useState(null);
  const [simulationId, setSimulationId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const bessConstructorRef = useRef(null);
  const scenarioSelectorRef = useRef(null);

  const handleBESSCreated = (config) => {
    setSelectedBESS(config);
    setCurrentStep('scenario');
  };

  const handleScenarioChange = (scenario) => {
    setSelectedScenario(scenario);
  };

  const handleRunSimulation = async () => {
    if (!selectedBESS || !selectedScenario) {
      setError('Please select BESS and scenario');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        generation_mix: {
          bess: selectedBESS,
          solar_mw: selectedScenario.solar_mw,
          wind_mw: selectedScenario.wind_mw,
          gas_enabled: selectedScenario.gas_enabled,
          gas_scenario: selectedScenario.gas_enabled ? {
            type: selectedScenario.gas_scenario_type,
            gas_price_per_mmbtu: selectedScenario.gas_custom_price || 5.0,
            plant_efficiency: 0.45,
            min_load_pct: 0.3,
            ramp_rate_mw_per_min: 10,
            co2_price_per_ton: 80
          } : null,
          bess_only: selectedScenario.solar_mw === 0 && selectedScenario.wind_mw === 0 && !selectedScenario.gas_enabled
        },
        year: 2025,
        simulation_years: 10
      };

      const response = await axios.post('/api/simulate', payload);
      
      setSimulationId(response.data.simulation_id);
      setSimulationData(response.data);
      setCurrentStep('output');
    } catch (err) {
      console.error('Simulation error:', err);
      setError(err.response?.data?.detail || 'Failed to run simulation');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setCurrentStep('bess');
    setSelectedBESS(null);
    setSelectedScenario(null);
    setSimulationData(null);
    setSimulationId(null);
    setError(null);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-green-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-600 rounded-lg">
                <Zap className="text-white" size={28} />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  Chervonohrad BESS Simulator
                </h1>
                <p className="text-sm text-gray-600">
                  Battery Energy Storage System Modeling for Renewable Integration
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Settings size={16} />
              <span>v0.1.0</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Progress Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            {[
              { step: 'bess', label: 'BESS Setup', icon: '⚙️' },
              { step: 'scenario', label: 'Generation Mix', icon: '☀️' },
              { step: 'output', label: 'Results & Analysis', icon: '📊' }
            ].map((item, idx) => (
              <React.Fragment key={item.step}>
                <div
                  onClick={() => {
                    if (item.step === 'bess' || (item.step === 'scenario' && selectedBESS) || (item.step === 'output' && simulationData)) {
                      setCurrentStep(item.step);
                    }
                  }}
                  className={`flex items-center gap-3 cursor-pointer transition ${
                    currentStep === item.step
                      ? 'text-blue-600'
                      : currentStep === 'output' || (currentStep === 'scenario' && item.step === 'bess')
                      ? 'text-gray-600 opacity-60'
                      : 'text-gray-400'
                  }`}
                >
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                    currentStep === item.step
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-600'
                  }`}>
                    {item.icon}
                  </div>
                  <span className="font-medium hidden sm:inline">{item.label}</span>
                </div>

                {idx < 2 && (
                  <div className={`flex-1 h-1 mx-2 ${
                    idx === 0
                      ? currentStep !== 'bess' ? 'bg-blue-600' : 'bg-gray-300'
                      : currentStep === 'output' ? 'bg-blue-600' : 'bg-gray-300'
                  }`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-medium">❌ {error}</p>
          </div>
        )}

        {/* Content */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100">
          {currentStep === 'bess' && (
            <div className="p-8">
              <BESSConstructor
                ref={bessConstructorRef}
                onConfigCreated={handleBESSCreated}
              />
            </div>
          )}

          {currentStep === 'scenario' && (
            <div className="p-8">
              <ScenarioSelector
                selectedBESS={selectedBESS}
                onScenarioChange={handleScenarioChange}
              />

              <div className="flex gap-4 mt-8 pt-6 border-t border-gray-200">
                <button
                  onClick={() => setCurrentStep('bess')}
                  className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 font-medium"
                >
                  ← Back
                </button>
                <button
                  onClick={handleRunSimulation}
                  disabled={loading || !selectedScenario}
                  className="flex-1 px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <Loader className="animate-spin" size={20} />
                      Running Simulation...
                    </>
                  ) : (
                    <>
                      <BarChart3 size={20} />
                      Run Simulation (< 1 sec)
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {currentStep === 'output' && (
            <div className="p-8">
              <OutputDashboard
                simulationId={simulationId}
                simulationData={simulationData}
              />

              <div className="flex gap-4 mt-8 pt-6 border-t border-gray-200">
                <button
                  onClick={handleReset}
                  className="px-6 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 font-medium"
                >
                  ← Start Over
                </button>
                <button
                  onClick={() => setCurrentStep('scenario')}
                  className="px-6 py-2 bg-blue-100 text-blue-700 rounded-lg hover:bg-blue-200 font-medium"
                >
                  Modify Scenario →
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-sm text-gray-600 pb-6">
          <p>Chervonohrad BESS Simulator • Built with React + FastAPI • © 2025</p>
          <p className="mt-2">
            For questions: 
            <a href="mailto:support@example.com" className="text-blue-600 hover:underline ml-1">
              support@example.com
            </a>
          </p>
        </footer>
      </main>
    </div>
  );
}

export default App;
