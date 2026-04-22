-- Schema PostgreSQL inicial para CiudadAI

CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    descripcion TEXT NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    urgencia_predicha INT,
    urgencia_real INT,
    canal VARCHAR(10) NOT NULL,
    ubicacion_incidencia TEXT,
    ubicacion_descripcion TEXT,
    fecha_creacion TIMESTAMP DEFAULT NOW(),
    fecha_actualizacion TIMESTAMP DEFAULT NOW(),
    persona_anonimizado VARCHAR(50),
    apellidos_anonimizado VARCHAR(50),
    nif_anonimizado VARCHAR(50),
    telefono_anonimizado VARCHAR(50),
    email_anonimizado VARCHAR(50),
    direccion_anonimizado VARCHAR(255),
    anonimizacion_hash VARCHAR(64),
    modelo_version VARCHAR(20) DEFAULT 'v1.0'
);

CREATE TABLE IF NOT EXISTS predicciones (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    urgencia_predicha INT NOT NULL,
    confianza FLOAT NOT NULL,
    modelo_version VARCHAR(20) NOT NULL,
    fecha_prediccion TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS validaciones (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    urgencia_real INT NOT NULL,
    usuario_id VARCHAR(50),
    notas TEXT,
    procesado BOOLEAN DEFAULT FALSE,
    fecha_validacion TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS anonimizacion_log (
    id SERIAL PRIMARY KEY,
    ticket_id INT NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    entidades_detectadas JSONB,
    campos_anonimizados JSONB,
    fecha_anonimizacion TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS modelo_metadata (
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
