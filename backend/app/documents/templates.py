"""Plantillas de documentos (Fase 5b).

Un archivo base del tenant desde el cual se crean documentos nuevos,
estandarizando el formato del SGSI. Vive aparte del ciclo de aprobación: una
plantilla no es evidencia ni tiene versiones — es solo el punto de partida.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.documents import storage
from app.documents.models import DocumentTemplate
from app.documents.service import DocumentError


class TemplateNotFound(DocumentError):
    pass


def create_template(
    db: Session,
    tenant_id: str,
    *,
    name: str,
    description: str | None,
    document_type: str,
    created_by: str,
    file_content: bytes,
    original_filename: str,
    content_type: str | None,
) -> DocumentTemplate:
    template_id = uuid.uuid4()
    storage_ref = storage.build_storage_ref(tenant_id, "templates", template_id)
    storage.save(storage_ref, file_content)
    template = DocumentTemplate(
        id=template_id,
        tenant_id=tenant_id,
        name=name,
        description=description,
        document_type=document_type,
        storage_ref=storage_ref,
        original_filename=original_filename,
        content_type=content_type,
        file_size=len(file_content),
        created_by=created_by,
    )
    db.add(template)
    db.flush()
    return template


def list_templates(db: Session, tenant_id: str) -> list[DocumentTemplate]:
    return list(
        db.scalars(
            select(DocumentTemplate)
            .where(DocumentTemplate.tenant_id == tenant_id)
            .order_by(DocumentTemplate.name)
        )
    )


def get_template(db: Session, tenant_id: str, template_id: uuid.UUID) -> DocumentTemplate:
    template = db.scalars(
        select(DocumentTemplate).where(
            DocumentTemplate.id == template_id, DocumentTemplate.tenant_id == tenant_id
        )
    ).first()
    if template is None:
        raise TemplateNotFound(str(template_id))
    return template


def read_template_file(db: Session, tenant_id: str, template_id: uuid.UUID) -> tuple[DocumentTemplate, bytes]:
    template = get_template(db, tenant_id, template_id)
    path = storage.path_for(template.storage_ref)
    return template, path.read_bytes()


def delete_template(db: Session, tenant_id: str, template_id: uuid.UUID) -> None:
    template = get_template(db, tenant_id, template_id)
    db.delete(template)
    db.flush()
