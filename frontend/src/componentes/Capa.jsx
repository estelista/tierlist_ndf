import { useState } from 'react'
import { poster } from '../textos.js'

/** Pôster de um título. Sem pôster, mostra o nome no lugar. */
export default function Capa({ titulo, url, grande = false, alt = titulo }) {
  const [quebrada, setQuebrada] = useState(null)
  if (!url || quebrada === url) {
    return <span className="capa capa-vazia">{titulo}</span>
  }
  return (
    <img
      className="capa"
      src={poster(url, grande ? 'w500' : 'w342')}
      srcSet={grande ? undefined : `${poster(url, 'w185')} 185w, ${poster(url, 'w342')} 342w`}
      sizes={grande ? undefined : '120px'}
      alt={alt}
      width="342"
      height="513"
      loading={grande ? 'eager' : 'lazy'}
      onError={() => setQuebrada(url)}
    />
  )
}
