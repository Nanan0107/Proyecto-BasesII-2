import GraficoFacet, { Tarjetas, etiquetaValor } from './Graficos.jsx'
import PanelSolr from './PanelSolr.jsx'

// Columnas preferidas para la tabla de documentos (en este orden)
const COLUMNAS = [
  ['nombre_cientifico', 'Nombre científico'], ['orden', 'Orden'], ['familia', 'Familia'],
  ['area_protegida', 'Área protegida'], ['categoria_manejo', 'Categoría'], ['area_conservacion', 'AC'],
  ['provincia', 'Provincia'], ['elevacion_m', 'Elevación (m)'], ['fecha_evento', 'Fecha'],
  ['etapa_vida', 'Etapa'], ['estacion', 'Estación'], ['dist', 'Distancia (km)'],
]

export default function Resultado({ resultado, visualizacion, pagina, filas, onPagina, cargando }) {
  const { numFound, docs, facets, stats, qtime } = resultado
  const totalPaginas = Math.ceil(numFound / filas)

  return (
    <div className={`resultado ${cargando ? 'cargando' : ''}`}>
      <div className="resumen">
        <div className="total"><span className="valor">{numFound.toLocaleString('es-CR')}</span> registros encontrados</div>
        {qtime != null && <div className="nota">Solr respondió en {qtime} ms</div>}
      </div>

      {facets.map((f) => <GraficoFacet key={f.nombre + f.tipo} facet={f} visualizacion={visualizacion} />)}

      {Object.entries(stats || {}).map(([campo, m]) => (
        <div key={campo}><h3 className="subtitulo">Estadísticas de {campo}</h3><Tarjetas metricas={m} /></div>
      ))}

      {docs.length > 0 && (
        <>
          <TablaDocs docs={docs} />
          {totalPaginas > 1 && (
            <div className="paginacion">
              <button disabled={pagina === 0 || cargando} onClick={() => onPagina(pagina - 1)}>‹ Anterior</button>
              <span>Página {pagina + 1} de {totalPaginas.toLocaleString('es-CR')}</span>
              <button disabled={pagina + 1 >= totalPaginas || cargando} onClick={() => onPagina(pagina + 1)}>Siguiente ›</button>
            </div>
          )}
        </>
      )}

      <PanelSolr resultado={resultado} />
    </div>
  )
}

export function TablaDocs({ docs, max }) {
  const presentes = new Set(docs.flatMap((d) => Object.keys(d)))
  const cols = COLUMNAS.filter(([c]) => presentes.has(c))
  const lista = max ? docs.slice(0, max) : docs
  return (
    <div className="tabla-scroll">
      <table className="tabla">
        <thead><tr>{cols.map(([c, e]) => <th key={c} className={c === 'elevacion_m' || c === 'dist' ? 'num' : ''}>{e}</th>)}</tr></thead>
        <tbody>
          {lista.map((d) => (
            <tr key={d.id}>
              {cols.map(([c]) => (
                <td key={c} className={c === 'elevacion_m' || c === 'dist' ? 'num' : c === 'nombre_cientifico' ? 'cientifico' : ''}>
                  {d[c] == null ? '—' : etiquetaValor(d[c])}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
