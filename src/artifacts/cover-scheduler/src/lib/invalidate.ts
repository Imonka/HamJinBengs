import { useQueryClient } from "@tanstack/react-query";
import { getGetCurrentUserQueryKey } from "@workspace/api-client-react";

/** Invalidate every data query (not the signed-in user) after a mutation. */
export function useInvalidateOps() {
  const qc = useQueryClient();
  const me = getGetCurrentUserQueryKey()[0];
  return () => qc.invalidateQueries({ predicate: (q) => q.queryKey[0] !== me });
}
