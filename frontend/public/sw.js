// Gestion MP PRO : service worker de l'application installée au téléphone (ARCHITECTURE § 10.4).
//
// Il ne garde que l'ENVELOPPE (la page, ses scripts, ses styles, ses icônes), jamais une donnée :
// un stock d'hier affiché comme celui d'aujourd'hui serait pire qu'un message « pas de réseau ».
// - /api/… : jamais intercepté, jamais gardé.
// - l'enveloppe : toujours demandée au réseau d'abord (une nouvelle version arrive sans rien
//   vider) ; la copie gardée ne sert que sans réseau, pour que l'écran s'ouvre et dise « Le
//   serveur ne répond pas » au lieu d'une page d'erreur du navigateur.
const ENVELOPPE = 'gestion-mp-pro-enveloppe-1'
const ACCUEIL = '/'

self.addEventListener('install', (evenement) => {
  evenement.waitUntil(
    caches
      .open(ENVELOPPE)
      .then((cache) => cache.add(ACCUEIL))
      .catch(() => undefined)
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (evenement) => {
  evenement.waitUntil(
    caches
      .keys()
      .then((cles) => Promise.all(cles.filter((c) => c !== ENVELOPPE).map((c) => caches.delete(c))))
      .then(() => self.clients.claim()),
  )
})

/** Ce qui fait partie de l'enveloppe : une page, ou un fichier statique du même site. */
function estEnveloppe(requete, adresse) {
  if (requete.method !== 'GET' || adresse.origin !== self.location.origin) return false
  if (adresse.pathname.startsWith('/api/') || adresse.pathname === '/api') return false
  return requete.mode === 'navigate' || /^\/(assets\/|icone|manifest\.webmanifest$)/.test(adresse.pathname)
}

self.addEventListener('fetch', (evenement) => {
  const requete = evenement.request
  const adresse = new URL(requete.url)
  if (!estEnveloppe(requete, adresse)) return
  const page = requete.mode === 'navigate'
  evenement.respondWith(
    fetch(requete)
      .then((reponse) => {
        if (reponse.ok) {
          const copie = reponse.clone()
          caches.open(ENVELOPPE).then((cache) => cache.put(page ? ACCUEIL : requete, copie))
        }
        return reponse
      })
      .catch(() =>
        caches.match(page ? ACCUEIL : requete).then((garde) => garde ?? Response.error()),
      ),
  )
})
