import { ArrowUp, ArrowDown, ArrowRight } from 'lucide-react'

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  trend?: 'up' | 'down' | 'neutral'
  color?: 'blue' | 'green' | 'red' | 'purple' | 'orange'
  icon?: React.ReactNode
}

const colorClasses = {
  blue: 'bg-blue-500',
  green: 'bg-green-500',
  red: 'bg-red-500',
  purple: 'bg-purple-500',
  orange: 'bg-orange-500'
}

const trendIcons = {
  up: <ArrowUp className="w-4 h-4 text-green-500" />,
  down: <ArrowDown className="w-4 h-4 text-red-500" />,
  neutral: <ArrowRight className="w-4 h-4 text-gray-500" />
}

export default function MetricCard({
  title,
  value,
  subtitle,
  trend,
  color = 'blue',
  icon
}: MetricCardProps) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 border border-slate-700 relative overflow-hidden">
      <div className={`absolute top-0 left-0 w-full h-1 ${colorClasses[color]}`} />
      
      {icon && (
        <div className="absolute top-4 right-4 text-slate-600">
          {icon}
        </div>
      )}
      
      <div className="space-y-2">
        <p className="text-sm text-slate-400">{title}</p>
        
        <div className="flex items-baseline gap-2">
          <p className="text-3xl font-bold text-white">{value}</p>
          {trend && trendIcons[trend]}
        </div>
        
        {subtitle && (
          <p className="text-xs text-slate-500">{subtitle}</p>
        )}
      </div>
    </div>
  )
}
