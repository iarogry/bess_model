/**
 * Scenario Selector Component
 * Выбор типов генерации (СЕС, КГУ/газ, ветер) и их параметров
 */

import React, { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import axios from 'axios';

const ScenarioSelector = ({ selectedBESS, onScenarioChange }) => {
  const [gasScenarios, setGasScenarios] = useState({});
  const [loadingScenarios, setLoadingScenarios] = useState(true);
  
  const [scenario, setScenario] = useState({
    solar_mw: 0,
    wind_mw: 0,
    gas_enabled: false,
    gas_scenario_type: 'mid',
    gas_custom_price: null
  });

  useEffect(() => {
    fetchGasScenarios();
  }, []);

  useEffect(() => {
    onScenarioChange(scenario);
  }, [scenario]);

  const fetchGasScenarios = async () => {
    try {
      const response = await axios.post('/api/gas/scenarios');
      setGasScenarios(response.data);
      setLoadingScenarios(false);
    } catch (error) {
      console.error('Error fetching gas scenarios:', error);
      setLoadingScenarios(false);
    }
  };

  const handleSolarChange = (e) => {
    setScenario(prev => ({
      ...prev,
      solar_mw: parseFloat(e.target.value) || 0
    }));
  };

  const handleWindChange = (e) => {
    setScenario(prev => ({
      ...prev,
      wind_mw: parseFloat(e.target.value) || 0
    }));
  };

  const toggleGas = () => {
    setScenario(prev => ({
      ...prev,
      gas_enabled: !prev.gas_enabled
    }));
  };

  const handleGasScenarioChange = (type) => {
    setScenario(prev => ({
      ...prev,
      gas_scenario_type: type,
      gas_custom_price: null
    }));
  };

  const handleCustomGasPrice = (e) => {
    setScenario(prev => ({
      ...prev,
      gas_scenario_type: 'custom',
      gas_custom_price: parseFloat(e.target.value) || null
    }));
  };

  if (!selectedBESS) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-yellow-800">Please select or create a BESS configuration first</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 bg-white rounded-lg p-6 border border-gray-200">
      <h2 className="text-2xl font-bold text-gray-900">Generation Mix</h2>

      {/* Solar Generation */}
      <div className="space-y-3">
        <label className="block text-sm font-semibold text-gray-900">
          Solar (СЕС) Generation
        </label>
        <p className="text-xs text-gray-600">
          Усредненная модель на базі Червонограда + коррекція потужності
        </p>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="50"
            step="0.5"
            value={scenario.solar_mw}
            onChange={handleSolarChange}
            className="flex-1 h-2 bg-yellow-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="50"
              step="0.5"
              value={scenario.solar_mw}
              onChange={handleSolarChange}
              className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
            />
            <span className="text-sm font-medium text-gray-700">MW</span>
          </div>
        </div>
        <div className="text-xs text-gray-600 bg-yellow-50 p-2 rounded">
          Capacity Factor: ~25-30% | Annual Output: ~{(scenario.solar_mw * 2200).toFixed(0)} MWh
        </div>
      </div>

      {/* Wind Generation */}
      <div className="space-y-3 pt-4 border-t border-gray-200">
        <label className="block text-sm font-semibold text-gray-900">
          Wind Generation (Ветер)
        </label>
        <p className="text-xs text-gray-600">
          Усреднённые данні для України
        </p>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0"
            max="50"
            step="0.5"
            value={scenario.wind_mw}
            onChange={handleWindChange}
            className="flex-1 h-2 bg-blue-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex items-center gap-2">
            <input
              type="number"
              min="0"
              max="50"
              step="0.5"
              value={scenario.wind_mw}
              onChange={handleWindChange}
              className="w-20 px-2 py-1 border border-gray-300 rounded text-sm"
            />
            <span className="text-sm font-medium text-gray-700">MW</span>
          </div>
        </div>
        <div className="text-xs text-gray-600 bg-blue-50 p-2 rounded">
          Capacity Factor: ~30% | Annual Output: ~{(scenario.wind_mw * 2600).toFixed(0)} MWh
        </div>
      </div>

      {/* Gas Generation */}
      <div className="space-y-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <label className="text-sm font-semibold text-gray-900">
            Gas Generation (КГУ)
          </label>
          <label className="flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={scenario.gas_enabled}
              onChange={toggleGas}
              className="w-4 h-4 text-blue-600"
            />
            <span className="ml-2 text-sm text-gray-700">
              {scenario.gas_enabled ? 'Enabled' : 'Disabled'}
            </span>
          </label>
        </div>

        {scenario.gas_enabled && !loadingScenarios && (
          <div className="space-y-3 bg-gray-50 p-4 rounded-lg">
            <p className="text-xs text-gray-600">
              Gas works when market price &gt; marginal cost. Set the cost scenario:
            </p>

            <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
              {Object.entries(gasScenarios).map(([key, scenario]) => (
                <button
                  key={key}
                  onClick={() => handleGasScenarioChange(key)}
                  className={`p-3 rounded-lg border-2 transition ${
                    scenario.scenario_type === key
                      ? 'border-blue-600 bg-blue-50'
                      : 'border-gray-300 bg-white hover:border-gray-400'
                  }`}
                >
                  <div className="font-semibold text-sm capitalize">{key}</div>
                  <div className="text-xs text-gray-600 mt-1">
                    ${scenario.gas_price_per_mmbtu.toFixed(1)}/MMBtu
                  </div>
                </button>
              ))}
            </div>

            {/* Custom Gas Price */}
            <div className="pt-2 border-t border-gray-300">
              <label className="text-xs font-semibold text-gray-700">
                Custom Price ($/MMBtu)
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                placeholder="Enter custom price"
                onChange={handleCustomGasPrice}
                className="w-full mt-1 px-3 py-2 border border-gray-300 rounded text-sm"
              />
            </div>

            <div className="text-xs text-gray-600 bg-white p-2 rounded">
              <div>• Plant efficiency: 45%</div>
              <div>• Min load: 30%</div>
              <div>• CO₂ cost: €80/ton</div>
            </div>
          </div>
        )}
      </div>

      {/* Summary */}
      <div className="pt-4 border-t border-gray-200 bg-gradient-to-r from-green-50 to-blue-50 p-4 rounded-lg">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">Configuration Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-gray-600">BESS:</span>
            <div className="font-semibold">{selectedBESS.name}</div>
          </div>
          <div>
            <span className="text-gray-600">Solar:</span>
            <div className="font-semibold">{scenario.solar_mw.toFixed(1)} MW</div>
          </div>
          <div>
            <span className="text-gray-600">Wind:</span>
            <div className="font-semibold">{scenario.wind_mw.toFixed(1)} MW</div>
          </div>
          <div>
            <span className="text-gray-600">Gas:</span>
            <div className="font-semibold">{scenario.gas_enabled ? '✓ Enabled' : '✗ Disabled'}</div>
          </div>
          <div>
            <span className="text-gray-600">Total Capacity:</span>
            <div className="font-semibold">
              {(selectedBESS.power_mw + scenario.solar_mw + scenario.wind_mw).toFixed(1)} MW
            </div>
          </div>
          <div>
            <span className="text-gray-600">Simulation Years:</span>
            <div className="font-semibold">10</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ScenarioSelector;
