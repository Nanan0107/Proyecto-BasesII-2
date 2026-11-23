import { useCallback, useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { Circle, CircleMarker, MapContainer, Polygon, Polyline, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { api } from '../api.js'
import GraficoFacet from '../components/Graficos.jsx'
import PanelSolr from '../components/PanelSolr.jsx'
import { TablaDocs } from '../components/Resultado.jsx'

const CENTRO_CR = [9.75, -84.1]
const COLOR_PUNTO = '#2a78d6'
const COLOR_FORMA = '#eb6834'

const MODOS = [
  { id: 'explorar', titulo: 'Explorar', ayuda: 'Muestra de registros sobre el mapa. Use los filtros de la izquierda.' },
  { id: 'proximidad', titulo: 'Proximidad', ayuda: 'Haga clic en el mapa para elegir el centro y ajuste el radio.' },
  { id: 'poligono', titulo: 'Polígono', ayuda: 'Haga clic para agregar vértices. Cierre el polígono con el botón o haciendo clic en el primer vértice.' },
  { id: 'poligono_facets', titulo: 'Polígono + facets', ayuda: 'Igual que Polígono, y además muestra la distribución de los registros dentro según un atributo.' },
]

const CAMPOS_FACET = [
  ['orden', 'Orden'], ['familia', 'Familia'], ['area_protegida', 'Área protegida'],
  ['categoria_manejo', 'Categoría de manejo'], ['piso_altitudinal', 'Piso altitudinal'],
  ['estacion', 'Estación'], ['etapa_vida', 'Etapa de vida'],
]

export default function VistaMapa({ modoInicial = 'explorar', opciones }) {
  const [modo, setModo] = useState(modoInicial)
  const [orden, setOrden] = useState('')
  const [limite, setLimite] = useState(2000)
  const [radio, setRadio] = useState(15)
  const [centro, setCentro] = useState(null)
  const [vertices, setVertices] = useState([])
  const [cerrado, setCerrado] = useState(false)
  const [campoFacet, setCampoFacet] = useState('orden')
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)
  const pedido = useRef(0)

  const esPoligono = modo === 'poligono' || modo === 'poligono_facets'
  const filtros = orden ? { orden } : {}

  const correr = useCallback(async (fn) => {
    const n = ++pedido.current
    setCargando(true)
    setError(null)
    try {
      const r = await fn()
      if (n === pedido.current) setResultado(r)
    } catch (e) {
      if (n === pedido.current) { setResultado(null); setError(e) }
    } finally {
      if (n === pedido.current) setCargando(false)
    }
  }, [])

  // Ejecuta la consulta que corresponde al modo actual
  useEffect(() => {
    if (modo === 'explorar') {
      correr(() => api.puntos(orden, limite))
    } else if (modo === 'proximidad') {
      if (!centro) { setResultado(null); return }
      const t = setTimeout(() => correr(() => api.proximidad({ lat: centro[0], lon: centro[1], radio_km: radio, filtros, filas: limite })), 250)
      return () => clearTimeout(t)
    } else if (esPoligono) {
      if (!cerrado) { setResultado(null); return }
      const cuerpo = { vertices, filtros, filas: limite, campo_facet: campoFacet }
      correr(() => (modo === 'poligono' ? api.poligono(cuerpo) : api.poligonoFacets(cuerpo)))
    }
  }, [modo, orden, limite, radio, centro, cerrado, vertices, campoFacet]) // eslint-disable-line react-hooks/exhaustive-deps

  const cambiarModo = (m) => {
    setModo(m)
    setResultado(null)
    setError(null)
    if (!(m.startsWith('poligono') && esPoligono)) { setVertices([]); setCerrado(false) }
  }

  const limpiar = () => { setVertices([]); setCerrado(false); setCentro(null); setResultado(null); setError(null) }

  const alClicMapa = (latlng) => {
    if (modo === 'proximidad') setCentro([latlng.lat, latlng.lng])
    else if (esPoligono && !cerrado) setVertices((v) => [...v, [latlng.lat, latlng.lng]])
  }

  const docs = resultado?.docs || []
  const facets = (resultado?.facets || []).filter((f) => f.buckets.length)
  const ayuda = MODOS.find((m) => m.id === modo).ayuda

  return (
    <div className="vista-mapa">
      <aside className="panel-mapa">
        <section>
          <h2>Tipo de consulta</h2>
          <div className="modos" role="radiogroup">
            {MODOS.map((m) => (
              <button key={m.id} role="radio" aria-checked={modo === m.id} onClick={() => cambiarModo(m.id)}>{m.titulo}</button>
            ))}
          </div>
          <p className="ayuda">{ayuda}</p>
        </section>

        <section className="controles">
          <label className="campo">
            <span>Filtrar por orden</span>
            <select value={orden} onChange={(e) => setOrden(e.target.value)}>
              <option value="">— Todos —</option>
              {(opciones.orden || []).map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </label>
          <label className="campo">
            <span>Máximo de puntos a dibujar</span>
            <select value={limite} onChange={(e) => setLimite(Number(e.target.value))}>
              {[500, 1000, 2000, 5000].map((n) => <option key={n} value={n}>{n.toLocaleString('es-CR')}</option>)}
            </select>
          </label>

          {modo === 'proximidad' && (
            <label className="campo">
              <span>Radio: <b>{radio} km</b></span>
              <input type="range" min="1" max="100" value={radio} onChange={(e) => setRadio(Number(e.target.value))} />
            </label>
          )}

          {modo === 'poligono_facets' && (
            <label className="campo">
              <span>Facet sobre</span>
              <select value={campoFacet} onChange={(e) => setCampoFacet(e.target.value)}>
                {CAMPOS_FACET.map(([v, e]) => <option key={v} value={v}>{e}</option>)}
              </select>
            </label>
          )}

          {esPoligono && (
            <div className="herramientas">
              <span className="nota">{vertices.length} vértice{vertices.length === 1 ? '' : 's'}{cerrado ? ' · cerrado' : ''}</span>
              <div className="botones">
                <button disabled={cerrado || !vertices.length} onClick={() => setVertices((v) => v.slice(0, -1))}>Deshacer</button>
                <button className="primario" disabled={cerrado || vertices.length < 3} onClick={() => setCerrado(true)}>Cerrar y consultar</button>
                <button disabled={!vertices.length} onClick={limpiar}>Limpiar</button>
              </div>
            </div>
          )}
          {modo === 'proximidad' && centro && (
            <div className="herramientas">
              <span className="nota">Centro: {centro[0].toFixed(4)}, {centro[1].toFixed(4)}</span>
              <div className="botones"><button onClick={limpiar}>Limpiar</button></div>
            </div>
          )}
        </section>

        <section className="resultado-mapa">
          {error && (
            <div className={`aviso ${error.pendiente ? 'pendiente' : 'error'}`}>
              {error.pendiente
                ? <><strong>Pendiente de implementar.</strong> Falta la función en <code>backend/app/consultas/geoespaciales.py</code>.</>
                : <><strong>Error:</strong> {error.message}</>}
            </div>
          )}
          {resultado && (
            <>
              <div className="resumen">
                <div className="total">
                  <span className="valor">{resultado.numFound.toLocaleString('es-CR')}</span>
                  {modo === 'explorar' ? ' registros en el índice' : esPoligono ? ' registros dentro del polígono' : ` registros a ≤ ${radio} km`}
                </div>
                <div className="nota">
                  {docs.length < resultado.numFound
                    ? `Se dibujan ${docs.length.toLocaleString('es-CR')} puntos (límite elegido).`
                    : `Se dibujan los ${docs.length.toLocaleString('es-CR')} puntos.`}
                  {resultado.qtime != null && ` Solr: ${resultado.qtime} ms.`}
                </div>
              </div>
              {facets.map((f) => <GraficoFacet key={f.nombre} facet={f} visualizacion="barras" />)}
              {modo === 'proximidad' && docs.length > 0 && (
                <>
                  <h3 className="subtitulo">Los más cercanos</h3>
                  <TablaDocs docs={docs} max={8} />
                </>
              )}
              {modo !== 'explorar' && <PanelSolr resultado={resultado} />}
            </>
          )}
          {!resultado && !error && !cargando && modo !== 'explorar' && <p className="vacio">{ayuda}</p>}
        </section>
      </aside>

      <div className={`mapa ${modo !== 'explorar' && !(esPoligono && cerrado) ? 'dibujando' : ''} ${cargando ? 'cargando' : ''}`}>
        <MapContainer center={CENTRO_CR} zoom={8} preferCanvas doubleClickZoom={false} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <ClicMapa onClic={alClicMapa} />
          <CapaPuntos docs={docs} interactivo={modo === 'explorar' || (esPoligono && cerrado)} />

          {modo === 'proximidad' && centro && (
            <>
              <Circle center={centro} radius={radio * 1000} pathOptions={{ color: COLOR_FORMA, weight: 2, fillOpacity: 0.06 }} interactive={false} />
              <CircleMarker center={centro} radius={6} pathOptions={{ color: '#fff', weight: 2, fillColor: COLOR_FORMA, fillOpacity: 1 }} interactive={false} />
            </>
          )}

          {esPoligono && vertices.length > 0 && (cerrado
            ? <Polygon positions={vertices} pathOptions={{ color: COLOR_FORMA, weight: 2, fillOpacity: 0.06 }} interactive={false} />
            : <Polyline positions={vertices} pathOptions={{ color: COLOR_FORMA, weight: 2, dashArray: '6 6' }} interactive={false} />)}
          {esPoligono && vertices.map((v, i) => (
            <CircleMarker
              key={i}
              center={v}
              radius={i === 0 && !cerrado && vertices.length >= 3 ? 9 : 6}
              pathOptions={{ color: '#fff', weight: 2, fillColor: COLOR_FORMA, fillOpacity: 1 }}
              bubblingMouseEvents={false}
              eventHandlers={{ click: () => { if (i === 0 && !cerrado && vertices.length >= 3) setCerrado(true) } }}
            />
          ))}
        </MapContainer>
        <div className="leyenda">
          <span><i style={{ background: COLOR_PUNTO }} /> Registro de insecto</span>
          {modo !== 'explorar' && <span><i style={{ background: COLOR_FORMA }} /> {modo === 'proximidad' ? 'Centro y radio' : 'Polígono'}</span>}
        </div>
      </div>
    </div>
  )
}

function ClicMapa({ onClic }) {
  useMapEvents({ click: (e) => onClic(e.latlng) })
  return null
}

// Capa de puntos dibujada directamente con Leaflet (canvas): miles de puntos
// sin crear un componente React por cada uno.
function CapaPuntos({ docs, interactivo }) {
  const mapa = useMap()
  useEffect(() => {
    const capa = L.layerGroup()
    const renderer = L.canvas({ padding: 0.5 })
    docs.forEach((d) => {
      if (d.latitud == null || d.longitud == null) return
      const m = L.circleMarker([d.latitud, d.longitud], {
        renderer, radius: 4, weight: 1, color: '#ffffff', fillColor: COLOR_PUNTO, fillOpacity: 0.85,
        interactive: interactivo, bubblingMouseEvents: false,
      })
      if (interactivo) m.bindPopup(() => popup(d))
      capa.addLayer(m)
    })
    capa.addTo(mapa)
    return () => { capa.remove() }
  }, [docs, interactivo, mapa])
  return null
}

function popup(d) {
  const div = document.createElement('div')
  div.className = 'popup'
  const filas = [
    ['Orden', d.orden], ['Área protegida', d.area_protegida], ['Elevación', d.elevacion_m != null ? `${d.elevacion_m} m` : null],
    ['Fecha', d.fecha_evento?.slice(0, 10)], ['Distancia', d.dist != null ? `${Number(d.dist).toFixed(2)} km` : null],
  ].filter(([, v]) => v != null)
  const t = document.createElement('strong')
  t.className = 'cientifico'
  t.textContent = d.nombre_cientifico || d.id
  div.appendChild(t)
  filas.forEach(([k, v]) => {
    const p = document.createElement('div')
    p.textContent = `${k}: ${v}`
    div.appendChild(p)
  })
  return div
}
