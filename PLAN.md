# PLAN: CiudadAI – De MVP a Plataforma de Triaje Inteligente con Active Learning

**Estado:** ✅ Plan Confirmado - Listo para implementar
**Equipo:** 5 personas × 52 horas = 260 horas-persona
**Fecha plan:** 2026-01-21

---

## 0. Resumen Ejecutivo

CiudadAI es una plataforma web que **automatiza el triaje de solicitudes ciudadanas** mediante:

1. **Privacidad por diseño:** Anonimización local (Presidio) de datos sensibles. Los datos originales NUNCA se guardan.
2. **IA adaptativa:** Modelo RandomForest que predice urgencia (1-5) basado en descripción + categoría.
3. **Active Learning:** Admin valida predicciones → Sistema rereentrena cada 50 validaciones de forma síncrona.
4. **Auditoría completa:** Log de anonimización y versionamiento de modelos.

---

## 1. DECISIONES FINALES CONFIRMADAS ✅

| Aspecto | Decisión |
|---------|----------|
| **Arquitectura** | Backend FastAPI + Frontend React + PostgreSQL en Docker |
| **Modelo ML** | RandomForest regresor. Input: (descripción, categoría) → Output: urgencia (1-5) |
| **Active Learning** | Admin valida SOLO urgencia. Reentrenamiento automático cada 50 validaciones |
| **Reentrenamiento** | Síncrono (10-30s espera) + Full dataset (original + validaciones) + Swap automático |
| **Privacidad** | Solo datos anonimizados en BD. Originales NUNCA se guardan. Hash para auditoría |
| **Dataset** | ~1000 tickets sintéticos generados al inicio (Faker). Nunca se regeneran |
| **Versionamiento** | Última versión activa + backup anterior (rollback si es necesario) |
| **Datos para reentrenamiento** | Dataset original (1000) + Validaciones nuevas (50) = 1050 total |

---

## 2. FASE 1: Arquitectura & DevOps (6 horas/persona = 30 horas totales)

### 2.1 Schema PostgreSQL

```sql
-- Tabla principal: tickets anonimizados
CREATE TABLE tickets (
    id SERIAL PRIMARY KEY,
    descripcion TEXT NOT NULL,
    categoria VARCHAR(50) NOT NULL, 
    urgencia_predicha INT,
    urgencia_real INT, -- solo durante entrenamiento
    canal VARCHAR(10) NOT NULL, -- Web, App
    ubicacion_incidencia TEXT, -- GPS
    ubicacion_descripcion TEXT,
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP DEFAULT NOW(),
    
    -- Campos anonimizados (nunca originales)
    persona_anonimizado VARCHAR(50),
    apellidos_anonimizado VARCHAR(50),
    nif_anonimizado VARCHAR(50),
    telefono_anonimizado VARCHAR(50),
    email_anonimizado VARCHAR(50),
    direccion_anonimizado VARCHAR(255),
    
    -- Metadata
    anonimizacion_hash VARCHAR(64), -- SHA256 para auditoría
    modelo_version VARCHAR(20) DEFAULT 'v1.0'
);

-- Histórico de predicciones
CREATE TABLE predicciones (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id),
    urgencia_predicha INT NOT NULL,
    confianza FLOAT NOT NULL,
    modelo_version VARCHAR(20) NOT NULL,
    fecha_prediccion TIMESTAMP DEFAULT NOW()
);

-- Active Learning: validaciones del admin
CREATE TABLE validaciones (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id),
    urgencia_real INT NOT NULL,
    usuario_id VARCHAR(50),
    notas TEXT,
    procesado BOOLEAN DEFAULT FALSE,
    fecha_validacion TIMESTAMP DEFAULT NOW()
);

-- Auditoría: qué entidades PII se detectaron
CREATE TABLE anonimizacion_log (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id),
    entidades_detectadas JSONB,
    campos_anonimizados JSONB,
    fecha_anonimizacion TIMESTAMP DEFAULT NOW()
);

-- Versionamiento de modelos
CREATE TABLE modelo_metadata (
    id SERIAL PRIMARY KEY,
    version VARCHAR(20) UNIQUE NOT NULL,
    fecha_entrenamiento TIMESTAMP NOT NULL,
    datos_utilizados INT NOT NULL,
    accuracy FLOAT,
    mse FLOAT,
    activo BOOLEAN DEFAULT FALSE,
    backup_anterior VARCHAR(20),
    fecha_creacion TIMESTAMP DEFAULT NOW()
);
```

