import { useState, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import type { ModelComparison } from '../types';

interface ModelComparisonChartProps {
  data: ModelComparison[];
}

const MODEL_COLORS: Record<string, string> = {
  donut: '#3b82f6',
  layoutlmv3: '#10b981',
  trocr: '#f97316',
  llava: '#a855f7',
  two_stage: '#ef4444'
};

export default function ModelComparisonChart({ data }: ModelComparisonChartProps) {
  const [selectedDocType, setSelectedDocType] = useState<string>('All');

  const documentTypes = useMemo(() => {
    const types = new Set(data.map(item => item.document_type));
    return ['All', ...Array.from(types)];
  }, [data]);

  const filteredData = useMemo(() => {
    if (selectedDocType === 'All') {
      return data;
    }
    return data.filter(item => item.document_type === selectedDocType);
  }, [data, selectedDocType]);

  const chartData = useMemo(() => {
    const grouped: Record<string, any> = {};
    
    filteredData.forEach(item => {
      if (!grouped[item.document_type]) {
        grouped[item.document_type] = { document_type: item.document_type };
      }
      grouped[item.document_type][item.model_used] = item.avg_f1;
    });

    return Object.values(grouped);
  }, [filteredData]);

  const models = useMemo(() => {
    const modelSet = new Set(data.map(item => item.model_used));
    return Array.from(modelSet);
  }, [data]);

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold text-white">
          Model Performance by Document Type
        </h3>
        <div className="flex gap-2">
          {documentTypes.map(type => (
            <button
              key={type}
              onClick={() => setSelectedDocType(type)}
              className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                selectedDocType === type
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {type}
            </button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="document_type"
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            domain={[0, 1]}
            label={{ value: 'Avg F1 Score', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0'
            }}
            formatter={(value: any, name: string) => {
              const item = filteredData.find(d => d.model_used === name);
              return [
                <div key={name}>
                  <div>F1: {(value as number).toFixed(3)}</div>
                  {item && <div>Latency: {item.avg_latency.toFixed(0)}ms</div>}
                </div>,
                name
              ];
            }}
          />
          <Legend wrapperStyle={{ color: '#94a3b8' }} />
          {models.map(model => (
            <Bar
              key={model}
              dataKey={model}
              fill={MODEL_COLORS[model] || '#64748b'}
              name={model}
              radius={[8, 8, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
