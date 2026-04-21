# SPEC.MD: Arquitectura Atómica (Bala Trazadora)

## 1. Objetivo del Hito
Demostrar la viabilidad de la infraestructura. El objetivo exclusivo es que el Frontend (React) envíe una petición al Backend (FastAPI), este la procese y devuelva una respuesta, y el Frontend la renderice. Todo esto orquestado bajo un único comando de Docker Compose.

**Restricción estricta:** Prohibido añadir bases de datos, modelos de IA o estilos CSS hasta que este flujo esté validado al 100%.

---

## 2. Pila Tecnológica Base
* **Backend:** FastAPI (Python 3.12)
* **Frontend:** React (usando Vite, Node 20)
* **Infraestructura:** Docker & Docker Compose

---

## 3. Estructura de Archivos Obligatoria
No inventen arquitecturas complejas. Respeten esta jerarquía plana:

```text
/ciudadai-mvp
│
├── /backend
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── /frontend
│   ├── src/
│   │   └── App.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
│
└── docker-compose.yml