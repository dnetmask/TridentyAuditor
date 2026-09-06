import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { DocumentViewer } from "../components/DocumentViewer";
import type { DirectoryUser, DocumentDetail, Process, ProcessNode } from "../api/types";

export function ProcessesPage() {
  const { session } = useAuth();
  const token = session!.token;
  const canManage = session!.role === "tenant_admin";

  const [tree, setTree] = useState<ProcessNode[] | null>(null);
  const [flat, setFlat] = useState<Process[]>([]);
  const [documents, setDocuments] = useState<DocumentDetail[]>([]);
  const [directory, setDirectory] = useState<DirectoryUser[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ process?: Process } | null>(null);
  const [viewing, setViewing] = useState<{ documentId: string; version: number; title: string } | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    try {
      setTree(await api.processTree(token));
      api.listProcesses(token).then(setFlat).catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo cargar el mapa de procesos");
    }
  }

  useEffect(() => {
    reload();
    api.listDocuments(token).then(setDocuments).catch(() => {});
    api.directory(token).then(setDirectory).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function runAction(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "La operación falló");
    } finally {
      setBusy(false);
    }
  }

  function latestApprovedVersion(documentId: string): number | null {
    const doc = documents.find((d) => d.id === documentId);
    if (!doc) return null;
    const approved = doc.versions
      .filter((v) => v.status === "approved")
      .sort((a, b) => b.version_number - a.version_number)[0];
    return approved?.version_number ?? doc.versions.sort((a, b) => b.version_number - a.version_number)[0]?.version_number ?? null;
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Mapa de procesos</h1>
          <p>
            MOD·PRC — los procesos del SGSI y los documentos que cuelgan de cada uno.
            Haz clic en un documento para previsualizarlo sin salir de la pantalla.
          </p>
        </div>
        {canManage && (
          <button className="btn btn-primary" onClick={() => setEditing({})}>
            + Nuevo proceso
          </button>
        )}
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}

      <div className="card">
        {tree === null ? (
          <div className="empty-state">Cargando…</div>
        ) : tree.length === 0 ? (
          <div className="empty-state">
            Todavía no hay procesos. {canManage ? "Crea el primero para empezar a armar el mapa." : ""}
          </div>
        ) : (
          <div className="process-tree">
            {tree.map((node) => (
              <ProcessBranch
                key={node.id}
                node={node}
                depth={0}
                canManage={canManage}
                busy={busy}
                onEdit={(p) => setEditing({ process: p })}
                onDelete={(id) => runAction(() => api.deleteProcess(token, id))}
                onView={(documentId, title) => {
                  const version = latestApprovedVersion(documentId);
                  if (version != null) setViewing({ documentId, version, title });
                }}
              />
            ))}
          </div>
        )}
      </div>

      {editing && (
        <ProcessFormModal
          token={token}
          existing={editing.process}
          processes={flat}
          documents={documents}
          directory={directory}
          onClose={() => setEditing(null)}
          onSaved={async () => {
            setEditing(null);
            await reload();
          }}
        />
      )}

      {viewing && (
        <DocumentViewer
          token={token}
          documentId={viewing.documentId}
          versionNumber={viewing.version}
          title={viewing.title}
          onClose={() => setViewing(null)}
        />
      )}
    </div>
  );
}

function ProcessBranch({
  node,
  depth,
  canManage,
  busy,
  onEdit,
  onDelete,
  onView,
}: {
  node: ProcessNode;
  depth: number;
  canManage: boolean;
  busy: boolean;
  onEdit: (p: Process) => void;
  onDelete: (id: string) => void;
  onView: (documentId: string, title: string) => void;
}) {
  const [open, setOpen] = useState(depth === 0);
  const hasChildren = node.children.length > 0;
  const hasDocs = node.documents.length > 0;

  return (
    <div className="process-branch" style={{ marginLeft: depth * 20 }}>
      <div className="process-node">
        <button
          className="process-toggle"
          onClick={() => setOpen((o) => !o)}
          disabled={!hasChildren && !hasDocs}
          aria-label={open ? "Contraer" : "Expandir"}
        >
          {hasChildren || hasDocs ? (open ? "▾" : "▸") : "·"}
        </button>
        <strong className="process-name">{node.name}</strong>
        <span className="process-count">{node.document_count} doc.</span>
        {canManage && (
          <span className="process-actions">
            <button className="btn btn-secondary btn-sm" disabled={busy} onClick={() => onEdit(node)}>
              Editar
            </button>
            <button className="btn btn-danger btn-sm" disabled={busy} onClick={() => onDelete(node.id)}>
              Eliminar
            </button>
          </span>
        )}
      </div>
      {node.description && open && <div className="process-desc">{node.description}</div>}
      {open && (
        <>
          {node.documents.map((d) => (
            <button key={d.id} className="process-doc" onClick={() => onView(d.id, `${d.code} · ${d.title}`)}>
              <span className="process-doc-code">{d.code}</span> {d.title}
            </button>
          ))}
          {node.children.map((child) => (
            <ProcessBranch
              key={child.id}
              node={child}
              depth={depth + 1}
              canManage={canManage}
              busy={busy}
              onEdit={onEdit}
              onDelete={onDelete}
              onView={onView}
            />
          ))}
        </>
      )}
    </div>
  );
}