### 2.2 Docker Compose actualizado

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ciudadai
      POSTGRES_PASSWORD: ciudadai_secure_pwd
      POSTGRES_DB: ciudadai_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - ciudadai-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ciudadai"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://ciudadai:ciudadai_secure_pwd@db:5432/ciudadai_db
      PRESIDIO_ENABLED: "true"
      MODEL_PATH: /app/models/classifier.pkl
      VECTORIZER_PATH: /app/models/vectorizer.pkl
      ALLOWED_ORIGINS: "http://localhost:5173"
    volumes:
      - ./backend/models:/app/models
    networks:
      - ciudadai-net

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    depends_on:
      - backend
    networks:
      - ciudadai-net

volumes:
  postgres_data:

networks:
  ciudadai-net:
    driver: bridge
```

### 2.3 Estructura del Backend

```
backend/
├── main.py (FastAPI app + rutas principales)
├── config.py (variables de entorno)
├── database.py (SQLAlchemy session)
├── models.py (ORM: Ticket, Prediccion, Validacion, etc)
├── requirements.txt (fastapi, psycopg2, presidio, scikit-learn, etc)
├── Dockerfile
│
├── api/
│   ├── tickets.py (POST /api/tickets, GET /api/tickets/{id})
│   ├── validations.py (POST /api/validate)
│   ├── stats.py (GET /api/stats)
│   └── retrain.py (POST /api/retrain)
│
├── services/
│   ├── anonymizer.py (Presidio PII detection + replacement)
│   ├── predictor.py (cargar modelo + predict urgencia)
│   └── retrainer.py (lógica reentrenamiento)
│
├── ml/
│   ├── classifier.py (RandomForest pipeline)
│   ├── features.py (TF-IDF vectorizer)
│   └── trainer.py (train + serialize)
│
├── scripts/
│   ├── generate_dataset.py (Faker → CSV → PostgreSQL)
│   ├── train_initial_model.py (training v1.0)
│   └── check_retrain_threshold.py (monitorear contador)
│
├── tests/
│   ├── test_anonymizer.py
│   ├── test_model.py
│   ├── test_api.py
│   └── test_retrain.py
│
├── sql/
│   └── init.sql (schema + sample inserts)
│
├── models/ (runtime)
│   ├── classifier.pkl
│   └── vectorizer.pkl
│
└── alembic/ (migrations)
    ├── versions/
    └── env.py
```

---

## 3. FASE 2: Data & NLP (14 horas/persona = 70 horas totales)

### 3.1 Dataset Sintético: `generate_dataset.py`

**Input esperado (CSV pre-anonimización):**
```
nombre,apellidos,nif,telefono,email,categoria,descripcion,urgencia,canal,fecha,direccion_persona,ubicacion_incidencia_lat,ubicacion_incidencia_lon,ubicacion_descripcion

Juan,Martínez Ruiz,12345678A,612345678,juan.martinez@gmail.com,Limpieza,"Basura acumulada frente a la escuela",3,Web,2026-01-15T10:30:00Z,"Calle Principal 42 3B 28001",40.4168,-3.7038,"Frente portal 12"
```

**Lógica:**
1. Faker genera ~1000 registros con datos realistas españoles
2. Asigna categorías: [Limpieza, Alumbrado Público, Movilidad, Parques y Jardines, Mobiliario Urbano]
3. Urgencias reales (1-5) aleatorias
4. Descripciones realistas en español (con typos intencionales)
5. Inserta en PostgreSQL directamente
6. Anonimiza usando Presidio
7. Guarda en tabla `tickets` (datos originales NUNCA se guardan)

### 3.2 Anonimización: `anonymizer.py`

**Presidio detecta y reemplaza:**
- `nombre`, `apellidos` → `<PERSON>`
- `nif` → `<ID_NUMBER>`
- `telefono` → `<PHONE_NUMBER>`
- `email` → `<EMAIL_ADDRESS>`
- `direccion_persona` → `<LOCATION>`

**Output:**
```python
{
    "anonimizado": {
        "persona": "<PERSON>",
        "email": "<EMAIL_ADDRESS>",
        "nif": "<ID_NUMBER>",
        "telefono": "<PHONE_NUMBER>",
        "direccion": "<LOCATION>"
    },
    "entidades_detectadas": {
        "PERSON": 2,
        "PHONE": 1,
        "EMAIL": 1,
        "ID_NUMBER": 1,
        "LOCATION": 1
    },
    "hash_original": "sha256_hash_for_audit"
}
```

**Crítico:** Los datos originales se descartan inmediatamente. Solo se guardan:
- Datos anonimizados (en tabla `tickets`)
- Hash (para auditoría RGPD)
- Entidades detectadas (log)

### 3.3 Modelo ML: RandomForest Urgency Predictor

**Pipeline:**
```
Input: (descripción_ticket, categoría) 
  ↓
