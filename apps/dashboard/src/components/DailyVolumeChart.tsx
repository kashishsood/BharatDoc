import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { DailyStats } from '../types';

interface DailyVolumeChartProps {
  data: DailyStats[];
}

export default function DailyVolumeChart({ data }: DailyVolumeChartProps) {
  const formattedData = data.map(item => ({
    ...item,
    dateFormatted: format(parseISO(item.date), 'MMM dd')
  }));

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <h3 className="text-xl font-semibold text-white mb-4">
        Daily Extraction Volume & Quality
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart data={formattedData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis
            dataKey="dateFormatted"
            stroke="#94a3b8"
            style={{ fontSize: '12px' }}
          />
          <YAxis
            yAxisId="left"
            stroke="#3b82f6"
            style={{ fontSize: '12px' }}
            label={{ value: 'Count', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke="#f97316"
            style={{ fontSize: '12px' }}
            domain={[0, 1]}
            label={{ value: 'F1 Score', angle: 90, position: 'insideRight', fill: '#94a3b8' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
              color: '#e2e8f0'
            }}
          />
          <Legend
            wrapperStyle={{ color: '#94a3b8' }}
          />
          <Bar
            yAxisId="left"
            dataKey="count"
            fill="#3b82f6"
            name="Extractions"
            radius={[8, 8, 0, 0]}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="avg_f1"
            stroke="#f97316"
            strokeWidth={2}
            name="Avg F1 Score"
            dot={{ fill: '#f97316', r: 4 }}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
