import { useState, useEffect, useCallback, useRef } from 'react'

export function useFetch<T>(
  fetchFn: () => Promise<T>,
  deps: unknown[] = []
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refetchCounter, setRefetchCounter] = useState(0)
  const isMountedRef = useRef(true)

  const refetch = useCallback(() => {
    setRefetchCounter(prev => prev + 1)
  }, [])

  useEffect(() => {
    isMountedRef.current = true
    let cancelled = false

    const fetch = async () => {
      try {
        setLoading(true)
        setError(null)
        const result = await fetchFn()
        
        if (!cancelled && isMountedRef.current) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (!cancelled && isMountedRef.current) {
          setError(err instanceof Error ? err.message : 'Unknown error')
          setData(null)
        }
      } finally {
        if (!cancelled && isMountedRef.current) {
          setLoading(false)
        }
      }
    }

    fetch()

    return () => {
      cancelled = true
      isMountedRef.current = false
    }
  }, [...deps, refetchCounter])

  return { data, loading, error, refetch }
}