function ProcessFormModal({
  token,
  existing,
  processes,
  documents,
  directory,
  onClose,
  onSaved,
}: {
  token: string;
  existing?: Process;
  processes: Process[];
  documents: DocumentDetail[];
  directory: DirectoryUser[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const isEdit = existing != null;
  const [name, setName] = useState(existing?.name ?? "");
  const [description, setDescription] = useState(existing?.description ?? "");
  const [parentId, setParentId] = useState(existing?.parent_id ?? "");
  const [ownerId, setOwnerId] = useState(existing?.owner_user_id ?? "");
  const [documentIds, setDocumentIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // Al editar, precargar los documentos ya vinculados desde el árbol.
  useEffect(() => {
    if (!isEdit) return;
    api
      .processTree(token)
      .then((tree) => {
        const find = (nodes: ProcessNode[]): ProcessNode | undefined => {
          for (const n of nodes) {
            if (n.id === existing.id) return n;
            const inChild = find(n.children);
            if (inChild) return inChild;
          }
          return undefined;
        };
        const node = find(tree);
        if (node) setDocumentIds(node.documents.map((d) => d.id));
      })
      .catch(() => {});
  }, [isEdit, existing, token]);

  const availableParents = useMemo(
    () => processes.filter((p) => p.id !== existing?.id),
    [processes, existing],
  );
  const linked = documents.filter((d) => documentIds.includes(d.id));
  const available = documents.filter((d) => !documentIds.includes(d.id) && !d.retired_at);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const payload = {
        name,
        description: description || null,
        parent_id: parentId || null,
        owner_user_id: ownerId || null,
        document_ids: documentIds,
      };
      if (isEdit) await api.updateProcess(token, existing.id, payload);
      else await api.createProcess(token, payload);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo guardar el proceso");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? `Editar ${existing.name}` : "Nuevo proceso"}</h2>
        {error && <div className="alert alert-error" style={{ marginBottom: "1rem" }}>{error}</div>}
        <form className="stacked" onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="p-name">Nombre</label>
            <input id="p-name" required value={name} onChange={(e) => setName(e.target.value)} placeholder="ej. Gestión Humana" />
          </div>
          <div className="field">
            <label htmlFor="p-desc">Descripción (opcional)</label>
            <textarea id="p-desc" rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="p-parent">Proceso padre (opcional)</label>
            <select id="p-parent" value={parentId} onChange={(e) => setParentId(e.target.value)}>
              <option value="">— proceso raíz —</option>
              {availableParents.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="p-owner">Responsable (opcional)</label>
            <select id="p-owner" value={ownerId} onChange={(e) => setOwnerId(e.target.value)}>
              <option value="">— sin responsable —</option>
              {directory.map((u) => (
                <option key={u.id} value={u.id}>{u.full_name}</option>
              ))}
            </select>
          </div>
          <div className="field">
            <label>Documentos del proceso</label>
            <div className="control-chips">
              {linked.map((d) => (
                <span className="control-chip" key={d.id} title={d.title}>
                  {d.code}
                  <button type="button" aria-label={`Quitar ${d.code}`} onClick={() => setDocumentIds((ids) => ids.filter((id) => id !== d.id))}>
                    ×
                  </button>
                </span>
              ))}
              <select value="" onChange={(e) => e.target.value && setDocumentIds((ids) => [...ids, e.target.value])}>
                <option value="">+ vincular documento…</option>
                {available.map((d) => (
                  <option key={d.id} value={d.id}>{d.code} · {d.title}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancelar</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Guardando…" : isEdit ? "Guardar" : "Crear"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
