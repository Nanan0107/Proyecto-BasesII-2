import { useEffect, useState } from 'react'
import { api } from './api.js'
import VistaConsultas from './vistas/VistaConsultas.jsx'
import VistaMapa from './vistas/VistaMapa.jsx'

export default function App() {
  const [vista, setVista] = useState('consultas')
  const [modoMapa, setModoMapa] = useState('explorar')
  const [estado, setEstado] = useState(null)
  const [catalogo, setCatalogo] = useState(null)
  const [opciones, setOpciones] = useState({})
  const [errorInicio, setErrorInicio] = useState(null)

  useEffect(() => {
    const revisar = () => api.estado().then(setEstado).catch((e) => setEstado({ ok: false, error: e.message }))
    revisar()
    const t = setInterval(revisar, 15000)
    api.catalogo().then(setCatalogo).catch((e) => setErrorInicio(e.message))
    api.opciones().then(setOpciones).catch(() => {})
    return () => clearInterval(t)
  }, [])

  const abrirMapa = (modo) => {
    setModoMapa(modo)
    setVista('mapa')
  }

  return (
    <div className="app">
      <header className="encabezado">
        <div className="marca">
          <span className="logo" aria-hidden>
            <svg viewBox="0 0 24 24" width="22" height="22"><path fill="currentColor" d="M12 2c1 1.6 1.4 3 1.2 4.3A4 4 0 0 1 16 10v.6l3.3-1.9.8 1.4L16 12.4V14l4 1-.4 1.6-3.8-1a4.6 4.6 0 0 1-.3.9l2.8 2.8-1.2 1.2-2.6-2.6A4 4 0 0 1 12 20a4 4 0 0 1-2.5-.9l-2.6 2.6-1.2-1.2 2.8-2.8a4.6 4.6 0 0 1-.3-.9l-3.8 1L4 15l4-1v-1.6L3.9 10.1l.8-1.4L8 10.6V10a4 4 0 0 1 2.8-3.7C10.6 5 11 3.6 12 2Z"/></svg>
          </span>
          <div>
            <h1>Insectos en áreas protegidas de Costa Rica</h1>
            <p>Consultas y visualización sobre Apache Solr</p>
          </div>
        </div>
        <nav className="pestanas" role="tablist">
          <button role="tab" aria-selected={vista === 'consultas'} onClick={() => setVista('consultas')}>Consultas</button>
          <button role="tab" aria-selected={vista === 'mapa'} onClick={() => setVista('mapa')}>Mapa</button>
        </nav>
        <EstadoSolr estado={estado} />
      </header>

      {errorInicio && <div className="aviso error">No se pudo cargar el catálogo: {errorInicio}</div>}

      <main className="contenido">
        {vista === 'consultas' && catalogo && (
          <VistaConsultas catalogo={catalogo} opciones={opciones} onAbrirMapa={abrirMapa} />
        )}
        {vista === 'mapa' && (
          <VistaMapa modoInicial={modoMapa} opciones={opciones} key={modoMapa} />
        )}
      </main>
    </div>
  )
}

function EstadoSolr({ estado }) {
  if (!estado) return <div className="estado-solr">Conectando…</div>
  return (
    <div className={`estado-solr ${estado.ok ? 'ok' : 'mal'}`} title={estado.url || estado.error}>
      <span className="punto" />
      {estado.ok ? `Solr · ${estado.documentos.toLocaleString('es-CR')} documentos` : 'Solr no disponible'}
    </div>
  )
}
