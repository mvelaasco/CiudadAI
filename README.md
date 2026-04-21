# CiudadAI – Plataforma de Gestión y Triaje Inteligente

[![Estado](https://img.shields.io/badge/Estado-Plan%20Confirmado-green)]()
[![Equipo](https://img.shields.io/badge/Equipo-5%20personas-blue)]()
[![Horas](https://img.shields.io/badge/Horas-52h%20%2Fpersona-orange)]()

---

## 📚 Documentación

Este proyecto contiene documentación completa organizada en diferentes niveles:

### Para Gestores / Stakeholders
- **[QUICK_START.md](QUICK_START.md)** ⭐ Empieza aquí
  - Resumen ejecutivo
  - Arquitectura visual
  - Flujo Active Learning
  - Decisiones clave
  - FAQs

### Para Desarrolladores
- **[PLAN.md](PLAN.md)** 📋 Plan técnico completo
  - Decisiones confirmadas
  - Todas las 5 fases detalladas
  - Schema PostgreSQL completo
  - API endpoints especificados
  - Timeline por persona

- **[TECH_SPECS.md](TECH_SPECS.md)** 💻 Especificaciones técnicas
  - Schema SQL con índices
  - Módulos backend (main.py, services, ml)
  - Componentes frontend (React/Vite)
  - Ejemplos de código
  - Testing strategy

### Especificaciones Iniciales
- **[spec.md](spec.md)** 📄 Especificaciones del MVP (Bala Trazadora)

---

## 🎯 Resumen Ejecutivo

**CiudadAI** automatiza el triaje de solicitudes ciudadanas mediante:

| Característica | Detalle |
|---|---|
| **Privacidad** | Anonimización local (Presidio). Datos originales NUNCA se guardan |
| **IA Adaptativa** | RandomForest predice urgencia (1-5) basado en descripción + categoría |
| **Active Learning** | Admin valida predicciones → Reentrenamiento automático cada 50 validaciones |
| **Auditoría Completa** | Logs de anonimización + Versionamiento de modelos + Rollback automático |

---

## 🏗️ Arquitectura

```
┌──────────────┐        ┌─────────────────────┐        ┌──────────────┐
│ Frontend     │        │ Backend             │        │ PostgreSQL   │
│ (React+Vite) │◄──────►│ (FastAPI + Python)  │◄──────►│ + Presidio   │
│ :5173        │        │ :8000               │        │ :5432        │
│              │        │                     │        │              │
│ • Dashboard  │        │ • Anonimización     │        │ tickets      │
│ • Validación │        │ • Modelo ML         │        │ predicciones │
│ • Estadísticas│       │ • Active Learning   │        │ validaciones │
└──────────────┘        │ • Reentrenamiento   │        │ logs         │
                        └─────────────────────┘        └──────────────┘
```

---

## 🚀 Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| **Backend** | FastAPI + Python | 3.11 |
| **Frontend** | React + Vite | Node 20 |
| **Database** | PostgreSQL | 15 |
| **ML** | scikit-learn | RandomForest |
| **Privacidad** | Microsoft Presidio | - |
| **DevOps** | Docker Compose | - |
| **CI/CD** | GitHub Actions | - |

---

## 📋 Fases del Proyecto (52 horas/persona)

### Fase 1: Arquitectura & DevOps (6h)
- [ ] Setup PostgreSQL + Docker Compose
- [ ] Schema BD + Alembic migrations
- [ ] Variables de entorno

### Fase 2: Data & NLP (14h)
- [ ] Dataset sintético con Faker (~1000 tickets)
- [ ] Anonimización con Presidio
- [ ] RandomForest + TF-IDF pipeline

### Fase 3: Backend (14h)
- [ ] API endpoints (POST/GET tickets, POST validate)
- [ ] ORM SQLAlchemy
- [ ] Lógica reentrenamiento síncrono

### Fase 4: Frontend (12h)
- [ ] Router + layout
- [ ] Dashboard + componentes
- [ ] Integración API

### Fase 5: QA & Integración (6h)
- [ ] Tests (backend + frontend)
- [ ] CI/CD (GitHub Actions)
- [ ] Documentación final

---

## 🔄 Flujo Active Learning (Clave)

```
1. Admin crea ticket
   ↓
2. Sistema anonimiza + predice urgencia
   ↓
3. Admin valida urgencia
   ↓
4. Contador += 1
   ↓
5. ¿Contador == 50?
   ├─ SÍ  → Reentrenamiento (síncrono, 10-30s)
   │       → Entrena con dataset (1000) + validaciones (50)
   │       → Si mejora: activa v1.1
   │       → Si no: rollback v1.0
   └─ NO  → Continúa normalmente
```

---

## 📊 API Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/tickets` | Crear + anonimizar + predecir urgencia |
| `GET` | `/api/tickets` | Listar tickets (paginado, filtrable) |
| `GET` | `/api/tickets/{id}` | Detalle ticket |
| `POST` | `/api/validate` | Validar urgencia (Active Learning) |
| `POST` | `/api/retrain` | Reentrenar modelo |
| `GET` | `/api/stats` | Estadísticas dashboard |

**Ejemplo:**
```bash
# Crear ticket
curl -X POST http://localhost:8000/api/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Juan",
    "apellidos": "Martínez",
    "nif": "12345678A",
    "telefono": "612345678",
    "email": "juan@mail.com",
    "categoria": "Limpieza",
    "descripcion": "Basura acumulada frente escuela",
    "canal": "Web",
    "direccion_persona": "Calle Principal 42",
    "ubicacion_incidencia": {"lat": 40.4, "lon": -3.7, "descripcion": "Portal 12"}
  }'

# Validar urgencia
curl -X POST http://localhost:8000/api/validate \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": 1,
    "urgencia_real": 4,
    "usuario_id": "admin@ayuntamiento.es"
  }'
```

---

## 🔐 Seguridad & Privacidad

### Anonimización en Tiempo Real
- ✅ Presidio detecta: PERSON, EMAIL, PHONE, ID_NUMBER, LOCATION
- ✅ Reemplaza con: `<PERSON>`, `<EMAIL>`, etc.
- ✅ Datos originales **NUNCA** se guardan
- ✅ Solo hash SHA256 para auditoría RGPD

### Versionamiento de Modelos
- ✅ v1.0 (inicial) → v1.1 (reentrenado)
- ✅ Backup automático de versión anterior
- ✅ Rollback si nueva versión degrada

---

## 🧪 Testing

```bash
# Backend
cd backend
pytest tests/

# Frontend
cd frontend
npm test

# Full integration
docker-compose up --build
```

---

## 📁 Estructura de Carpetas

```
ciudadai-mvp/
├── backend/
│   ├── main.py
│   ├── models.py (ORM)
│   ├── api/ (endpoints)
│   ├── services/ (anonymizer, predictor, retrainer)
│   ├── ml/ (classifier, trainer)
│   ├── scripts/ (generate_dataset, train_initial_model)
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx (router)
│   │   ├── pages/ (Dashboard, TicketDetail, Stats)
│   │   ├── components/
│   │   ├── services/ (api.js)
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
├── docker-compose.yml
├── PLAN.md (plan técnico completo)
├── QUICK_START.md (guía rápida)
├── TECH_SPECS.md (especificaciones técnicas)
├── spec.md (especificaciones iniciales)
└── README.md (este archivo)
```

---

## 🚀 Arranque Rápido

### 1. Prerequisitos
```bash
- Docker & Docker Compose
- Python 3.11+
- Node.js 20+
```

### 2. Build & Run
```bash
cd ciudadai-mvp
docker-compose up --build
```

### 3. Acceder
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 📞 Decisiones Confirmadas ✅

| Decisión | Razón |
|----------|-------|
| RandomForest Regresor | Rápido, interpretable, suficiente para MVP |
| Reentrenamiento síncrono cada 50 validaciones | Balance y simpleza |
| Anonimización local con Presidio | RGPD: datos NUNCA salen del servidor |
| PostgreSQL en Docker | Consistencia con infraestructura |
| 52h/persona | Realista para MVP completo |
| Versionamiento modelos | Rollback si degrada |

---

## ❓ Preguntas Frecuentes

**¿Qué pasa si el modelo se degrada?**
- Rollback automático. v1.0 se mantiene como backup.

**¿Dónde se guardan los datos originales?**
- NUNCA. Se anonimiza inmediatamente. Solo hash para auditoría.

**¿Puedo forzar reentrenamiento?**
- Sí: `POST /api/retrain?force=true`

**¿Cuánto tarda el reentrenamiento?**
- 10-30 segundos (síncrono). Cliente espera.

**¿Puedo extender el proyecto?**
- Sí. Arquitectura modular + bien documentada.

---

## 🎯 Próximos Pasos

1. ✅ Plan confirmado (LISTO AQUÍ)
2. ⏳ Implementar Fase 1: DevOps + BD
3. ⏳ Implementar Fase 2: Data + NLP
4. ⏳ Implementar Fase 3: Backend
5. ⏳ Implementar Fase 4: Frontend
6. ⏳ Implementar Fase 5: QA + Integración
7. ⏳ Deploy en producción

---

## 📖 Estructura de Documentación

```
README.md (este archivo) ← EMPIEZA AQUÍ
    ↓
QUICK_START.md (guía para todos)
    ↓
    ├─→ PLAN.md (dev: plan técnico)
    └─→ TECH_SPECS.md (dev: código + APIs)
        ↓
        spec.md (referencia original)
```

---

## 📝 Información del Proyecto

| Aspecto | Detalle |
|--------|--------|
| **Nombre** | CiudadAI – Plataforma de Gestión y Triaje Inteligente |
| **Objetivo** | Automatizar triaje de solicitudes ciudadanas con privacidad RGPD |
| **Equipo** | 5 personas |
| **Timeline** | 52 horas/persona = 2 semanas |
| **Stack** | FastAPI + React + PostgreSQL + RandomForest + Presidio |
| **Status** | ✅ Plan Confirmado - Listo para Implementar |

---

**Documento actualizado:** 2026-01-21
**Versión:** 1.0 - Plan Confirmado

```
╔════════════════════════════════════════╗
║  🚀 LISTO PARA IMPLEMENTAR              ║
║  Plan confirmado y validado por equipo ║
║  Documentación completa (1874 líneas)  ║
╚════════════════════════════════════════╝
```
