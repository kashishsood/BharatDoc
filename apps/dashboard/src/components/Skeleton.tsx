interface SkeletonCardProps {
  height?: string
  className?: string
}

export default function SkeletonCard({ height = '200px', className = '' }: SkeletonCardProps) {
  return (
    <div 
      className={`bg-slate-800 rounded-xl animate-pulse ${className}`}
      style={{ height }}
    />
  )
}
