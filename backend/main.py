import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, Optional

import psycopg2
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://ciudadai:ciudadai_secure_pwd@db:5432/ciudadai_db",
)

app = FastAPI(title="CiudadAI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGINS", "*")],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TicketCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=100)
    apellidos: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=255)
    categoria: str = Field(min_length=2, max_length=50)
    descripcion: str = Field(min_length=10, max_length=2000)
    canal: str = Field(default="Web", max_length=20)
    telefono: Optional[str] = Field(default=None, max_length=30)
    direccion_persona: Optional[str] = Field(default=None, max_length=255)
    ubicacion_incidencia: Optional[str] = Field(default=None, max_length=255)


class TicketResponse(BaseModel):
    id: int
    descripcion: str
    categoria: str
    canal: str
    urgencia_predicha: int
    confianza: float
    fecha_creacion: datetime
    mensaje: str


class TicketDetail(TicketResponse):
    nombre_anonimizado: Optional[str] = None
    apellidos_anonimizado: Optional[str] = None
    email_anonimizado: Optional[str] = None
    telefono_anonimizado: Optional[str] = None
    direccion_anonimizado: Optional[str] = None
    ubicacion_descripcion: Optional[str] = None


@contextmanager
def get_connection() -> Generator[psycopg2.extensions.connection, None, None]:
    connection = psycopg2.connect(DATABASE_URL)
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def predict_urgency(categoria: str, descripcion: str) -> tuple[int, float]:
    text = f"{categoria} {descripcion}".lower()

    high_priority_keywords = ["fuga", "incendio", "peligro", "accidente", "urgente", "rotura"]
    medium_priority_keywords = ["basura", "bache", "alumbrado", "ruido", "árbol", "arbol"]

    if any(keyword in text for keyword in high_priority_keywords):
        return 5, 0.94
    if any(keyword in text for keyword in medium_priority_keywords):
        return 3, 0.76
    if categoria.lower() in {"seguridad", "emergencia", "sanidad"}:
        return 4, 0.81
    return 2, 0.65


def anonymize_name(value: str) -> str:
    return f"{value[:1].upper()}***" if value else None


def anonymize_email(value: str) -> str:
    if not value or "@" not in value:
        return None
    local_part, domain = value.split("@", 1)
    return f"{local_part[:1]}***@{domain}"


def anonymize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) < 4:
        return "***"
    return f"***{digits[-3:]}"


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/tickets", response_model=TicketResponse)
def create_ticket(ticket: TicketCreate) -> TicketResponse:
    urgency, confidence = predict_urgency(ticket.categoria, ticket.descripcion)

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO tickets (
                    descripcion,
                    categoria,
                    urgencia_predicha,
                    canal,
                    ubicacion_descripcion,
                    persona_anonimizado,
                    apellidos_anonimizado,
                    nif_anonimizado,
                    telefono_anonimizado,
                    email_anonimizado,
                    direccion_anonimizado,
                    anonimizacion_hash,
                    modelo_version
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, md5(%s), %s)
                RETURNING id, fecha_creacion
                """,
                (
                    ticket.descripcion,
                    ticket.categoria,
                    urgency,
                    ticket.canal,
                    ticket.ubicacion_incidencia,
                    anonymize_name(ticket.nombre),
                    anonymize_name(ticket.apellidos),
                    None,
                    anonymize_phone(ticket.telefono),
                    anonymize_email(ticket.email),
                    anonymize_name(ticket.direccion_persona or ""),
                    f"{ticket.nombre}|{ticket.apellidos}|{ticket.email}|{ticket.descripcion}",
                    "v1.0",
                ),
            )
            ticket_id, fecha_creacion = cursor.fetchone()

            cursor.execute(
                """
                INSERT INTO predicciones (
                    ticket_id,
                    urgencia_predicha,
                    confianza,
                    modelo_version
                )
                VALUES (%s, %s, %s, %s)
                """,
                (ticket_id, urgency, confidence, "v1.0"),
            )

    return TicketResponse(
        id=ticket_id,
        descripcion=ticket.descripcion,
        categoria=ticket.categoria,
        canal=ticket.canal,
        urgencia_predicha=urgency,
        confianza=confidence,
        fecha_creacion=fecha_creacion,
        mensaje="Ticket creado correctamente",
    )


@app.get("/api/tickets/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: int) -> TicketDetail:
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    descripcion,
                    categoria,
                    canal,
                    urgencia_predicha,
                    fecha_creacion,
                    persona_anonimizado,
                    apellidos_anonimizado,
                    email_anonimizado,
                    telefono_anonimizado,
                    direccion_anonimizado,
                    ubicacion_descripcion
                FROM tickets
                WHERE id = %s
                """,
                (ticket_id,),
            )
            row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")

    ticket_id_value, descripcion, categoria, canal, urgencia_predicha, fecha_creacion, nombre_anonimizado, apellidos_anonimizado, email_anonimizado, telefono_anonimizado, direccion_anonimizado, ubicacion_descripcion = row

    return TicketDetail(
        id=ticket_id_value,
        descripcion=descripcion,
        categoria=categoria,
        canal=canal,
        urgencia_predicha=urgencia_predicha or 0,
        confianza=0.0,
        fecha_creacion=fecha_creacion,
        mensaje="Ticket recuperado correctamente",
        nombre_anonimizado=nombre_anonimizado,
        apellidos_anonimizado=apellidos_anonimizado,
        email_anonimizado=email_anonimizado,
        telefono_anonimizado=telefono_anonimizado,
        direccion_anonimizado=direccion_anonimizado,
        ubicacion_descripcion=ubicacion_descripcion,
    )


@app.get("/api/hello")
def hello() -> dict[str, str]:
    return {"message": "CiudadAI API lista"}
