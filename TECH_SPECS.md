# CiudadAI – Especificaciones Técnicas (Para Desarrolladores)

---

## 1. Base de Datos: Schema PostgreSQL

### Tabla `tickets`
```sql
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    
    -- Core fields
    descripcion TEXT NOT NULL,
    categoria VARCHAR(50) NOT NULL CHECK (categoria IN (
        'Limpieza',
        'Alumbrado Público',
        'Movilidad',
        'Parques y Jardines',
        'Mobiliario Urbano'
    )),
    canal VARCHAR(10) NOT NULL CHECK (canal IN ('Web', 'App')),
    
    -- Predictions
    urgencia_predicha INT CHECK (urgencia_predicha >= 1 AND urgencia_predicha <= 5),
    urgencia_real INT CHECK (urgencia_real >= 1 AND urgencia_real <= 5),
    modelo_version VARCHAR(20) DEFAULT 'v1.0',
    
    -- Location
    ubicacion_incidencia POINT,
    ubicacion_descripcion TEXT,
    
    -- Anonymized PII (NUNCA guardar originales)
    persona_anonimizado VARCHAR(255),
    apellidos_anonimizado VARCHAR(255),
    nif_anonimizado VARCHAR(50),
    telefono_anonimizado VARCHAR(50),
    email_anonimizado VARCHAR(255),
    direccion_anonimizado VARCHAR(500),
    
    -- Audit trail
    anonimizacion_hash VARCHAR(64) NOT NULL UNIQUE, -- SHA256
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tickets_categoria ON tickets(categoria);
CREATE INDEX idx_tickets_urgencia_predicha ON tickets(urgencia_predicha);
CREATE INDEX idx_tickets_estado ON tickets(urgencia_predicha, urgencia_real);
```

### Tabla `predicciones`
```sql
CREATE TABLE predicciones (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    urgencia_predicha INT NOT NULL,
    confianza FLOAT NOT NULL CHECK (confianza >= 0 AND confianza <= 1),
    modelo_version VARCHAR(20) NOT NULL,
    fecha_prediccion TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_predicciones_ticket ON predicciones(ticket_id);
CREATE INDEX idx_predicciones_modelo ON predicciones(modelo_version);
```

### Tabla `validaciones` (Active Learning)
```sql
CREATE TABLE validaciones (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    urgencia_real INT NOT NULL CHECK (urgencia_real >= 1 AND urgencia_real <= 5),
    usuario_id VARCHAR(255),
    notas TEXT,
    procesado BOOLEAN DEFAULT FALSE,
    fecha_validacion TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_validaciones_ticket ON validaciones(ticket_id);
CREATE INDEX idx_validaciones_procesado ON validaciones(procesado);
```

### Tabla `anonimizacion_log` (Auditoría RGPD)
```sql
CREATE TABLE anonimizacion_log (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    entidades_detectadas JSONB NOT NULL,
    -- {"PERSON": 2, "PHONE": 1, "EMAIL": 1, "ID_NUMBER": 1, "LOCATION": 1}
    campos_anonimizados JSONB NOT NULL,
    -- {"nombre": true, "apellidos": true, "email": true, ...}
    fecha_anonimizacion TIMESTAMP DEFAULT NOW()
);
```

### Tabla `modelo_metadata` (Versionamiento)
```sql
CREATE TABLE modelo_metadata (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL, -- "v1.0", "v1.1"
    fecha_entrenamiento TIMESTAMP NOT NULL,
    datos_utilizados INT NOT NULL,
    mse FLOAT,
    r2 FLOAT,
    activo BOOLEAN DEFAULT FALSE,
    backup_anterior VARCHAR(20),
    fecha_creacion TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_modelo_activo ON modelo_metadata(activo) WHERE activo = true;
```

---

## 2. Backend: Estructura Módulos

### `main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CiudadAI API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir routers
from api import tickets, validations, stats, retrain

