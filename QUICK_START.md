# CiudadAI – Quick Start Guide

## 📋 Resumen del Proyecto

**CiudadAI** es una plataforma inteligente de triaje de solicitudes ciudadanas que:
- ✅ Anonimiza datos sensibles automáticamente (Presidio)
- ✅ Predice urgencia (1-5) con RandomForest + TF-IDF
- ✅ Implementa Active Learning: admin valida → reentrenamiento cada 50 validaciones
- ✅ Mantiene auditoría completa (logs, versionamiento, rollback)

---

## 🏗️ Arquitectura

```
Frontend (React/Vite)          Backend (FastAPI)           Database (PostgreSQL)
   http://localhost:5173    →    http://localhost:8000   →    localhost:5432
        Dashboard                 API REST + ML                Datos anonimizados
        Validación urgencia       Anonimización (Presidio)    + Modelo metadata
        Estadísticas             Modelo RandomForest         + Logs auditoría
                                 Active Learning
```

---

## 📦 Stack Tecnológico

| Componente | Tecnología | Versión |
|-----------|-----------|---------|
| Backend | FastAPI + Python | 3.11 |
| Frontend | React + Vite | Node 20 |
| Database | PostgreSQL | 15 |
| ML | scikit-learn (RandomForest) | - |
| Privacidad | Microsoft Presidio | - |
| DevOps | Docker Compose | - |
| CI/CD | GitHub Actions | - |

---

## 🚀 Arranque Rápido (Dev)

### 1. Clonar y preparar
```bash
cd ciudadai-mvp
docker-compose up --build
```

### 2. Acceder
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Workflows principales

**A) Crear ticket (admin/usuario)**
```bash
curl -X POST http://localhost:8000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "apellidos": "Martínez",
    "nif": "12345678A",
    "telefono": "612345678",
    "email": "juan@email.com",
    "categoria": "Limpieza",
    "descripcion": "Basura acumulada frente escuela",
    "canal": "Web",
    "direccion_persona": "Calle Principal 42",
    "ubicacion_incidencia": {"lat": 40.4, "lon": -3.7, "descripcion": "Frente portal 12"}
  }'
```

**B) Validar urgencia (admin)**
```bash
curl -X POST http://localhost:8000/api/validate \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": 1,
    "urgencia_real": 4,
    "usuario_id": "admin@ayuntamiento.es",
    "notas": "Más urgente por proximidad a escuela"
  }'
```

**C) Listar tickets**
```bash
curl http://localhost:8000/api/tickets?categoria=Limpieza&limit=10
```

**D) Ver estadísticas**
```bash
curl http://localhost:8000/api/stats
```

---

## 🔄 Flujo Active Learning

```
1. Admin crea ticket en UI
   ↓
2. Sistema anonimiza + predice urgencia
   ↓
3. Admin valida urgencia (acepta/corrige/rechaza)
   ↓
4. Sistema registra validación
   ↓
5. Contador aumenta (+1)
   ↓
6. ¿Contador == 50?
   ├─ SÍ  → Reentrenamiento automático (síncrono, 10-30s)
   │       - Entrena con dataset (1000) + validaciones (50)
   │       - Evalúa calidad
   │       - Si mejora: activa v1.1, mantiene v1.0 como backup
   │       - Si degrada: rechaza, mantiene v1.0
   │
   └─ NO  → Continúa normalmente
```

---

## 📊 Decisiones Clave

| Aspecto | Decisión | Por qué |
|---------|----------|--------|
| **Modelo ML** | RandomForest Regresor | Rápido, interpretable, suficiente para MVP |
| **Privacidad** | Presidio local | RGPD: datos originales nunca se guardan |
| **Active Learning** | 50 validaciones | Balance entre reentrenamiento y datos reales |
| **Reentrenamiento** | Síncrono | Cliente espera, simple de debuguear |
| **Dataset** | ~1000 tickets Faker | Realista, predecible, reproducible |
| **Versionamiento** | v1.0, v1.1, ... | Rollback si nueva versión degrada |

---

## 📁 Estructura de Archivos Clave

