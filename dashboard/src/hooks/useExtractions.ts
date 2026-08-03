import { useQuery } from '@tanstack/react-query';
import { api, ExtractionRecord } from '../utils/api';

export function useExtractions() {
  return useQuery<ExtractionRecord[]>({
    queryKey: ['extractions'],
    queryFn: api.getExtractions,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}