TF-IDF Vectorizer (descripción) → 1000 features
  ↓
Concatenate category one-hot encoding
  ↓
RandomForestRegressor (n_estimators=100)
  ↓
Output: urgencia predicha (float 1-5), confianza (float 0-1)
```

**Entrenamiento:**
- Dataset: 1000 tickets originales
- Target: `urgencia_real` (1-5)
- Split: 80% train, 20% test
- Evaluar: MSE, MAE, R²
- Serializar: `models/classifier.pkl` + `models/vectorizer.pkl`

**Reentrenamiento (Active Learning):**
- Datos: dataset original (1000) + validaciones nuevas (50)
- Nuevo split: 80/20 sobre 1050 datos
- Umbral calidad: `nuevo_mse < old_mse * 1.05` (tolera 5% degradación)
- Si pasa: activar nuevo modelo. Si no: rollback

---

## 4. FASE 3: Backend (14 horas/persona = 70 horas totales)

### 4.1 API Endpoints

#### POST `/api/tickets` – Crear ticket
```json
Entrada:
{
  "nombre": "Juan",
  "apellidos": "Martínez Ruiz",
  "nif": "12345678A",
  "telefono": "612345678",
  "email": "juan@gmail.com",
  "categoria": "Limpieza",
  "descripcion": "Basura acumulada frente escuela",
  "canal": "Web",
  "direccion_persona": "Calle Principal 42 3B",
  "ubicacion_incidencia": {
    "lat": 40.4168,
    "lon": -3.7038,
    "descripcion": "Frente portal 12"
  }
}

Proceso:
1. Anonimizar localmente (Presidio) - datos originales se descartan
2. Cargar modelo activo
3. Predecir urgencia: predict(descripción, categoría)
4. Guardar en BD (solo datos anonimizados + predicción + confianza)
5. Registrar en anonimizacion_log
6. Registrar en predicciones
7. Chequear: ¿contador de validaciones no procesadas >= 50?
   - Si sí: trigger POST /api/retrain (pero cliente no espera, responde inmediatamente)

Salida (200 OK):
{
  "ticket_id": 1,
  "categoria": "Limpieza",
  "urgencia_predicha": 3,
  "confianza": 0.78,
  "modelo_version": "v1.0",
  "estado": "created"
}
```

#### GET `/api/tickets` – Listar tickets (paginado)
```
Query params:
  ?categoria=Limpieza
  ?urgencia_min=3
  &validado=false (solo pendientes)
  &limit=20
  &offset=0

