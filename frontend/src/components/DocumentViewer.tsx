import { useEffect, useState } from "react";
import { api, ApiError } from "../api/client";

/** Visor embebido (Fase 4): trae el binario estampado como blob y lo muestra
 *  en un iframe dentro de un modal, sin sacar al usuario de la app. Sirve para
 *  PDF, imágenes y texto — lo mismo que acepta el botón "Ver". */
export function DocumentViewer({
  token,
  documentId,
  versionNumber,
  title,
  onClose,
}: {
  token: string;
  documentId: string;
  versionNumber: number;
  title: string;
  onClose: () => void;
}) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;
    api
      .viewVersionFile(token, documentId, versionNumber)
      .then(({ blob }) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "No se pudo abrir el archivo");
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, documentId, versionNumber]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal modal-viewer" onClick={(e) => e.stopPropagation()}>
        <div className="modal-viewer-head">
          <h2 title={title}>{title}</h2>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {url && (
              <a className="btn btn-secondary btn-sm" href={url} target="_blank" rel="noopener">
                Abrir en pestaña
              </a>
            )}
            <button className="btn btn-secondary btn-sm" onClick={onClose}>Cerrar</button>
          </div>
        </div>
        {error ? (
          <div className="alert alert-error">{error}</div>
        ) : url === null ? (
          <div className="empty-state">Cargando previsualización…</div>
        ) : (
          <iframe className="doc-viewer-frame" src={url} title={title} />
        )}
      </div>
    </div>
  );
}
