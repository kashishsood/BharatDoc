import { useEffect } from 'react';
import { useFetch } from '../hooks/useFetch';
import {
  getOverview,
  getDailyStats,
  getModelComparison,
  getFieldErrors,
  getLatencyTrend
} from '../api/analytics';
import MetricCard from '../components/MetricCard';
import DailyVolumeChart from '../components/DailyVolumeChart';
import ModelComparisonChart from '../components/ModelComparisonChart';
import FieldErrorsTable from '../components/FieldErrorsTable';
import LatencyTrendChart from '../components/LatencyTrendChart';

export default function Dashboard() {
  const { data: overview, loading: overviewLoading, error: overviewError, refetch: refetchOverview } = useFetch(getOverview);
  const { data: dailyStats, loading: dailyLoading, error: dailyError, refetch: refetchDaily } = useFetch(() => getDailyStats(30));
  const { data: modelComparison, loading: modelLoading, error: modelError, refetch: refetchModel } = useFetch(getModelComparison);
  const { data: fieldErrors, loading: errorsLoading, error: errorsError, refetch: refetchErrors } = useFetch(() => getFieldErrors('all'));
  const { data: latencyTrend, loading: latencyLoading, error: latencyError, refetch: refetchLatency } = useFetch(() => getLatencyTrend(7));

  useEffect(() => {
    const interval = setInterval(() => {
      refetchOverview();
      refetchDaily();
      refetchModel();
      refetchErrors();
      refetchLatency();
    }, 30000);

    return () => clearInterval(interval);
  }, [refetchOverview, refetchDaily, refetchModel, refetchErrors, refetchLatency]);

  const isLoading = overviewLoading || dailyLoading || modelLoading || errorsLoading || latencyLoading;
  const hasError = overviewError || dailyError || modelError || errorsError || latencyError;

  if (hasError) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-slate-800 rounded-lg p-8 max-w-md text-center">
          <div className="text-red-400 text-5xl mb-4">⚠</div>
          <h2 className="text-xl font-semibold text-white mb-2">Error Loading Dashboard</h2>
          <p className="text-slate-400 mb-4">
            {overviewError || dailyError || modelError || errorsError || latencyError}
          </p>
          <button
            onClick={() => {
              refetchOverview();
              refetchDaily();
              refetchModel();
              refetchErrors();
              refetchLatency();
            }}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="space-y-6 p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-slate-800 rounded-lg p-6 h-32 animate-pulse" />
          ))}
        </div>
        <div className="bg-slate-800 rounded-lg p-6 h-96 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <div className="lg:col-span-3 bg-slate-800 rounded-lg p-6 h-96 animate-pulse" />
          <div className="lg:col-span-2 bg-slate-800 rounded-lg p-6 h-96 animate-pulse" />
        </div>
        <div className="bg-slate-800 rounded-lg p-6 h-96 animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Extractions"
          value={overview?.total_extractions.toLocaleString() || '0'}
          color="blue"
          trend="up"
        />
        <MetricCard
          title="Avg F1 Score"
          value={overview?.avg_f1_score.toFixed(3) || '0.000'}
          subtitle={`Best: ${overview?.best_model || 'N/A'}`}
          color="green"
          trend={overview && overview.avg_f1_score >= 0.85 ? 'up' : 'neutral'}
        />
        <MetricCard
          title="Avg Latency"
          value={`${overview?.avg_latency_ms.toFixed(0) || '0'}ms`}
          subtitle="Target: 200ms"
          color={overview && overview.avg_latency_ms <= 200 ? 'green' : 'purple'}
          trend={overview && overview.avg_latency_ms <= 200 ? 'up' : 'down'}
        />
        <MetricCard
          title="Total Errors"
          value={overview?.total_errors || '0'}
          subtitle={`Worst: ${overview?.worst_document_type || 'N/A'}`}
          color="red"
          trend={overview && overview.total_errors > 0 ? 'down' : 'neutral'}
        />
      </div>

      {dailyStats && dailyStats.length > 0 && (
        <DailyVolumeChart data={dailyStats} />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          {modelComparison && modelComparison.length > 0 && (
            <ModelComparisonChart data={modelComparison} />
          )}
        </div>
        <div className="lg:col-span-2">
          {fieldErrors && fieldErrors.length > 0 && (
            <FieldErrorsTable data={fieldErrors} />
          )}
        </div>
      </div>

      {latencyTrend && latencyTrend.length > 0 && (
        <LatencyTrendChart data={latencyTrend} />
      )}
    </div>
  );
}