app.include_router(tickets.router, prefix="/api/tickets", tags=["tickets"])
app.include_router(validations.router, prefix="/api/validations", tags=["validations"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(retrain.router, prefix="/api/retrain", tags=["retrain"])

@app.get("/health")
def health():
    return {"status": "ok"}
```

### `models.py` (ORM)
```python
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, JSONB, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Ticket(Base):
    __tablename__ = "tickets"
    # ... (como en SQL arriba)

class Prediccion(Base):
    __tablename__ = "predicciones"
    # ...

class Validacion(Base):
    __tablename__ = "validaciones"
    # ...

class AnonimizacionLog(Base):
    __tablename__ = "anonimizacion_log"
    # ...

class ModeloMetadata(Base):
    __tablename__ = "modelo_metadata"
    # ...
```

### `services/anonymizer.py`
```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import hashlib

class DataAnonimizer:
    def __init__(self):
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
    
    def anonymize_ticket(self, ticket_data: dict) -> dict:
        """
        ticket_data: {nombre, apellidos, nif, telefono, email, direccion, ...}
        
        Returns:
        {
            "anonimizado": {...},
            "entidades_detectadas": {...},
            "hash_original": "sha256_hash"
        }
        """
        # Concatenar todos los campos sensibles
        pii_text = f"{ticket_data.get('nombre', '')} {ticket_data.get('apellidos', '')} "
        pii_text += f"{ticket_data.get('nif', '')} {ticket_data.get('telefono', '')} "
        pii_text += f"{ticket_data.get('email', '')} {ticket_data.get('direccion', '')}"
        
        # Detectar entidades
        results = self.analyzer.analyze(text=pii_text, language="es")
        
        # Contar entidades
        entidades_detectadas = {}
        for result in results:
            entidad = result.entity_type
            entidades_detectadas[entidad] = entidades_detectadas.get(entidad, 0) + 1
        
        # Anonimizar
        from presidio_anonymizer.entities import OperatorConfig
        anonimizado = self.anonymizer.anonymize(
            text=pii_text,
            analyzer_results=results,
            operators={"DEFAULT": OperatorConfig("replace", {"new_value": "<REDACTED>"})}
        )
        
        # Crear hash de originales para auditoría
        hash_original = hashlib.sha256(pii_text.encode()).hexdigest()
        
        return {
            "anonimizado": anonimizado.text,
            "entidades_detectadas": entidades_detectadas,
            "hash_original": hash_original
        }
```

### `services/predictor.py`
```python
import pickle
from ml.classifier import UrgencyPredictor

class ModelPredictor:
    def __init__(self, model_path: str, vectorizer_path: str):
        with open(model_path, 'rb') as f:
            self.model = pickle.load(f)
        with open(vectorizer_path, 'rb') as f:
            self.vectorizer = pickle.load(f)
    
    def predict(self, descripcion: str, categoria: str) -> dict:
        """
        Input: descripción + categoría
        Output: {urgencia_predicha: float, confianza: float}
        """
        # Vectorizar descripción
        X = self.vectorizer.transform([descripcion])
        
        # Predecir urgencia
        urgencia = self.model.predict(X)[0]
        
        # Calcular confianza (promedio de probabilidades de árboles)
        confianza = self.model.predict_proba(X).max()
        
        return {
            "urgencia_predicha": int(round(urgencia)),
            "confianza": float(confianza)
        }
```

### `services/retrainer.py`
```python
from ml.trainer import train_urgency_predictor
from database import SessionLocal
from models import Ticket, Validacion, ModeloMetadata
import threading
import logging

logger = logging.getLogger(__name__)

class Retrainer:
    def __init__(self):
        self.lock = threading.Lock()
        self.is_retraining = False
    
    def check_and_trigger_retrain(self):
        """Llamado desde POST /api/validate"""
        db = SessionLocal()
        
        # Contar validaciones no procesadas
        unprocessed = db.query(Validacion).filter(
            Validacion.procesado == False
        ).count()
        
        if unprocessed >= 50:
            # Trigger reentrenamiento síncrono
            try:
                self.retrain_sync()
            except Exception as e:
                logger.error(f"Retrain failed: {e}")
        
        db.close()
    
    def retrain_sync(self):
        """Reentrenamiento síncrono (el cliente espera)"""
        if not self.lock.acquire(blocking=False):
            logger.warning("Reentrenamiento ya en progreso")
            return None
        
        try:
            self.is_retraining = True
            db = SessionLocal()
            
            # 1. Cargar datos
            tickets = db.query(Ticket).all()
            validaciones = db.query(Validacion).filter(
                Validacion.procesado == False
            ).all()
            
            X, y = self._prepare_data(tickets, validaciones)
            
            # 2. Entrenar
            new_model, new_vectorizer, metrics = train_urgency_predictor(X, y)
            
            # 3. Evaluar vs modelo actual
            old_metrics = db.query(ModeloMetadata).filter(
                ModeloMetadata.activo == True
            ).first()
            
            old_mse = old_metrics.mse if old_metrics else float('inf')
            new_mse = metrics['mse']
            
            # 4. Decidir
            if new_mse < old_mse * 1.05:
                # Activar nuevo modelo
                import pickle
                with open('/app/models/classifier_v1.1.pkl', 'wb') as f:
                    pickle.dump(new_model, f)
                with open('/app/models/vectorizer_v1.1.pkl', 'wb') as f:
                    pickle.dump(new_vectorizer, f)
                
                # Registrar en metadata
                old_model = db.query(ModeloMetadata).filter(
                    ModeloMetadata.activo == True
                ).first()
                old_model.activo = False
                
                new_meta = ModeloMetadata(
                    version='v1.1',
                    fecha_entrenamiento=datetime.now(),
                    datos_utilizados=len(X),
                    mse=new_mse,
                    r2=metrics['r2'],
                    activo=True,
                    backup_anterior='v1.0'
                )
                db.add(new_meta)
                
                # Marcar validaciones como procesadas
                for val in validaciones:
                    val.procesado = True
                
                db.commit()
                
                return {
                    "status": "success",
                    "version": "v1.1",
                    "mse": new_mse,
                    "r2": metrics['r2']
                }
            else:
                logger.warning(f"MSE no mejoró: {new_mse} vs {old_mse}")
                return {
                    "status": "failed",
                    "razon": "MSE no mejoró"
                }
        
        finally:
            self.is_retraining = False
            self.lock.release()
            db.close()
```

### `api/tickets.py`
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.anonymizer import DataAnonimizer
from services.predictor import ModelPredictor
from database import SessionLocal
from models import Ticket, Prediccion

router = APIRouter()
anonymizer = DataAnonimizer()
predictor = ModelPredictor('/app/models/classifier.pkl', '/app/models/vectorizer.pkl')

class TicketCreate(BaseModel):
    nombre: str
    apellidos: str
    nif: str
    telefono: str
    email: str
    categoria: str
    descripcion: str
    canal: str
    direccion_persona: str
    ubicacion_incidencia: dict  # {"lat": ..., "lon": ...}

@router.post("")
def create_ticket(ticket: TicketCreate):
    db = SessionLocal()
    
    try:
        # Anonimizar
        anon_result = anonymizer.anonymize_ticket(ticket.dict())
        
        # Predecir urgencia
        pred_result = predictor.predict(ticket.descripcion, ticket.categoria)
        
        # Guardar en BD
        new_ticket = Ticket(
            descripcion=ticket.descripcion,
            categoria=ticket.categoria,
            canal=ticket.canal,
            urgencia_predicha=pred_result['urgencia_predicha'],
            persona_anonimizado=anon_result['anonimizado'],
            anonimizacion_hash=anon_result['hash_original'],
            ubicacion_incidencia=f"POINT({ticket.ubicacion_incidencia['lon']} {ticket.ubicacion_incidencia['lat']})",
            ubicacion_descripcion=ticket.ubicacion_incidencia.get('descripcion', '')
        )
        db.add(new_ticket)
        db.flush()
        
        # Registrar predicción
        pred = Prediccion(
            ticket_id=new_ticket.id,
            urgencia_predicha=pred_result['urgencia_predicha'],
            confianza=pred_result['confianza'],
            modelo_version='v1.0'
        )
        db.add(pred)
        db.commit()
        
        return {
            "ticket_id": new_ticket.id,
            "urgencia_predicha": pred_result['urgencia_predicha'],
            "confianza": pred_result['confianza']
        }
    
    finally:
        db.close()
```

---

## 3. ML: RandomForest Pipeline

### `ml/classifier.py`
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
import numpy as np

class UrgencyPredictor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
            min_df=2,
            max_df=0.8,
            lowercase=True,
            strip_accents='unicode'
        )
        
        self.categoria_encoder = LabelEncoder()
        
        self.model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
    
    def train(self, descriptions, categories, urgencies):
        """
        descriptions: list[str]
        categories: list[str]
        urgencies: list[int]
        """
        # Vectorizar descripciones
        X_desc = self.vectorizer.fit_transform(descriptions)
        
        # Encode categorías
        categories_encoded = self.categoria_encoder.fit_transform(categories)
        categories_onehot = np.eye(len(self.categoria_encoder.classes_))[categories_encoded]
        
        # Concatenar features
        X = np.hstack([X_desc.toarray(), categories_onehot])
        
        # Entrenar
        self.model.fit(X, urgencies)
        
        return self
    
    def predict(self, description, category):
        """
        Predict urgency for single instance
        """
        X_desc = self.vectorizer.transform([description]).toarray()
        cat_encoded = self.categoria_encoder.transform([category])
        cat_onehot = np.eye(len(self.categoria_encoder.classes_))[cat_encoded]
        
        X = np.hstack([X_desc, cat_onehot])
        
        urgencia = self.model.predict(X)[0]
        confianza = 1.0 / (1.0 + np.std(
            [tree.predict(X)[0] for tree in self.model.estimators_]
        ))
        
        return {
            "urgencia": urgencia,
            "confianza": confianza
        }
```

---

## 4. Frontend: Componentes Clave

### `pages/Dashboard.jsx`
```jsx
import { useState, useEffect } from 'react'
import { useTickets } from '../hooks/useTickets'
import TicketTable from '../components/TicketTable'
import FilterPanel from '../components/FilterPanel'

export default function Dashboard() {
  const { tickets, loading, fetchTickets } = useTickets()
  const [filters, setFilters] = useState({})
  const [page, setPage] = useState(0)

  useEffect(() => {
    fetchTickets({ ...filters, limit: 20, offset: page * 20 })
  }, [filters, page])

  return (
    <div className="dashboard">
      <h1>CiudadAI - Triaje de Solicitudes</h1>
      
      <FilterPanel onFiltersChange={setFilters} />
      
      {loading ? (
        <p>Cargando...</p>
      ) : (
        <>
          <TicketTable tickets={tickets} />
          <div className="pagination">
            <button onClick={() => setPage(Math.max(0, page - 1))}>← Anterior</button>
            <span>Página {page + 1}</span>
            <button onClick={() => setPage(page + 1)}>Siguiente →</button>
          </div>
        </>
      )}
    </div>
  )
}
```

### `pages/TicketDetail.jsx`
```jsx
import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { fetchTicketDetail, submitValidation } from '../services/api'

export default function TicketDetail() {
  const { id } = useParams()
  const [ticket, setTicket] = useState(null)
  const [urgencyReal, setUrgencyReal] = useState(3)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [retraining, setRetraining] = useState(false)

  useEffect(() => {
    fetchTicketDetail(id).then(data => {
      setTicket(data)
      setLoading(false)
    })
  }, [id])

  const handleValidate = async () => {
    setSaving(true)
    const result = await submitValidation(
      parseInt(id),
      urgencyReal,
      "Validación manual del admin"
    )
    
    if (result.reentrenamiento_queued) {
      setRetraining(true)
      setTimeout(() => setRetraining(false), 3000)
    }
    
    setSaving(false)
  }

  if (loading) return <p>Cargando...</p>
  if (!ticket) return <p>Ticket no encontrado</p>

  return (
    <div className="ticket-detail">
      <h2>Ticket #{ticket.id}</h2>
      
      <section className="ticket-info">
        <p><strong>Descripción:</strong> {ticket.descripcion}</p>
        <p><strong>Categoría:</strong> {ticket.categoria}</p>
        <p><strong>Urgencia predicha:</strong> {ticket.urgencia_predicha}/5 (confianza: {(ticket.confianza * 100).toFixed(0)}%)</p>
      </section>
      
      <section className="validation">
        <h3>Validar Urgencia</h3>
        <input
          type="range"
          min="1"
          max="5"
          value={urgencyReal}
          onChange={(e) => setUrgencyReal(parseInt(e.target.value))}
        />
        <span>Urgencia real: {urgencyReal}</span>
        
        <button onClick={handleValidate} disabled={saving}>
          {saving ? 'Guardando...' : 'Guardar Validación'}
        </button>
        
        {retraining && (
          <div className="notification success">
            ✅ Reentrenamiento iniciado
          </div>
        )}
      </section>
    </div>
  )
}
```

---

## 5. Testing: Casos Clave

### Backend: `test_api.py`
```python
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_post_tickets_creates_entry():
    response = client.post("/api/tickets", json={
        "nombre": "Test",
        "apellidos": "User",
        "nif": "12345678A",
        "telefono": "612345678",
        "email": "test@test.com",
        "categoria": "Limpieza",
        "descripcion": "Prueba de basura",
        "canal": "Web",
        "direccion_persona": "Calle Test 1",
        "ubicacion_incidencia": {"lat": 40.4, "lon": -3.7}
    })
    assert response.status_code == 200
    assert "ticket_id" in response.json()
    assert "urgencia_predicha" in response.json()

def test_post_validate_increments_counter():
    # Crear ticket
    ticket_response = client.post("/api/tickets", json={...})
    ticket_id = ticket_response.json()["ticket_id"]
    
    # Validar
    val_response = client.post("/api/validate", json={
        "ticket_id": ticket_id,
        "urgencia_real": 4,
        "usuario_id": "admin@test.com"
    })
    assert val_response.status_code == 200
```

---

## 6. Variables de Entorno (.env)

```env
# Database
DATABASE_URL=postgresql://ciudadai:ciudadai_pwd@db:5432/ciudadai_db
DB_USER=ciudadai
DB_PASSWORD=ciudadai_pwd

# API
ALLOWED_ORIGINS=http://localhost:5173
API_HOST=0.0.0.0
API_PORT=8000

# ML
MODEL_PATH=/app/models/classifier.pkl
VECTORIZER_PATH=/app/models/vectorizer.pkl

# Presidio
PRESIDIO_ENABLED=true

# Logging
LOG_LEVEL=INFO
```

---

## 7. Performance & Scalability

| Operación | Tiempo esperado |
|-----------|-----------------|
| POST /api/tickets | 200-500ms (anonimización + predicción) |
| GET /api/tickets (20 items) | 50-100ms |
| POST /api/validate | 10-50ms |
| POST /api/retrain | 10-30s (síncrono) |

**Bottlenecks:**
- Presidio: lento para batch. Solución: caché o async.
- Reentrenamiento: síncrono. Solución: move to background job (Celery).
- DB queries: agregar índices según patrones de acceso.

---

**Documento actualizado:** 2026-01-21
