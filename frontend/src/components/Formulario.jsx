// Formulario dinámico construido a partir del catálogo de la API.

export default function Formulario({ campos, valores, opciones, onCambio, onEnviar, cargando }) {
  return (
    <form
      className="formulario"
      onSubmit={(e) => {
        e.preventDefault()
        onEnviar()
      }}
    >
      {campos.map((c) => (
        <label key={c.nombre} className={`campo campo-${c.tipo}`}>
          <span>{c.etiqueta}{c.opcional && <em> (opcional)</em>}</span>
          <Control campo={c} valor={valores[c.nombre]} opciones={opciones} onCambio={(v) => onCambio(c.nombre, v)} />
        </label>
      ))}
      <div className="acciones">
        <button type="submit" className="primario" disabled={cargando}>
          {cargando ? 'Consultando…' : 'Ejecutar consulta'}
        </button>
      </div>
    </form>
  )
}

function listaOpciones(campo, opciones) {
  if (campo.opciones) return campo.opciones
  return (opciones[campo.opciones_de] || []).map((v) => ({ valor: v, etiqueta: v }))
}

function Control({ campo, valor, opciones, onCambio }) {
  switch (campo.tipo) {
    case 'numero':
      return <input type="number" value={valor ?? ''} onChange={(e) => onCambio(e.target.value === '' ? '' : Number(e.target.value))} />
    case 'fecha':
      return <input type="date" value={valor ?? ''} onChange={(e) => onCambio(e.target.value)} />
    case 'seleccion': {
      const lista = listaOpciones(campo, opciones)
      // Si las opciones aún no cargan, se muestra el valor por defecto igual
      const incluye = !valor || lista.some((o) => o.valor === valor)
      return (
        <select value={valor ?? ''} onChange={(e) => onCambio(e.target.value)}>
          {campo.opcional && <option value="">— Cualquiera —</option>}
          {!incluye && <option value={valor}>{valor}</option>}
          {lista.map((o) => <option key={o.valor} value={o.valor}>{o.etiqueta}</option>)}
        </select>
      )
    }
    case 'multiseleccion': {
      const lista = listaOpciones(campo, opciones)
      const sel = new Set(valor || [])
      const todas = [...new Set([...lista.map((o) => o.valor), ...sel])]
      return (
        <div className="multiseleccion" role="group">
          {todas.map((v) => (
            <button
              type="button"
              key={v}
              aria-pressed={sel.has(v)}
              onClick={() => {
                const n = new Set(sel)
                n.has(v) ? n.delete(v) : n.add(v)
                onCambio([...n])
              }}
            >
              {v}
            </button>
          ))}
        </div>
      )
    }
    default:
      return <input type="text" value={valor ?? ''} onChange={(e) => onCambio(e.target.value)} />
  }
}
