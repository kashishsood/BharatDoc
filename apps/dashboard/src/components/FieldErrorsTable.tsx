import { useState, useMemo } from 'react';
import type { FieldError } from '../types';

interface FieldErrorsTableProps {
  data: FieldError[];
}

export default function FieldErrorsTable({ data }: FieldErrorsTableProps) {
  const [selectedErrorType, setSelectedErrorType] = useState<string>('all');
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  const errorTypes = useMemo(() => {
    const types = new Set(data.map(item => item.error_type));
    return ['all', ...Array.from(types)];
  }, [data]);

  const filteredData = useMemo(() => {
    if (selectedErrorType === 'all') {
      return [...data].sort((a, b) => b.count - a.count);
    }
    return data
      .filter(item => item.error_type === selectedErrorType)
      .sort((a, b) => b.count - a.count);
  }, [data, selectedErrorType]);

  const totalPages = Math.ceil(filteredData.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = filteredData.slice(startIndex, startIndex + itemsPerPage);

  const getProgressBarColor = (percentage: number) => {
    if (percentage > 10) return 'bg-red-500';
    if (percentage > 5) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold text-white">
          Most Common Extraction Errors
        </h3>
        <select
          value={selectedErrorType}
          onChange={(e) => {
            setSelectedErrorType(e.target.value);
            setCurrentPage(1);
          }}
          className="bg-slate-700 text-white px-3 py-2 rounded border border-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {errorTypes.map(type => (
            <option key={type} value={type}>
              {type === 'all' ? 'All Error Types' : type}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-700">
              <th className="text-left py-3 px-4 text-sm font-semibold text-slate-300">Field Name</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-slate-300">Error Type</th>
              <th className="text-right py-3 px-4 text-sm font-semibold text-slate-300">Count</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-slate-300">Percentage</th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.map((item, index) => (
              <tr key={index} className="border-b border-slate-700 hover:bg-slate-700/50 transition-colors">
                <td className="py-3 px-4 text-sm text-white">{item.field_name}</td>
                <td className="py-3 px-4 text-sm text-slate-300">{item.error_type}</td>
                <td className="py-3 px-4 text-sm text-white text-right">{item.count}</td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 bg-slate-700 rounded-full h-2 overflow-hidden">
                      <div
                        className={`h-full ${getProgressBarColor(item.error_pct)} transition-all`}
                        style={{ width: `${Math.min(item.error_pct, 100)}%` }}
                      />
                    </div>
                    <span className="text-sm text-slate-300 w-12 text-right">
                      {item.error_pct.toFixed(1)}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-4">
        <div className="text-sm text-slate-400">
          Showing {startIndex + 1} to {Math.min(startIndex + itemsPerPage, filteredData.length)} of {filteredData.length} errors
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
            disabled={currentPage === 1}
            className="px-3 py-1 bg-slate-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600 transition-colors"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-slate-300">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
            disabled={currentPage === totalPages}
            className="px-3 py-1 bg-slate-700 text-white rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-600 transition-colors"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
