import { useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import Formulario from '../components/Formulario.jsx'
import Resultado from '../components/Resultado.jsx'

const FILAS = 20

export default function VistaConsultas({ catalogo, opciones, onAbrirMapa }) {
  const [seleccionada, setSeleccionada] = useState(catalogo.consultas[0].id)
  const consulta = useMemo(() => catalogo.consultas.find((c) => c.id === seleccionada), [catalogo, seleccionada])

  return (
    <div className="vista-consultas">
      <aside className="menu-consultas" aria-label="Consultas disponibles">
        {catalogo.grupos.map((g) => (
          <section key={g.id}>
            <h2>{g.titulo}</h2>
            <ul>
              {catalogo.consultas.filter((c) => c.grupo === g.id).map((c) => (
                <li key={c.id}>
                  <button
                    className={c.id === seleccionada ? 'activa' : ''}
                    onClick={() => (c.modo_mapa ? onAbrirMapa(c.modo_mapa) : setSeleccionada(c.id))}
                  >
                    <span className="num">{c.id}</span>
                    <span className="titulo">{c.titulo}</span>
                    {c.modo_mapa && <span className="ir-mapa" title="Se abre en el mapa">↗</span>}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </aside>
      <PanelConsulta key={consulta.id} consulta={consulta} opciones={opciones} />
    </div>
  )
}

function PanelConsulta({ consulta, opciones }) {
  const inicial = Object.fromEntries(consulta.formulario.map((c) => [c.nombre, c.por_defecto ?? '']))
  const [valores, setValores] = useState(inicial)
  const [pagina, setPagina] = useState(0)
  const [resultado, setResultado] = useState(null)
  const [error, setError] = useState(null)
  const [cargando, setCargando] = useState(false)

  const ejecutar = async (pag = 0) => {
    setCargando(true)
    setError(null)
    try {
      const r = await api.consulta(consulta.id, valores, pag, FILAS)
      setResultado(r)
      setPagina(pag)
    } catch (e) {
      setResultado(null)
      setError(e)
    } finally {
      setCargando(false)
    }
  }

  // Ejecutar al abrir con los valores por defecto
  useEffect(() => { ejecutar(0) }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className="panel-consulta">
      <header>
        <div className="etiquetas">
          <span className="chip">Consulta {consulta.id}</span>
          <span className="chip suave">{consulta.requisito}</span>
        </div>
        <h2>{consulta.titulo}</h2>
        <p className="descripcion">{consulta.descripcion}</p>
      </header>

      <Formulario
        campos={consulta.formulario}
        valores={valores}
        opciones={opciones}
        onCambio={(nombre, v) => setValores((s) => ({ ...s, [nombre]: v }))}
        onEnviar={() => ejecutar(0)}
        cargando={cargando}
      />

      {error && (
        <div className={`aviso ${error.pendiente ? 'pendiente' : 'error'}`}>
          {error.pendiente ? (
            <>
              <strong>Pendiente de implementar.</strong> Esta consulta todavía no está escrita en
              <code>backend/app/consultas/convencionales.py</code>. Siga la guía en <code>docs/guia-solr.md</code>.
            </>
          ) : (
            <>
              <strong>Error:</strong> {error.message}
              {error.solrParams && <pre className="codigo">{JSON.stringify(error.solrParams, null, 2)}</pre>}
            </>
          )}
        </div>
      )}

      {resultado && (
        <Resultado
          resultado={resultado}
          visualizacion={consulta.visualizacion}
          pagina={pagina}
          filas={FILAS}
          onPagina={ejecutar}
          cargando={cargando}
        />
      )}
    </section>
  )
}
