/** Une valeur qui ne suit la frappe qu'après une courte pause (une recherche au serveur par mot, pas par lettre). */
import { useEffect, useState } from 'react'

export function useDiffere<T>(valeur: T, delai = 300): T {
  const [differee, setDifferee] = useState(valeur)
  useEffect(() => {
    const minuterie = setTimeout(() => setDifferee(valeur), delai)
    return () => clearTimeout(minuterie)
  }, [valeur, delai])
  return differee
}
