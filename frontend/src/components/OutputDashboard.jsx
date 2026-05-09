/**
 * Output Dashboard Component
 * Показує результати симуляції: графіки, таблиці, sensitivity аналіз
 */

import React, { useState, useEffect } from 'react';
import Plot from 'react-plotly.js';
import { Download, TrendingUp, DollarSign, Clock } from 'lucide-react';
import axios from 'axios';

const OutputDashboard = ({ simulationId, simulationData }) => {
  const [activeTab, setActiveTab] = useState('summary');
  const [reportGenerating, setReportGenerating] = useState(false);

  if (!simulationData) {
    return (
      <div className="text-center py-12 bg-gray-50 rounded-lg">
        <p className="text-gray-600">Run a simulation to see results</p>
      </div>
    );
  }

  const output = simulationData.output;

  // Prepare data for charts
  const years = output.annual_results.map(r => r.year);
  const revenues = output.annual_results.map(r => r.total_revenue_uah / 40); // Convert to EUR
  const opex = output.annual_results.map(r => r.total_opex_uah / 40);
  const cumulative = output.annual_results.map(r => r.cumulative_cashflow_uah / 40);

  const handleGenerateReport = async (format) => {
    setReportGenerating(true);
    try {
      const endpoint = format === 'pdf' ? '/api/report/pdf' : '/api/report/excel';
      const response = await axios.post(endpoint, { sim_id: simulationId });
      
      alert(`${format.toUpperCase()} report generation started. Task ID: ${response.data.task_id}`);
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report');
    } finally {
      setReportGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">IRR</p>
              <p className="text-3xl font-bold text-green-600">{output.irr_pct.toFixed(1)}%</p>
            </div>
            <TrendingUp className="text-green-500" size={32} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">NPV (€)</p>
              <p className="text-3xl font-bold text-blue-600">
                {(output.npv_eur / 1000000).toFixed(1)}M
              </p>
            </div>
            <DollarSign className="text-blue-500" size={32} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">Payback Period</p>
              <p className="text-3xl font-bold text-purple-600">{output.payback_years.toFixed(1)}</p>
              <p className="text-xs text-gray-600">years</p>
            </div>
            <Clock className="text-purple-500" size={32} />
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg border border-gray-200 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 mb-1">CAPEX</p>
              <p className="text-3xl font-bold text-orange-600">
                {(output.capex_eur / 1000000).toFixed(1)}M €
              </p>
            </div>
            <Download className="text-orange-500" size={32} />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="flex border-b border-gray-200">
          {[
            { id: 'summary', label: 'Summary' },
            { id: 'charts', label: 'Charts' },
            { id: 'annual', label: 'Annual Results' },
            { id: 'sensitivity', label: 'Sensitivity' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex-1 py-3 px-4 font-medium transition ${
                activeTab === tab.id
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* Summary Tab */}
          {activeTab === 'summary' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Configuration</p>
                  <p className="font-semibold">{output.generation_mix.bess.name}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Solar Capacity</p>
                  <p className="font-semibold">{output.generation_mix.solar_mw} MW</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Wind Capacity</p>
                  <p className="font-semibold">{output.generation_mix.wind_mw} MW</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Gas Enabled</p>
                  <p className="font-semibold">{output.generation_mix.gas_enabled ? '✓ Yes' : '✗ No'}</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Annual Revenue (avg)</p>
                  <p className="font-semibold">€{(output.revenue_annual_avg_eur / 1000).toFixed(0)}k</p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Annual OPEX (avg)</p>
                  <p className="font-semibold">€{(output.opex_annual_eur / 1000).toFixed(0)}k</p>
                </div>
              </div>

              <div className="pt-6 border-t border-gray-200">
                <h3 className="font-semibold mb-4">Generate Reports</h3>
                <div className="flex gap-3">
                  <button
                    onClick={() => handleGenerateReport('pdf')}
                    disabled={reportGenerating}
                    className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50"
                  >
                    📄 PDF Report
                  </button>
                  <button
                    onClick={() => handleGenerateReport('excel')}
                    disabled={reportGenerating}
                    className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                  >
                    📊 Excel Report
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Charts Tab */}
          {activeTab === 'charts' && (
            <div className="space-y-6">
              {/* Revenue & OPEX */}
              <div>
                <h3 className="font-semibold mb-4">Annual Revenue vs OPEX</h3>
                <Plot
                  data={[
                    {
                      x: years,
                      y: revenues,
                      name: 'Revenue',
                      type: 'bar',
                      marker: { color: 'rgba(34, 197, 94, 0.8)' }
                    },
                    {
                      x: years,
                      y: opex,
                      name: 'OPEX',
                      type: 'bar',
                      marker: { color: 'rgba(239, 68, 68, 0.8)' }
                    }
                  ]}
                  layout={{
                    title: '',
                    xaxis: { title: 'Year' },
                    yaxis: { title: 'Amount (€)' },
                    barmode: 'group',
                    height: 400,
                    margin: { l: 60, r: 40, t: 40, b: 60 }
                  }}
                  config={{ responsive: true }}
                />
              </div>

              {/* Cumulative Cashflow */}
              <div>
                <h3 className="font-semibold mb-4">Cumulative Cashflow</h3>
                <Plot
                  data={[
                    {
                      x: years,
                      y: cumulative,
                      fill: 'tozeroy',
                      name: 'Cumulative CF',
                      line: { color: 'rgb(59, 130, 246)' },
                      fillcolor: 'rgba(59, 130, 246, 0.1)'
                    }
                  ]}
                  layout={{
                    title: '',
                    xaxis: { title: 'Year' },
                    yaxis: { title: 'Amount (€)' },
                    height: 400,
                    margin: { l: 60, r: 40, t: 40, b: 60 }
                  }}
                  config={{ responsive: true }}
                />
              </div>
            </div>
          )}

          {/* Annual Results Tab */}
          {activeTab === 'annual' && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold">Year</th>
                    <th className="px-4 py-3 text-right font-semibold">Revenue (€)</th>
                    <th className="px-4 py-3 text-right font-semibold">OPEX (€)</th>
                    <th className="px-4 py-3 text-right font-semibold">CAPEX (€)</th>
                    <th className="px-4 py-3 text-right font-semibold">Net Cashflow (€)</th>
                    <th className="px-4 py-3 text-right font-semibold">Cumulative (€)</th>
                  </tr>
                </thead>
                <tbody>
                  {output.annual_results.map((result, idx) => (
                    <tr key={idx} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                      <td className="px-4 py-3">{result.year}</td>
                      <td className="px-4 py-3 text-right font-medium text-green-600">
                        €{(result.total_revenue_uah / 40).toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-red-600">
                        €{(result.total_opex_uah / 40).toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium">
                        €{(result.total_capex_uah / 40).toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium">
                        €{(result.net_cashflow_uah / 40).toFixed(0)}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold text-blue-600">
                        €{(result.cumulative_cashflow_uah / 40).toFixed(0)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Sensitivity Tab */}
          {activeTab === 'sensitivity' && (
            <div className="space-y-4">
              {output.sensitivity && output.sensitivity.length > 0 ? (
                output.sensitivity.map((sens, idx) => (
                  <div key={idx}>
                    <h3 className="font-semibold mb-3">{sens.parameter} Sensitivity</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                      {sens.scenarios.map((scen, sidx) => (
                        <div key={sidx} className="p-3 bg-gray-50 rounded-lg">
                          <p className="text-sm font-medium">{scen.scenario}</p>
                          <p className="text-lg font-bold text-blue-600 mt-1">
                            {(scen.irr * 100).toFixed(1)}%
                          </p>
                          <p className="text-xs text-gray-600">IRR</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-gray-600">No sensitivity data available</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OutputDashboard;
