// Visualización de los facets normalizados por la API.
// Cada facet: { nombre, tipo, buckets: [{valor, conteo, metricas, hijos}], metricas }
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

// Paleta categórica en orden fijo (validada para daltonismo en pares adyacentes)
// Los atributos SVG de Recharts no aceptan var(--…): se leen los tokens CSS.
const token = (n) => getComputedStyle(document.documentElement).getPropertyValue(n).trim()
export const serie = (i) => token(`--serie-${i + 1}`)
const color = (v) => (v.startsWith('var(') ? token(v.slice(4, -1)) : v)

const fmt = (n) => (typeof n === 'number'
  ? n.toLocaleString('es-CR', { maximumFractionDigits: 2 })
  : n)

const ejeTexto = { fill: 'currentColor', fontSize: 12 }

export function etiquetaValor(v) {
  if (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T/.test(v)) return v.slice(0, 10)
  if (typeof v === 'number') return fmt(v)
  return String(v)
}

function Consejo({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="tooltip">
      <strong>{etiquetaValor(label)}</strong>
      {payload.map((p) => (
        <div key={p.dataKey}>
          <span className="muestra" style={{ background: p.color }} /> {p.name}: <b>{fmt(p.value)}</b>
        </div>
      ))}
    </div>
  )
}

export default function GraficoFacet({ facet, visualizacion }) {
  if (facet.tipo === 'metricas') return <Tarjetas metricas={facet.metricas} />
  if (!facet.buckets.length) return <p className="vacio">El facet «{facet.nombre}» no tiene valores.</p>

  const anidado = facet.buckets.some((b) => b.hijos?.length)
  const conMetricas = facet.buckets.some((b) => Object.keys(b.metricas || {}).length)

  return (
    <figure className="grafico">
      <figcaption>
        <span className="chip suave">{nombreTipo(facet.tipo, anidado)}</span> {facet.nombre}
        {facet.metricas?.gap != null && <span className="nota"> · intervalo {facet.metricas.gap}</span>}
      </figcaption>
      {anidado ? <Anidado facet={facet} />
        : facet.tipo === 'rango' || visualizacion === 'histograma' ? <Histograma facet={facet} />
          : <Barras facet={facet} />}
      {conMetricas && !anidado && <TablaMetricas facet={facet} />}
      <details className="tabla-datos">
        <summary>Ver como tabla</summary>
        <TablaBuckets facet={facet} />
      </details>
    </figure>
  )
}

function nombreTipo(tipo, anidado) {
  if (anidado) return 'Facet anidado'
  return { campo: 'Field facet', rango: 'Range facet', consulta: 'Query facet', pivot: 'Pivot', json: 'JSON facet' }[tipo] || tipo
}

