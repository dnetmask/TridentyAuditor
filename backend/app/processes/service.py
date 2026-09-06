"""MOD·PRC — lógica del mapa de procesos."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.documents.models import Document
from app.processes.models import DocumentProcessLink, Process


class ProcessError(Exception):
    """Violación de regla de negocio del mapa de procesos (409/404/422)."""


class ProcessNotFound(ProcessError):
    pass


class UnknownDocument(ProcessError):
    """Algún document_id del enlace no existe en el tenant."""


class InvalidParent(ProcessError):
    """El padre no existe, es el propio proceso, o crearía un ciclo."""


def _get(db: Session, tenant_id: str, process_id: uuid.UUID) -> Process:
    stmt = (
        select(Process)
        .where(Process.id == process_id, Process.tenant_id == tenant_id)
        .options(selectinload(Process.document_links))
    )
    process = db.scalars(stmt).first()
    if process is None:
        raise ProcessNotFound(str(process_id))
    return process


def list_processes(db: Session, tenant_id: str) -> list[Process]:
    stmt = (
        select(Process)
        .where(Process.tenant_id == tenant_id)
        .options(selectinload(Process.document_links))
        .order_by(Process.order_index, Process.name)
    )
    return list(db.scalars(stmt))


def _validate_parent(
    db: Session, tenant_id: str, process_id: uuid.UUID | None, parent_id: uuid.UUID | None
) -> None:
    if parent_id is None:
        return
    if process_id is not None and parent_id == process_id:
        raise InvalidParent("Un proceso no puede ser su propio padre")
    parent = db.scalars(
        select(Process).where(Process.id == parent_id, Process.tenant_id == tenant_id)
    ).first()
    if parent is None:
        raise InvalidParent("El proceso padre no existe en este tenant")
    # Evitar ciclos: subir por la cadena de padres desde el candidato.
    seen: set[uuid.UUID] = set()
    cursor: uuid.UUID | None = parent_id
    while cursor is not None:
        if cursor == process_id:
            raise InvalidParent("La jerarquía no puede formar un ciclo")
        if cursor in seen:
            break
        seen.add(cursor)
        node = db.scalars(select(Process).where(Process.id == cursor)).first()
        cursor = node.parent_id if node else None


def _set_document_links(
    db: Session, process: Process, tenant_id: str, document_ids: list[uuid.UUID]
) -> None:
    unique_ids = list(dict.fromkeys(document_ids))
    if unique_ids:
        found = set(
            db.scalars(
                select(Document.id).where(
                    Document.id.in_(unique_ids), Document.tenant_id == tenant_id
                )
            )
        )
        missing = [str(d) for d in unique_ids if d not in found]
        if missing:
            raise UnknownDocument(", ".join(missing))
    process.document_links.clear()
    db.flush()
    for document_id in unique_ids:
        db.add(
            DocumentProcessLink(
                tenant_id=tenant_id, process_id=process.id, document_id=document_id
            )
        )
    db.flush()


def create_process(
    db: Session,
    tenant_id: str,
    *,
    name: str,
    description: str | None,
    parent_id: uuid.UUID | None,
    owner_user_id: uuid.UUID | None,
    order_index: int,
    document_ids: list[uuid.UUID],
) -> Process:
    _validate_parent(db, tenant_id, None, parent_id)
    process = Process(
        tenant_id=tenant_id,
        name=name,
        description=description,
        parent_id=parent_id,
        owner_user_id=owner_user_id,
        order_index=order_index,
    )
    db.add(process)
    db.flush()
    if document_ids:
        _set_document_links(db, process, tenant_id, document_ids)
    db.refresh(process)
    return process


_UNSET = object()


def update_process(
    db: Session,
    tenant_id: str,
    process_id: uuid.UUID,
    *,
    name: str | None = None,
    description: str | None | object = _UNSET,
    parent_id: uuid.UUID | None | object = _UNSET,
    owner_user_id: uuid.UUID | None | object = _UNSET,
    order_index: int | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> Process:
    process = _get(db, tenant_id, process_id)
    if name is not None:
        process.name = name
    if description is not _UNSET:
        process.description = description
    if parent_id is not _UNSET:
        _validate_parent(db, tenant_id, process_id, parent_id)
        process.parent_id = parent_id
    if owner_user_id is not _UNSET:
        process.owner_user_id = owner_user_id
    if order_index is not None:
        process.order_index = order_index
    if document_ids is not None:
        _set_document_links(db, process, tenant_id, document_ids)
    db.flush()
    db.refresh(process)
    return process


def delete_process(db: Session, tenant_id: str, process_id: uuid.UUID) -> None:
    process = _get(db, tenant_id, process_id)
    # Los hijos quedan huérfanos (parent_id → NULL por el FK); los enlaces de
    # documentos se borran en cascada. No se tocan los documentos en sí.
    db.execute(
        select(Process).where(Process.parent_id == process_id, Process.tenant_id == tenant_id)
    )
    for child in db.scalars(
        select(Process).where(Process.parent_id == process_id, Process.tenant_id == tenant_id)
    ):
        child.parent_id = None
    db.delete(process)
    db.flush()


def build_tree(db: Session, tenant_id: str) -> list[dict]:
    """Árbol de procesos con documentos por nodo y conteo acumulado.

    ``document_count`` incluye los documentos de los subprocesos, para que el
    dashboard/mapa muestre el peso real de un proceso raíz de un vistazo.
    """
    processes = list_processes(db, tenant_id)
    doc_ids = {link.document_id for p in processes for link in p.document_links}
    docs_by_id: dict[uuid.UUID, Document] = {}
    if doc_ids:
        docs_by_id = {
            d.id: d
            for d in db.scalars(
                select(Document).where(
                    Document.id.in_(doc_ids), Document.tenant_id == tenant_id
                )
            )
        }

    nodes: dict[uuid.UUID, dict] = {}
    for p in processes:
        nodes[p.id] = {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "parent_id": p.parent_id,
            "owner_user_id": p.owner_user_id,
            "order_index": p.order_index,
            "created_at": p.created_at,
            "documents": [
                {"id": docs_by_id[link.document_id].id,
                 "code": docs_by_id[link.document_id].code,
                 "title": docs_by_id[link.document_id].title}
                for link in p.document_links
                if link.document_id in docs_by_id
            ],
            "children": [],
            "document_count": 0,
        }

    roots: list[dict] = []
    for p in processes:
        node = nodes[p.id]
        parent = nodes.get(p.parent_id) if p.parent_id else None
        if parent is not None:
            parent["children"].append(node)
        else:
            roots.append(node)

    def count(node: dict) -> int:
        total = len(node["documents"]) + sum(count(c) for c in node["children"])
        node["document_count"] = total
        return total

    for root in roots:
        count(root)
    return roots