```
ciudadai-mvp/
├── backend/
│   ├── main.py                  # FastAPI app
│   ├── models.py                # ORM SQLAlchemy
│   ├── api/
│   │   ├── tickets.py           # POST /api/tickets
│   │   ├── validations.py       # POST /api/validate
│   │   ├── stats.py             # GET /api/stats
│   │   └── retrain.py           # POST /api/retrain
│   ├── services/
│   │   ├── anonymizer.py        # Presidio integration
│   │   ├── predictor.py         # Model inference
│   │   └── retrainer.py         # Retraining logic
│   ├── ml/
│   │   ├── classifier.py        # RandomForest pipeline
│   │   └── trainer.py           # Training script
│   ├── scripts/
│   │   ├── generate_dataset.py  # Faker → DB
│   │   └── train_initial_model.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── models/ (runtime)
│       ├── classifier.pkl
│       └── vectorizer.pkl
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Router
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── TicketDetail.jsx
│   │   │   └── Stats.jsx
│   │   ├── components/
│   │   ├── services/
│   │   │   └── api.js
│   │   └── main.jsx
│   ├── Dockerfile
│   ├── package.json
│   └── vite.config.js
│
├── docker-compose.yml
├── PLAN.md                      # Documento técnico completo
├── QUICK_START.md               # Este archivo
└── spec.md                      # Especificaciones iniciales
```

---

## 🧪 Testing

### Backend
```bash
cd backend
pytest tests/
```

### Frontend
```bash
cd frontend
npm test
```

### Full integration
```bash
docker-compose up --build
# Luego en otra terminal:
python backend/scripts/test_integration.py
```

---

## 📊 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/tickets` | Crear ticket + anonimizar + predecir |
| `GET` | `/api/tickets` | Listar tickets (paginado, filtrable) |
| `GET` | `/api/tickets/{id}` | Detalle ticket |
| `POST` | `/api/validate` | Validar urgencia (Active Learning) |
| `POST` | `/api/retrain` | Reentrenar modelo manualmente |
| `GET` | `/api/stats` | Estadísticas dashboard |

---

## 🔐 Seguridad & Privacidad

### Anonimización
- Presidio detecta: PERSON, EMAIL, PHONE_NUMBER, ID_NUMBER, LOCATION
- Reemplaza con: `<PERSON>`, `<EMAIL>`, etc.
- Datos originales **NUNCA** se guardan en BD
- Solo se guarda hash SHA256 para auditoría RGPD

### Auditoría
- `anonimizacion_log`: entidades detectadas + campos anonimizados
- `modelo_metadata`: versionamiento completo
- `validaciones`: feedback del usuario para Active Learning

---

## 🎯 Próximos Pasos (Roadmap)

**Fase 1: DevOps/Data (6h)**
- [ ] Setup PostgreSQL + Docker Compose
- [ ] Script generador dataset (Faker)
- [ ] Integración Presidio

**Fase 2: ML (14h)**
- [ ] RandomForest pipeline + TF-IDF
- [ ] Training script
- [ ] Testing modelo

**Fase 3: Backend (14h)**
- [ ] API endpoints CRUD
- [ ] Lógica reentrenamiento
- [ ] Tests

**Fase 4: Frontend (12h)**
- [ ] Router + layout
- [ ] Dashboard + validación
- [ ] Estadísticas

**Fase 5: QA/Integración (6h)**
- [ ] E2E testing
- [ ] CI/CD
- [ ] Docs

---

## ❓ Preguntas Frecuentes

**¿Qué pasa si el reentrenamiento degrad el modelo?**
Rollback automático. Se mantiene versión anterior (v1.0).

**¿Los datos originales se guardan en algún lugar?**
No. Son anonimizados inmediatamente. Solo se guarda hash para auditoría.

**¿Puedo forzar reentrenamiento manualmente?**
Sí: `POST /api/retrain?force=true`

**¿Cuánto tarda el reentrenamiento?**
10-30 segundos (síncrono). El cliente espera.

**¿Puedo agregar mis propios casos de uso?**
Sí. PLAN.md describe la arquitectura completa. Extiende fácilmente.

---

## 📝 Licencia & Contacto

Este es un proyecto educativo de demostración.

Equipo: 5 personas × 52 horas = 260 horas-persona
Horizonte: 2 semanas
