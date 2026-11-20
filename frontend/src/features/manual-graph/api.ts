import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router';
import { request, type HttpMethod } from '@/shared/api/client';
import type { GraphNodeType } from '@/shared/api';

export interface WorkspaceUser {
  id: string;
  username: string;
}
export interface ManualNode {
  id: string;
  kind: GraphNodeType;
  label: string;
  notes: string;
  source: string;
}
export interface ManualEdge {
  id: string;
  source_id: string;
  target_id: string;
  label: string;
  notes: string;
  source: string;
}
export interface WorkspaceSummary {
  id: string;
  official_id: string;
  owner_id: string;
  owner_name: string;
  title: string;
  created_at: string;
  can_edit: boolean;
}
export interface Workspace extends WorkspaceSummary {
  nodes: ManualNode[];
  edges: ManualEdge[];
  shared_with: WorkspaceUser[];
}
export function useGraphWorkspace(officialId: string) {
  const client = useQueryClient();
  const [params, setParams] = useSearchParams();
  const activeId = params.get('scheme');
  const list = useQuery({
    queryKey: ['graph-workspaces', officialId],
    queryFn: () =>
      request<WorkspaceSummary[]>('GET', '/graph-workspaces', {
        query: { official_id: officialId },
      }),
  });
  const detail = useQuery({
    queryKey: ['graph-workspace', activeId],
    queryFn: () => request<Workspace>('GET', `/graph-workspaces/${activeId}`),
    enabled: Boolean(activeId),
    refetchInterval: 15000,
    retry: false,
  });
  const select = (id: string | null) => {
    setParams(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (id) next.set('scheme', id);
        else next.delete('scheme');
        return next;
      },
      { replace: true },
    );
  };
  const mutation = useMutation({
    mutationFn: ({ method, path, body }: { method: HttpMethod; path: string; body?: unknown }) =>
      request<Workspace | undefined>(method, path, { body }),
    onSuccess: (workspace) => {
      if (workspace) {
        client.setQueryData(['graph-workspace', workspace.id], workspace);
        select(workspace.id);
      }
      void client.invalidateQueries({ queryKey: ['graph-workspaces', officialId] });
    },
  });
  const workspace =
    !detail.isError && detail.data?.official_id === officialId ? detail.data : undefined;
  return { officialId, activeId, list, detail, workspace, select, mutation };
}
export type WorkspaceController = ReturnType<typeof useGraphWorkspace>;