function Barras({ facet }) {
  const datos = facet.buckets.map((b) => ({ nombre: etiquetaValor(b.valor), conteo: b.conteo }))
  const alto = Math.max(160, datos.length * 30 + 40)
  const ancho = Math.min(220, Math.max(80, ...datos.map((d) => d.nombre.length * 7)))
  return (
    <ResponsiveContainer width="100%" height={alto}>
      <BarChart data={datos} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }} barCategoryGap={2}>
        <CartesianGrid horizontal={false} stroke={color('var(--grid)')} />
        <XAxis type="number" tick={ejeTexto} tickFormatter={fmt} stroke={color('var(--eje)')} />
        <YAxis type="category" dataKey="nombre" width={ancho} tick={ejeTexto} stroke={color('var(--eje)')} interval={0} />
        <Tooltip content={<Consejo />} cursor={{ fill: color('var(--hover)') }} />
        <Bar dataKey="conteo" name="Registros" fill={serie(0)} radius={[0, 4, 4, 0]} maxBarSize={22} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function Histograma({ facet }) {
  const datos = facet.buckets.map((b) => ({ nombre: etiquetaValor(b.valor), conteo: b.conteo }))
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={datos} margin={{ left: 8, right: 16, top: 8, bottom: 4 }} barCategoryGap={2}>
        <CartesianGrid vertical={false} stroke={color('var(--grid)')} />
        <XAxis dataKey="nombre" tick={ejeTexto} stroke={color('var(--eje)')} />
        <YAxis tick={ejeTexto} tickFormatter={fmt} stroke={color('var(--eje)')} />
        <Tooltip content={<Consejo />} cursor={{ fill: color('var(--hover)') }} />
        <Bar dataKey="conteo" name="Registros" fill={serie(0)} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function Anidado({ facet }) {
  // Las series (valores del segundo nivel) se ordenan por su total y se limitan
  // a 7 + «Otros», para no generar colores nuevos.
  const totales = new Map()
  facet.buckets.forEach((b) => b.hijos.forEach((h) => totales.set(h.valor, (totales.get(h.valor) || 0) + h.conteo)))
  const orden = [...totales.entries()].sort((a, b) => b[1] - a[1]).map(([v]) => String(v))
  const series = orden.slice(0, 7)
  const hayOtros = orden.length > 7 || facet.buckets.some((b) => b.conteo > b.hijos.reduce((s, h) => s + h.conteo, 0))
  const datos = facet.buckets.map((b) => {
    const fila = { nombre: etiquetaValor(b.valor) }
    let suma = 0
    b.hijos.forEach((h) => {
      if (series.includes(String(h.valor))) { fila[h.valor] = h.conteo; suma += h.conteo }
    })
    if (hayOtros) fila.Otros = b.conteo - suma
    return fila
  })
  const claves = hayOtros ? [...series, 'Otros'] : series
  const alto = Math.max(200, datos.length * 34 + 70)
  return (
    <ResponsiveContainer width="100%" height={alto}>
      <BarChart data={datos} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }} barCategoryGap={3}>
        <CartesianGrid horizontal={false} stroke={color('var(--grid)')} />
        <XAxis type="number" tick={ejeTexto} tickFormatter={fmt} stroke={color('var(--eje)')} />
        <YAxis type="category" dataKey="nombre" width={170} tick={ejeTexto} stroke={color('var(--eje)')} interval={0} />
        <Tooltip content={<Consejo />} cursor={{ fill: color('var(--hover)') }} />
        {/* El texto de la leyenda va en color de texto; la muestra de color identifica la serie */}
        <Legend wrapperStyle={{ fontSize: 12 }}
          formatter={(v) => <span style={{ color: 'var(--texto-2)' }}>{v}</span>} />
        {claves.map((k, i) => (
          <Bar key={k} dataKey={k} name={k} stackId="a" maxBarSize={24}
            fill={k === 'Otros' ? color('var(--otros)') : serie(i)} stroke={color('var(--superficie)')} strokeWidth={1} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

function TablaMetricas({ facet }) {
  const cols = [...new Set(facet.buckets.flatMap((b) => Object.keys(b.metricas || {})))]
  return (
    <div className="tabla-scroll">
      <table className="tabla">
        <thead>
          <tr><th>{facet.nombre}</th><th className="num">Registros</th>{cols.map((c) => <th key={c} className="num">{c}</th>)}</tr>
        </thead>
        <tbody>
          {facet.buckets.map((b) => (
            <tr key={String(b.valor)}>
              <td>{etiquetaValor(b.valor)}</td>
              <td className="num">{fmt(b.conteo)}</td>
              {cols.map((c) => <td key={c} className="num">{fmt(b.metricas?.[c])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function TablaBuckets({ facet }) {
  const filas = []
  facet.buckets.forEach((b) => {
    filas.push({ nivel: 0, valor: b.valor, conteo: b.conteo })
    b.hijos?.forEach((h) => filas.push({ nivel: 1, valor: h.valor, conteo: h.conteo }))
  })
  return (
    <table className="tabla">
      <thead><tr><th>Valor</th><th className="num">Registros</th></tr></thead>
      <tbody>
        {filas.map((f, i) => (
          <tr key={i} className={f.nivel ? 'hijo' : ''}>
            <td style={{ paddingLeft: 10 + f.nivel * 20 }}>{etiquetaValor(f.valor)}</td>
            <td className="num">{fmt(f.conteo)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export function Tarjetas({ metricas }) {
  const entradas = Object.entries(metricas || {}).filter(([, v]) => v != null)
  if (!entradas.length) return null
  return (
    <div className="tarjetas">
      {entradas.map(([k, v]) => (
        <div className="tarjeta" key={k}>
          <span className="etiqueta">{k === 'count' ? 'Registros' : k}</span>
          <span className="valor">{fmt(v)}</span>
        </div>
      ))}
    </div>
  )
}