Retorna: Array de tickets (datos anonimizados, sin originales)
{
  "tickets": [
    {
      "id": 1,
      "descripcion": "Basura acumulada...",
      "categoria": "Limpieza",
      "urgencia_predicha": 3,
      "confianza": 0.78,
      "estado": "pending_validation",
      "fecha_creacion": "2026-01-15T10:30:00Z"
    }
  ],
  "total": 1050,
  "pendientes_validacion": 8
}
```

#### GET `/api/tickets/{id}` – Detalle ticket
```json
Retorna:
{
  "id": 1,
  "descripcion": "Basura acumulada frente a la escuela",
  "categoria": "Limpieza",
  "urgencia_predicha": 3,
  "confianza": 0.78,
  "persona_anonimizado": "<PERSON>",
  "email_anonimizado": "<EMAIL_ADDRESS>",
  "telefono_anonimizado": "<PHONE_NUMBER>",
  "ubicacion_incidencia": {
    "lat": 40.4168,
    "lon": -3.7038,
    "descripcion": "Frente portal 12"
  },
  "estado": "pending_validation",
  "fecha_creacion": "2026-01-15T10:30:00Z",
  "modelo_version": "v1.0"
}
```

#### POST `/api/validate` – Validar urgencia (Active Learning)
```json
Entrada:
{
  "ticket_id": 1,
  "urgencia_real": 4,
  "usuario_id": "admin@ayuntamiento.es",
  "notas": "Es más urgente por proximidad a escuela"
}

Proceso:
1. Guardar en tabla validaciones (procesado=false)
2. Incrementar contador validaciones no procesadas
3. Si contador == 50 → registrar que debe reentrenarse (pero no bloquear respuesta)
4. Retornar inmediatamente

Salida (200 OK - caso normal):
{
  "validacion_id": 42,
  "ticket_id": 1,
  "status": "registered",
  "reentrenamiento_queued": false
}

Salida (200 OK - caso 50 validaciones):
{
  "validacion_id": 43,
  "ticket_id": 2,
  "status": "registered",
  "reentrenamiento_queued": true,
  "mensaje": "Se iniciará reentrenamiento en background"
}
```

#### POST `/api/retrain` – Reentrenamiento (SÍNCRONO)
```
Este endpoint puede ser:
A) Llamado automáticamente cuando se alcanza contador == 50
B) Llamado manualmente por el admin: POST /api/retrain?force=true

Proceso (SÍNCRONO - el cliente ESPERA respuesta):
1. Lock: Asegurar que solo un reentrenamiento ocurre simultáneamente
2. Cargar datos:
   - Dataset original: 1000 tickets
   - Validaciones nuevas: 50 tickets (procesado=false)
   - Total: 1050 para entrenar
3. Entrenar nuevo RandomForest
4. Evaluar en test set (20%)
5. Calcular MSE nuevo vs MSE anterior
6. Decision:
   - Si mse_nuevo < mse_anterior * 1.05: ACTIVAR
   - Else: RECHAZAR (rollback)
7. Si activar:
   - Serializar nuevo modelo → models/classifier_v1.1.pkl
   - Crear entrada en modelo_metadata (v1.1, activo=true)
   - Marcar v1.0 como backup
   - Marcar validaciones como procesado=true
   - Resetear contador
8. Si rechazar:
   - Registrar error en logs
   - Mantener v1.0 como activo

Salida (200 OK - éxito):
{
  "status": "success",
  "nueva_version": "v1.1",
  "metricas": {
    "mse_anterior": 0.40,
    "mse_nuevo": 0.38,
    "r2": 0.85
  },
  "tickets_utilizados": 1050,
  "tickets_nuevos_validados": 50,
  "backup": "v1.0"
}

Salida (200 OK - rechazado):
{
  "status": "failed_quality_check",
  "razon": "MSE no mejoró",
  "mse_anterior": 0.40,
  "mse_nuevo": 0.45,
  "modelo_activo_mantenido": "v1.0"
}

Salida (500 - error):
{
  "status": "error",
  "mensaje": "Error durante entrenamiento: ...",
  "modelo_activo": "v1.0"
}
```

**Timeout:** 60 segundos máximo. Si excede, responder con error.

#### GET `/api/stats` – Estadísticas dashboard
```json
Retorna:
{
  "total_tickets": 1050,
  "pendientes_validacion": 8,
  "por_categoria": {
    "Limpieza": 210,
    "Alumbrado": 180,
    "Movilidad": 250,
    "Parques": 200,
    "Mobiliario": 210
  },
  "urgencia_promedio_predicha": 2.8,
  "confianza_promedio": 0.76,
  "validaciones_acumuladas": 42,
  "validaciones_para_reentrenamiento": 50,
  "modelo_activo": "v1.0",
  "modelo_backup": "v1.0",
  "ultima_prediccion": "2026-01-15T14:22:33Z",
  "ultimo_reentrenamiento": "2026-01-10T09:15:00Z"
}
```

### 4.2 Persistencia: SQLAlchemy ORM

```python
# backend/models.py

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, JSONB, Point
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Ticket(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True)
    descripcion = Column(Text)
    categoria = Column(String)
    urgencia_predicha = Column(Integer, nullable=True)
    urgencia_real = Column(Integer, nullable=True)
    canal = Column(String)
    ubicacion_incidencia = Column(Point)
    ubicacion_descripcion = Column(String)
    
    # Anonimizados
    persona_anonimizado = Column(String)
    nif_anonimizado = Column(String)
    email_anonimizado = Column(String)
    
    # Metadata
    anonimizacion_hash = Column(String)
    modelo_version = Column(String, default='v1.0')
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow)

