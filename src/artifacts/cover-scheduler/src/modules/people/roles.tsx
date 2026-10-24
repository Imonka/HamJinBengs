import { useState } from "react";
import { Plus, Trash2, Pencil } from "lucide-react";
import { useListRoles, useCreateRole, useUpdateRole, useDeleteRole, type Role } from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useToast } from "@/hooks/use-toast";
import { Panel, SkeletonRows, ErrorState, Empty } from "@/components/kit";
import { errMsg } from "@/lib/api-error";
import { useInvalidateOps } from "@/lib/invalidate";
import { cn } from "@/lib/utils";

const PALETTE = ["#1f6f78", "#e8a317", "#c4473a", "#4f7b52", "#5b5f97", "#a0522d", "#2f8f9d", "#8a6d3b"];

/* ---------------- Roles ---------------- */
function RoleRow({ r }: { r: Role }) {
  const upd = useUpdateRole();
  const del = useDeleteRole();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [name, setName] = useState(r.name);
  const [editing, setEditing] = useState(false);
  const save = (data: { name: string; color?: string }) => upd.mutate({ roleId: r.id, data }, {
    onSuccess: () => { invalidate(); setEditing(false); }, onError: (e) => toast({ title: "Could not save role", description: errMsg(e), variant: "destructive" }),
  });
  return (
    <div className="flex items-center gap-3 px-4 py-2.5" data-testid={`row-role-${r.id}`}>
      <div className="flex gap-1">
        {PALETTE.map((c) => (
          <button key={c} onClick={() => save({ name: r.name, color: c })} aria-label={`Colour ${c}`} data-testid={`button-role-color-${r.id}-${c.slice(1)}`}
            className={cn("h-5 w-5 rounded-full transition-transform hover:scale-110", r.color.toLowerCase() === c && "ring-2 ring-offset-2 ring-offset-card ring-foreground/60")} style={{ background: c }} />
        ))}
      </div>
      {editing ? (
        <form className="flex-1 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (name.trim()) save({ name: name.trim(), color: r.color }); }}>
          <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus className="h-8" data-testid={`input-role-name-${r.id}`} />
          <Button size="sm" type="submit" disabled={upd.isPending}>Save</Button>
          <Button size="sm" type="button" variant="ghost" onClick={() => { setEditing(false); setName(r.name); }}>Cancel</Button>
        </form>
      ) : (
        <div className="flex-1 flex items-center gap-2 min-w-0">
          <span className="font-medium truncate">{r.name}</span>
          <span className="font-mono text-xs text-muted-foreground">{r.employeeCount} people</span>
        </div>
      )}
      {!editing && <Button size="icon" variant="ghost" onClick={() => setEditing(true)} data-testid={`button-rename-role-${r.id}`}><Pencil className="h-4 w-4" /></Button>}
      <Button size="icon" variant="ghost" className="text-destructive hover:text-destructive" disabled={del.isPending} data-testid={`button-delete-role-${r.id}`}
        onClick={() => { if (confirm(`Delete role ${r.name}?`)) del.mutate({ roleId: r.id }, { onSuccess: () => { invalidate(); toast({ title: "Role deleted" }); }, onError: (e) => toast({ title: "Cannot delete role", description: errMsg(e), variant: "destructive" }) }); }}>
        <Trash2 className="h-4 w-4" />
      </Button>
    </div>
  );
}

export function RolesTab() {
  const q = useListRoles();
  const create = useCreateRole();
  const invalidate = useInvalidateOps();
  const { toast } = useToast();
  const [name, setName] = useState("");
  const add = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    create.mutate({ data: { name: name.trim(), color: PALETTE[(q.data?.length ?? 0) % PALETTE.length] } }, {
      onSuccess: () => { invalidate(); setName(""); }, onError: (err) => toast({ title: "Could not add role", description: errMsg(err), variant: "destructive" }),
    });
  };
  return (
    <div className="max-w-3xl">
      <Panel title="Job roles" action={<span className="text-xs text-muted-foreground">Cover is only offered within the same role</span>}>
        {q.isLoading ? <SkeletonRows n={4} /> : q.isError ? <ErrorState what="roles" onRetry={() => q.refetch()} /> : !q.data?.length ? (
          <Empty icon={<Plus className="h-5 w-5" />} title="No roles yet" body="Add roles like Cashier, Server, Chef." />
        ) : <div className="divide-y">{q.data.map((r) => <RoleRow key={r.id} r={r} />)}</div>}
        <form onSubmit={add} className="flex gap-2 p-4 border-t">
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="New role, e.g. Barista" data-testid="input-new-role" />
          <Button type="submit" disabled={!name.trim() || create.isPending} data-testid="button-add-role"><Plus className="h-4 w-4 mr-1.5" />Add role</Button>
        </form>
      </Panel>
    </div>
  );
}

