// Cliente de la API FastAPI. Todas las rutas pasan por el proxy de Vite (/api).

export class ErrorApi extends Error {
  constructor(status, detalle) {
    const mensaje = typeof detalle === 'string' ? detalle : detalle?.mensaje || JSON.stringify(detalle)
    super(mensaje)
    this.status = status
    this.pendiente = status === 501
    this.solrParams = detalle?.solr_params
  }
}

async function pedir(ruta, opciones = {}) {
  let r
  try {
    r = await fetch(ruta, {
      headers: { 'Content-Type': 'application/json' },
      ...opciones,
      body: opciones.body ? JSON.stringify(opciones.body) : undefined,
    })
  } catch {
    throw new ErrorApi(0, 'No se pudo conectar con la API (¿está corriendo el backend en el puerto 8000?)')
  }
  const datos = await r.json().catch(() => ({}))
  if (!r.ok) {
    let detalle = datos.detail ?? `HTTP ${r.status}`
    if (Array.isArray(detalle)) detalle = detalle.map((d) => d.msg).join('; ')
    throw new ErrorApi(r.status, detalle)
  }
  return datos
}

export const api = {
  estado: () => pedir('/api/estado'),
  catalogo: () => pedir('/api/catalogo'),
  opciones: () => pedir('/api/opciones'),
  consulta: (id, parametros, pagina = 0, filas = 20) =>
    pedir(`/api/consultas/${id}`, { method: 'POST', body: { parametros, pagina, filas } }),
  puntos: (orden, filas) => {
    const qs = new URLSearchParams({ filas })
    if (orden) qs.set('orden', orden)
    return pedir(`/api/mapa/puntos?${qs}`)
  },
  proximidad: (cuerpo) => pedir('/api/geo/proximidad', { method: 'POST', body: cuerpo }),
  poligono: (cuerpo) => pedir('/api/geo/poligono', { method: 'POST', body: cuerpo }),
  poligonoFacets: (cuerpo) => pedir('/api/geo/poligono-facets', { method: 'POST', body: cuerpo }),
}
