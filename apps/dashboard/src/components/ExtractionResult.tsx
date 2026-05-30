import type { ExtractionResult as ExtractionResultType } from '../types';

interface ExtractionResultProps {
  result: ExtractionResultType;
}

const DOC_TYPE_COLORS: Record<string, string> = {
  aadhaar: 'bg-blue-600',
  invoice: 'bg-green-600',
  lic_policy: 'bg-purple-600',
  handwritten_form: 'bg-orange-600',
  printed_form: 'bg-pink-600',
  default: 'bg-slate-600'
};

const formatFieldName = (fieldName: string): string => {
  return fieldName
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

const getConfidenceColor = (score: number): string => {
  if (score >= 0.85) return 'text-green-400';
  if (score >= 0.7) return 'text-yellow-400';
  return 'text-red-400';
};

export default function ExtractionResult({ result }: ExtractionResultProps) {
  const docTypeColor = DOC_TYPE_COLORS[result.document_type] || DOC_TYPE_COLORS.default;
  const confidenceColor = getConfidenceColor(result.confidence_score);

  return (
    <div className="bg-slate-800 rounded-lg p-6 shadow-lg fade-in">
      <div className="flex items-start justify-between mb-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className={`${docTypeColor} text-white px-3 py-1 rounded-full text-sm font-medium`}>
              {formatFieldName(result.document_type)}
            </span>
            <span className="bg-slate-700 text-slate-300 px-3 py-1 rounded-full text-xs">
              {result.model_used}
            </span>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div>
              <span className="text-slate-400">Confidence: </span>
              <span className={`font-semibold ${confidenceColor}`}>
                {(result.confidence_score * 100).toFixed(1)}%
              </span>
            </div>
            <div>
              <span className="text-slate-400">Latency: </span>
              <span className="text-white font-semibold">
                {result.latency_ms.toFixed(0)}ms
              </span>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-700 pt-4">
        <h4 className="text-lg font-semibold text-white mb-4">Extracted Fields</h4>
        <div className="space-y-3">
          {Object.entries(result.extracted_fields).map(([key, value]) => (
            <div key={key} className="flex items-start justify-between py-2 border-b border-slate-700/50">
              <span className="text-slate-400 text-sm font-medium">
                {formatFieldName(key)}
              </span>
              <span className="text-white text-sm font-mono ml-4 text-right">
                {String(value)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
