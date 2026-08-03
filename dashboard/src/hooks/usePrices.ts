import { useQuery } from '@tanstack/react-query';
import { api, MineralPrice } from '../utils/api';

export function usePrices() {
  return useQuery<MineralPrice[]>({
    queryKey: ['prices'],
    queryFn: api.getPrices,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}
