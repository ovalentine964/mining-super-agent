import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Proposal } from '../utils/api';

export function useProposals() {
  return useQuery<Proposal[]>({
    queryKey: ['proposals'],
    queryFn: api.getProposals,
    refetchInterval: 30_000,
    staleTime: 15_000,
  });
}

export function useVote() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ proposalId, support, voter }: { proposalId: string; support: boolean; voter: string }) =>
      api.voteOnProposal(proposalId, support, voter),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['proposals'] }),
  });
}