class Prediccion(Base):
    __tablename__ = "predicciones"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    urgencia_predicha = Column(Integer)
    confianza = Column(Float)
    modelo_version = Column(String)
    fecha_prediccion = Column(DateTime, default=datetime.utcnow)

class Validacion(Base):
    __tablename__ = "validaciones"
    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey('tickets.id'))
    urgencia_real = Column(Integer)
    usuario_id = Column(String)
    notas = Column(Text, nullable=True)
    procesado = Column(Boolean, default=False)
    fecha_validacion = Column(DateTime, default=datetime.utcnow)

class ModeloMetadata(Base):
    __tablename__ = "modelo_metadata"
    id = Column(Integer, primary_key=True)
    version = Column(String, unique=True)
    fecha_entrenamiento = Column(DateTime)
    datos_utilizados = Column(Integer)
    mse = Column(Float, nullable=True)
    activo = Column(Boolean, default=False)
    backup_anterior = Column(String, nullable=True)
    fecha_creacion = Column(DateTime, default=datetime.utcnow)
```

### 4.3 Migrations (Alembic)

```bash
# Crear migrations automáticas
alembic revision --autogenerate -m "initial schema"

# Aplicar
alembic upgrade head
```

---

## 5. FASE 4: Frontend (12 horas/persona = 60 horas totales)

### 5.1 Router & Layout

**App.jsx**
```jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import TicketDetail from './pages/TicketDetail'
import Stats from './pages/Stats'

export default function App() {
  return (
    <BrowserRouter>
      <nav>
        <a href="/">Dashboard</a>
        <a href="/stats">Estadísticas</a>
      </nav>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/ticket/:id" element={<TicketDetail />} />
        <Route path="/stats" element={<Stats />} />
      </Routes>
    </BrowserRouter>
  )
}
```

### 5.2 Componentes Principales

**Dashboard.jsx**
- Tabla de tickets con columnas: ID | Categoría | Urgencia | Confianza | Estado | Acciones
- Filtros: Categoría, Urgencia mínima, "Solo pendientes"
- Paginación: 20 tickets por página
- Card de información: "42 pendientes de validación"

**TicketDetail.jsx**
- Descripción del ticket
- Urgencia predicha (barra 1-5)
- Confianza (%)
- Selector de urgencia real (1-5)
- Botón "Guardar validación"
- Notificación si reentrenamiento se inició

**Stats.jsx**
- KPIs: Total, Pendientes, Confianza promedio, Modelo activo
- Gráficas: Tickets por categoría, Urgencia promedio, Evolución modelo
- Tabla: Historial reentrenamientos (versión, fecha, MSE, estado)

### 5.3 API Service

```javascript
// frontend/src/services/api.js

const API_URL = '/api'

export const fetchTickets = (filters) => {
  const params = new URLSearchParams(filters || {})
  return fetch(`${API_URL}/tickets?${params}`).then(r => r.json())
}

export const fetchTicketDetail = (id) =>
  fetch(`${API_URL}/tickets/${id}`).then(r => r.json())

