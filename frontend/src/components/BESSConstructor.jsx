/**
 * BESS Constructor Component
 * Дозволяє додавати нові конфігурації батарей вручну
 */

import React, { useState } from 'react';
import { Plus, Trash2, Copy } from 'lucide-react';
import axios from 'axios';

const BESSConstructor = ({ onConfigCreated, existingConfigs = [] }) => {
  const [showForm, setShowForm] = useState(false);
  const [configs, setConfigs] = useState(existingConfigs);
  const [formData, setFormData] = useState({
    name: '',
    manufacturer: 'Hithium',
    power_mw: 5,
    capacity_mwh: 20,
    capex_per_mwh: 1500,
    capex_per_mw: 500,
    opex_per_year_pct: 2.5,
    efficiency: 0.92,
    lifespan_years: 10
  });

  const manufacturers = [
    { id: 'hithium', name: 'Hithium' },
    { id: 'catl', name: 'CATL' },
    { id: 'byd', name: 'BYD' },
    { id: 'samsung', name: 'Samsung' },
    { id: 'lg', name: 'LG Chem' },
    { id: 'other', name: 'Other' }
  ];

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const response = await axios.post('/api/bess/create', formData);
      const newConfig = response.data.config;
      
      setConfigs(prev => [...prev, newConfig]);
      onConfigCreated?.(newConfig);
      
      // Reset form
      setFormData({
        name: '',
        manufacturer: 'Hithium',
        power_mw: 5,
        capacity_mwh: 20,
        capex_per_mwh: 1500,
        capex_per_mw: 500,
        opex_per_year_pct: 2.5,
        efficiency: 0.92,
        lifespan_years: 10
      });
      
      setShowForm(false);
    } catch (error) {
      console.error('Error creating BESS config:', error);
      alert('Failed to create BESS configuration');
    }
  };

  const handleDelete = async (configId) => {
    try {
      await axios.delete(`/api/bess/${configId}`);
      setConfigs(prev => prev.filter(c => c.id !== configId));
    } catch (error) {
      console.error('Error deleting BESS config:', error);
    }
  };

  const handleDuplicate = (config) => {
    const newConfig = { ...config };
    delete newConfig.id;
    newConfig.name = `${config.name} (copy)`;
    setFormData(newConfig);
    setShowForm(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">BESS Constructor</h2>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
        >
          <Plus size={20} />
          New Configuration
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Configuration Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={formData.name}
                  onChange={handleInputChange}
                  placeholder="e.g., Hithium 5MW/20MWh"
                  required
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>

              {/* Manufacturer */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Manufacturer
                </label>
                <select
                  name="manufacturer"
                  value={formData.manufacturer}
                  onChange={handleInputChange}
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                >
                  {manufacturers.map(m => (
                    <option key={m.id} value={m.name}>{m.name}</option>
                  ))}
                </select>
              </div>

              {/* Power (MW) */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Power (MW) *
                </label>
                <input
                  type="number"
                  name="power_mw"
                  value={formData.power_mw}
                  onChange={handleInputChange}
                  step="0.5"
                  min="0.1"
                  required
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>

              {/* Capacity (MWh) */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Capacity (MWh) *
                </label>
                <input
                  type="number"
                  name="capacity_mwh"
                  value={formData.capacity_mwh}
                  onChange={handleInputChange}
                  step="1"
                  min="1"
                  required
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>

              {/* CAPEX per MWh */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  CAPEX (€/MWh) *
                </label>
                <input
                  type="number"
                  name="capex_per_mwh"
                  value={formData.capex_per_mwh}
                  onChange={handleInputChange}
                  step="100"
                  min="100"
                  required
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>

              {/* CAPEX per MW */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  CAPEX (€/MW) *
                </label>
                <input
                  type="number"
                  name="capex_per_mw"
                  value={formData.capex_per_mw}
                  onChange={handleInputChange}
                  step="50"
                  min="50"
                  required
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>

              {/* OPEX */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  OPEX (% of CAPEX/year) *
                </label>
                <input
                  type="number"
                  name="opex_per_year_pct"
                  value={formData.opex_per_year_pct}
                  onChange={handleInputChange}
                  step="0.1"
                  min="0.1"
                  max="100"
                  required
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>

              {/* Efficiency */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Efficiency (round-trip)
                </label>
                <input
                  type="number"
                  name="efficiency"
                  value={formData.efficiency}
                  onChange={handleInputChange}
                  step="0.01"
                  min="0.8"
                  max="0.99"
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>

              {/* Lifespan */}
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Lifespan (years)
                </label>
                <input
                  type="number"
                  name="lifespan_years"
                  value={formData.lifespan_years}
                  onChange={handleInputChange}
                  step="1"
                  min="5"
                  max="30"
                  className="mt-1 w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500"
                />
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="submit"
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"
              >
                Save Configuration
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 bg-gray-300 text-gray-800 rounded-md hover:bg-gray-400"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Config List */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {configs.map(config => (
          <div key={config.id} className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm hover:shadow-md">
            <div className="flex justify-between items-start mb-3">
              <div>
                <h3 className="font-bold text-gray-900">{config.name}</h3>
                <p className="text-sm text-gray-600">{config.manufacturer}</p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => handleDuplicate(config)}
                  className="p-1 text-blue-600 hover:bg-blue-50 rounded"
                  title="Duplicate"
                >
                  <Copy size={18} />
                </button>
                <button
                  onClick={() => handleDelete(config.id)}
                  className="p-1 text-red-600 hover:bg-red-50 rounded"
                  title="Delete"
                >
                  <Trash2 size={18} />
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-gray-600">Power:</span>
                <span className="font-medium"> {config.power_mw} MW</span>
              </div>
              <div>
                <span className="text-gray-600">Capacity:</span>
                <span className="font-medium"> {config.capacity_mwh} MWh</span>
              </div>
              <div>
                <span className="text-gray-600">CAPEX:</span>
                <span className="font-medium"> €{config.capex_per_mwh}/MWh</span>
              </div>
              <div>
                <span className="text-gray-600">OPEX:</span>
                <span className="font-medium"> {config.opex_per_year_pct}%/yr</span>
              </div>
              <div>
                <span className="text-gray-600">Efficiency:</span>
                <span className="font-medium"> {(config.efficiency * 100).toFixed(1)}%</span>
              </div>
              <div>
                <span className="text-gray-600">Hours:</span>
                <span className="font-medium"> {(config.capacity_mwh / config.power_mw).toFixed(1)}h</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {configs.length === 0 && !showForm && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-600 mb-4">No BESS configurations yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="text-blue-600 hover:text-blue-700 font-medium"
          >
            Create your first one →
          </button>
        </div>
      )}
    </div>
  );
};

export default BESSConstructor;
