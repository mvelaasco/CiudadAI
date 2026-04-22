import { useMemo, useState } from 'react'
import './App.css'

const initialTicket = {
  nombre: '',
  apellidos: '',
  email: '',
  categoria: 'Limpieza',
  descripcion: '',
  canal: 'Web',
  telefono: '',
  direccion_persona: '',
  ubicacion_incidencia: '',
}

function App() {
  const [ticket, setTicket] = useState(initialTicket)
  const [createdTicket, setCreatedTicket] = useState(null)
  const [lookupId, setLookupId] = useState('')
  const [lookupTicket, setLookupTicket] = useState(null)
  const [loading, setLoading] = useState(false)
  const [lookupLoading, setLookupLoading] = useState(false)
  const [error, setError] = useState('')

  const urgencyLabel = useMemo(() => {
    if (!createdTicket) {
      return 'Todavía no hay ticket creado'
    }

    const labels = {
      1: 'Muy baja',
      2: 'Baja',
      3: 'Media',
      4: 'Alta',
      5: 'Crítica',
    }

    return labels[createdTicket.urgencia_predicha] ?? 'No disponible'
  }, [createdTicket])

  const handleChange = event => {
    const { name, value } = event.target
    setTicket(currentTicket => ({ ...currentTicket, [name]: value }))
  }

  const handleSubmit = async event => {
    event.preventDefault()
    setLoading(true)
    setError('')
    setLookupTicket(null)

    try {
      const response = await fetch('/api/tickets', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(ticket),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'No se pudo crear el ticket')
      }

      setCreatedTicket(data)
      setLookupId(String(data.id))
      setTicket(initialTicket)
    } catch (submitError) {
      setError(submitError.message)
    } finally {
      setLoading(false)
    }
  }

  const handleLookup = async event => {
    event.preventDefault()
    if (!lookupId.trim()) {
      return
    }

    setLookupLoading(true)
    setError('')

    try {
      const response = await fetch(`/api/tickets/${lookupId.trim()}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'No se pudo recuperar el ticket')
      }

      setLookupTicket(data)
    } catch (lookupError) {
      setError(lookupError.message)
      setLookupTicket(null)
    } finally {
      setLookupLoading(false)
    }
  }

  return (
    <main className="page-shell">
      <section className="hero-card">
        <div>
          <p className="eyebrow">CiudadAI</p>
          <h1>Crear ticket y ver respuesta</h1>
          <p className="hero-copy">
            Envía una incidencia, guarda el ticket en PostgreSQL y revisa la
            respuesta que devuelve el backend.
          </p>
        </div>
        <div className="status-pill">Backend + API + BD conectados</div>
      </section>

      <section className="content-grid">
        <article className="panel">
          <h2>Nuevo ticket</h2>
          <form className="ticket-form" onSubmit={handleSubmit}>
            <div className="field-grid">
              <label>
                Nombre
                <input name="nombre" value={ticket.nombre} onChange={handleChange} required />
              </label>
              <label>
                Apellidos
                <input name="apellidos" value={ticket.apellidos} onChange={handleChange} required />
              </label>
            </div>

            <div className="field-grid">
              <label>
                Email
                <input name="email" type="email" value={ticket.email} onChange={handleChange} required />
              </label>
              <label>
                Teléfono
                <input name="telefono" value={ticket.telefono} onChange={handleChange} placeholder="Opcional" />
              </label>
            </div>

            <div className="field-grid">
              <label>
                Categoría
                <select name="categoria" value={ticket.categoria} onChange={handleChange}>
                  <option>Limpieza</option>
                  <option>Seguridad</option>
                  <option>Movilidad</option>
                  <option>Sanidad</option>
                  <option>Otros</option>
                </select>
              </label>
              <label>
                Canal
                <select name="canal" value={ticket.canal} onChange={handleChange}>
                  <option>Web</option>
                  <option>App</option>
                  <option>Teléfono</option>
                </select>
              </label>
            </div>

            <label>
              Descripción
              <textarea
                name="descripcion"
                rows="5"
                value={ticket.descripcion}
                onChange={handleChange}
                required
                placeholder="Describe la incidencia con el mayor detalle posible"
              />
            </label>

            <div className="field-grid">
              <label>
                Dirección
                <input
                  name="direccion_persona"
                  value={ticket.direccion_persona}
                  onChange={handleChange}
                  placeholder="Opcional"
                />
              </label>
              <label>
                Ubicación incidencia
                <input
                  name="ubicacion_incidencia"
                  value={ticket.ubicacion_incidencia}
                  onChange={handleChange}
                  placeholder="Opcional"
                />
              </label>
            </div>

            {error ? <p className="error-banner">{error}</p> : null}

            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? 'Creando...' : 'Crear ticket'}
            </button>
          </form>
        </article>

        <article className="panel">
          <h2>Respuesta del ticket</h2>
          {createdTicket ? (
            <div className="response-card">
              <div className="response-header">
                <span className="response-id">Ticket #{createdTicket.id}</span>
                <span className="response-badge">{urgencyLabel}</span>
              </div>
              <p>{createdTicket.mensaje}</p>
              <dl>
                <div>
                  <dt>Categoría</dt>
                  <dd>{createdTicket.categoria}</dd>
                </div>
                <div>
                  <dt>Urgencia predicha</dt>
                  <dd>{createdTicket.urgencia_predicha} / 5</dd>
                </div>
                <div>
                  <dt>Confianza</dt>
                  <dd>{Math.round(createdTicket.confianza * 100)}%</dd>
                </div>
                <div>
                  <dt>Fecha</dt>
                  <dd>{new Date(createdTicket.fecha_creacion).toLocaleString('es-ES')}</dd>
                </div>
              </dl>
            </div>
          ) : (
            <p className="empty-state">Aún no has creado ningún ticket.</p>
          )}

          <form className="lookup-form" onSubmit={handleLookup}>
            <label>
              Consultar por ID
              <input value={lookupId} onChange={event => setLookupId(event.target.value)} />
            </label>
            <button className="secondary-button" type="submit" disabled={lookupLoading}>
              {lookupLoading ? 'Buscando...' : 'Ver ticket'}
            </button>
          </form>

          {lookupTicket ? (
            <div className="response-card muted-card">
              <div className="response-header">
                <span className="response-id">Ticket #{lookupTicket.id}</span>
                <span className="response-badge">Recuperado</span>
              </div>
              <p>{lookupTicket.mensaje}</p>
              <dl>
                <div>
                  <dt>Descripción</dt>
                  <dd>{lookupTicket.descripcion}</dd>
                </div>
                <div>
                  <dt>Urgencia</dt>
                  <dd>{lookupTicket.urgencia_predicha} / 5</dd>
                </div>
                <div>
                  <dt>Canal</dt>
                  <dd>{lookupTicket.canal}</dd>
                </div>
              </dl>
            </div>
          ) : null}
        </article>
      </section>
    </main>
  )
}

export default App
