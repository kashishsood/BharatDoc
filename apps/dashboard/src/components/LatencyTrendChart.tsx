import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { LatencyTrend } from '../types';

interface LatencyTrendChartProps {
  data: LatencyTrend[];
}

const MODEL_COLORS: Record<string, string> = {
  donut: '#3b82f6',
  layoutlmv3: '#10b981',
  trocr: '#f97316',
  llava: '#a855f7',
  two_stage: '#ef4444'
};

export default function LatencyTrendChart({ data }: LatencyTrendChartProps) {
  const formattedData = data.map(item => ({
    ...item,
    hourFormatted: format(parseISO(item.hour), 'MMM dd HH:mm')
  }));

  const groupedData: Record<string, any> = {};
  formattedData.forEach(item => {
    if (!groupedData[item.hourFormatted]) {
      groupedData[item.hourFormatted] = { hour: item.hourFormatted };
    }
    groupedData[item.hourFormatted][item.model_used] = item.avg_latency_ms;
  });

  const chartData = Object.values(groupedData);
  const models = Array.from(new Set(data.map(item => item.model_used)));

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <h3 className="text-xl font-semibold text-white mb-4">
        Latency Trend by Model
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="hour"
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
            label={{ value: 'Latency (ms)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0'
            }}
          />
          <Legend wrapperStyle={{ color: '#94a3b8' }} />
          <ReferenceLine
            y={200}
            stroke="#10b981"
            strokeDasharray="3 3"
            label={{ value: 'Target', fill: '#10b981', position: 'right' }}
          />
          {models.map(model => (
            <Line
              key={model}
              type="monotone"
              dataKey={model}
              stroke={MODEL_COLORS[model] || '#64748b'}
              strokeWidth={2}
              name={model}
              dot={{ r: 3 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
