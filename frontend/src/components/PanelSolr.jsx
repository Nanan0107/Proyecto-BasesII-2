import { useState } from 'react'

// Muestra exactamente qué parámetros se enviaron a Solr (útil para la defensa).
export default function PanelSolr({ resultado }) {
  const [copiado, setCopiado] = useState(false)
  if (!resultado?.solr_params) return null
  const copiar = async () => {
    try {
      await navigator.clipboard.writeText(resultado.solr_url)
      setCopiado(true)
      setTimeout(() => setCopiado(false), 1500)
    } catch { /* sin permiso de portapapeles */ }
  }
  return (
    <details className="panel-solr">
      <summary>Consulta enviada a Solr</summary>
      <pre className="codigo">{JSON.stringify(resultado.solr_params, null, 2)}</pre>
      <div className="url-solr">
        <code title={resultado.solr_url}>{decodeURIComponent(resultado.solr_url)}</code>
        <button type="button" onClick={copiar}>{copiado ? 'Copiada' : 'Copiar URL'}</button>
      </div>
    </details>
  )
}
