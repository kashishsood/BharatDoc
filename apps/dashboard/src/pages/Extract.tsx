import { useState } from 'react';
import DocumentUpload from '../components/DocumentUpload';
import ExtractionResult from '../components/ExtractionResult';
import type { ExtractionResult as ExtractionResultType } from '../types';

export default function Extract() {
  const [result, setResult] = useState<ExtractionResultType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ExtractionResultType[]>([]);

  const handleResult = (newResult: ExtractionResultType) => {
    setResult(newResult);
    setError(null);
    setHistory(prev => [newResult, ...prev].slice(0, 5));
  };

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleReset = () => {
    setResult(null);
    setError(null);
  };

  return (
    <div className="p-6">
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-2">
          <DocumentUpload onResult={handleResult} onError={handleError} />
          
          {error && (
            <div className="mt-4 bg-red-900/20 border border-red-500 rounded-lg p-4">
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          )}
        </div>

        <div className="lg:col-span-3">
          {result ? (
            <div className="space-y-4">
              <ExtractionResult result={result} />
              <button
                onClick={handleReset}
                className="w-full bg-slate-700 hover:bg-slate-600 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                Extract Another Document
              </button>
            </div>
          ) : (
            <div className="bg-slate-800 rounded-lg p-12 text-center h-full flex flex-col items-center justify-center">
              <svg className="w-24 h-24 text-slate-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-xl font-semibold text-slate-400 mb-2">
                Upload a document to see extraction results
              </h3>
              <p className="text-slate-500">
                Supported formats: Aadhaar, Invoice, LIC Policy, Forms
              </p>
            </div>
          )}
        </div>
      </div>

      {history.length > 0 && (
        <div className="mt-8">
          <h3 className="text-xl font-semibold text-white mb-4">Recent Extractions</h3>
          <div className="space-y-4 max-h-96 overflow-y-auto">
            {history.map((item, index) => (
              <div
                key={index}
                className="bg-slate-800 rounded-lg p-4 hover:bg-slate-700 transition-colors cursor-pointer"
                onClick={() => setResult(item)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="bg-blue-600 text-white px-3 py-1 rounded text-sm">
                      {item.document_type}
                    </span>
                    <span className="text-slate-400 text-sm">{item.model_used}</span>
                  </div>
                  <div className="flex items-center gap-4 text-sm">
                    <span className="text-slate-400">
                      F1: <span className="text-white">{(item.confidence_score * 100).toFixed(1)}%</span>
                    </span>
                    <span className="text-slate-400">
                      {item.latency_ms.toFixed(0)}ms
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