export const submitValidation = (ticketId, urgencyReal, notas) =>
  fetch(`${API_URL}/validate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ticket_id: ticketId,
      urgencia_real: urgencyReal,
      notas: notas
    })
  }).then(r => r.json())

export const fetchStats = () =>
  fetch(`${API_URL}/stats`).then(r => r.json())
```

---

## 6. FASE 5: Integración & QA (6 horas/persona = 30 horas totales)

### 6.1 Test Suite

**Backend (pytest)**
```
backend/tests/
├── test_anonymizer.py
│   ├── test_detect_person_names()
│   ├── test_detect_phone()
│   ├── test_detect_email()
│   └── test_anonymized_data_never_contains_originals()
│
├── test_model.py
│   ├── test_train_urgency_predictor()
│   ├── test_predict_returns_valid_urgency()
│   ├── test_model_serialization()
│   └── test_retrainer_quality_check()
│
├── test_api.py
│   ├── test_post_tickets_creates_entry()
│   ├── test_post_tickets_anonimizes_data()
│   ├── test_post_validate_increments_counter()
│   ├── test_retrain_triggered_at_50_validations()
│   └── test_get_stats_returns_correct_counts()
│
└── test_integration.py
    ├── test_full_flow_ticket_to_validation()
    └── test_reentrenamiento_workflow()
```

**Frontend (Vitest)**
```
frontend/tests/
├── Dashboard.test.jsx
│   ├── test_renders_ticket_table()
│   ├── test_filter_by_category()
│   └── test_pagination_works()
│
├── TicketDetail.test.jsx
│   ├── test_loads_ticket_data()
│   ├── test_validate_button_sends_request()
│   └── test_retraining_notification_appears()
│
└── Stats.test.jsx
    └── test_stats_display_correct_counts()
```

### 6.2 CI/CD: GitHub Actions

```yaml
# .github/workflows/test-and-deploy.yml
name: CiudadAI Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_PASSWORD: test
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
      - name: Run backend tests
        run: |
          cd backend
          pytest tests/

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      - name: Install & build frontend
        run: |
          cd frontend
          npm install
          npm run build
      - name: Run frontend tests
        run: |
          cd frontend
          npm run test
```

### 6.3 Checklist Pre-Deploy

- [ ] `docker-compose up --build` levanta sin errores
- [ ] PostgreSQL inicializada con schema
- [ ] Dataset sintético (~1000 tickets) cargado
- [ ] Modelo v1.0 entrenado y serializado
- [ ] Frontend carga en http://localhost:5173
- [ ] POST /api/tickets crea ticket anonimizado
- [ ] GET /api/tickets lista tickets
- [ ] POST /api/validate guarda validación
- [ ] 50 validaciones triggerean reentrenamiento
- [ ] Tests backend pasan
- [ ] Tests frontend pasan
- [ ] CI/CD pasa en GitHub
- [ ] README.md actualizado con instrucciones

---

## 7. Timeline por Persona

| Persona | Rol | Semana 1 | Semana 2 |
|---------|-----|----------|----------|
| 1 | DevOps/Data | Schema PostgreSQL (2h) + Docker Compose (2h) + init.sql (2h) | Dataset generator (4h) + Anonimización testing (2h) |
| 2 | ML Engineer | Design features (3h) + RandomForest pipeline (3h) | Training script (4h) + Testing modelo (2h) |
| 3 | Backend Dev | ORM setup (4h) + Presidio integration (2h) | API endpoints (5h) + Retrain logic (3h) |
| 4 | Frontend Dev | Router + layout (4h) | Dashboard (5h) + Detail page + Stats (3h) |
| 5 | QA/DevOps | CI/CD setup (2h) + Test infrastructure (3h) | Integration tests (3h) + Docs (2h) |

---

## 8. Requisitos Previos

- Python 3.11+
- Node.js 20+
- Docker & Docker Compose
- PostgreSQL 15
- pip, npm

---

## 9. Próximos Pasos

1. ✅ Plan confirmado
2. ⏳ Implementar Fase 1: Setup DevOps + BD
3. ⏳ Implementar Fase 2: Dataset + Anonimización + Modelo
4. ⏳ Implementar Fase 3: Backend API
5. ⏳ Implementar Fase 4: Frontend
6. ⏳ Implementar Fase 5: QA + Integración
7. ⏳ Deploy en producción

---

**Documento creado:** 2026-01-21
**Estado:** ✅ LISTO PARA IMPLEMENTAR
