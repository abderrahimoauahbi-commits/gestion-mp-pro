// Tournée d'écran du stress test « 10 ans » de Gestion MP PRO (épreuve d'écran).
//
// Pilote un Chrome sans tête (SON profil, SON port CDP — jamais le panneau partagé) sur un serveur
// jetable, et parcourt par de vraies navigations TOUS les écrans et TOUS les onglets ouverts à
// chaque rôle (direction, achats, alimentation), au bureau (1 440 × 900) et au téléphone
// (375 × 812, tactile : l'atelier, et le bureau de l'alimentation). Pour chaque écran il relève :
//   - le temps jusqu'à l'affichage (navigation → roue disparue, texte présent, plus aucun appel
//     /api/ en vol), et l'appel /api/ le plus lent de l'écran (route, durée, octets) ;
//   - les réponses 4xx/5xx inattendues, les erreurs JavaScript, l'écran d'erreur, la page vide ;
//   - les tableaux : lignes dans le DOM, pagination (« n lignes chargées sur N »), tableau plus
//     large que son cadre (barre horizontale, invisible sur Mac), cellules dont le texte est coupé ;
//   - dans une fenêtre : tout élément qui défile pour lui-même (défilement caché) ;
//   - le défilement horizontal de la page et les éléments qui débordent ;
//   - chez l'alimentation : tout montant, prix, cours (balayage du texte rendu) ;
//   - la recherche : frappe d'un mot tiré de la base dans le champ de la liste → temps jusqu'au
//     calme réseau, lignes restantes ; la recherche globale de la coque ;
//   - chaque export Excel et chaque document (bon, bilan, feuille de comptage, étiquettes) vu sur
//     l'écran : lancé par `fetch` dans la page (même session), chronométré, taille et statut.
// Une capture PNG est prise pour chaque écran qui a une anomalie ou dépasse 1 s.
//
// Usage : node tournee_ecran.mjs <base_url> <codes.json> <contexte.json> <dossier_captures>
//                                <profil_chrome> <port_cdp> <resultat.json>
// Env  : TOURNEE_ROLES="direction,achats" (filtre), TOURNEE_SANS_ONGLETS=1 (écrans de base seuls).

import { spawn } from 'node:child_process'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'

const [BASE, FICHIER_CODES, FICHIER_CONTEXTE, CAPTURES, PROFIL, PORT_CDP_TXT, SORTIE] = process.argv.slice(2)
const CODES = JSON.parse(readFileSync(FICHIER_CODES, 'utf8'))
const CTX = JSON.parse(readFileSync(FICHIER_CONTEXTE, 'utf8'))
const PORT_CDP = Number(PORT_CDP_TXT ?? 9381)
mkdirSync(CAPTURES, { recursive: true })
const CHROME = process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
const FILTRE = (process.env.TOURNEE_ROLES ?? '').split(',').filter(Boolean)
const SANS_ONGLETS = process.env.TOURNEE_SANS_ONGLETS === '1'
// TOURNEE_ECRANS="/receptions,/operations" : seulement les écrans du bureau dont le chemin commence ainsi.
const FILTRE_ECRANS = (process.env.TOURNEE_ECRANS ?? '').split(',').filter(Boolean)
const SEUIL_LENT_MS = 1000
const SEUIL_BLOQUANT_MS = 3000
const DELAI_ECRAN_MS = 30000

const ID = CTX.ids
const avec = (v) => v != null
const fiche = (chemin, cle) => (avec(ID[cle]) ? [chemin.replace(':id', String(ID[cle]))] : [])

// --- Écrans et onglets, repris de frontend/src/pages/*/ecrans.ts (registre unique). ---
const ECRANS = [
  { ch: '/cockpit', roles: ['direction'], onglets: ['faire', 'alertes', 'ensemble', 'evolution', 'economies'] },
  { ch: '/accueil', roles: ['achats', 'alimentation'] },
  { ch: '/stock', roles: ['direction', 'achats', 'alimentation'], onglets: ['matieres', 'lots', 'mouvements', 'ordres', 'a-valider'] },
  ...fiche('/stock/matieres/:id', 'matiere').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'] })),
  ...fiche('/lots/:id', 'lot').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'] })),
  ...(avec(ID.lot) ? [{ ch: `/tracabilite?lot=${ID.lot}`, roles: ['direction', 'achats', 'alimentation'] }] : []),
  ...(avec(ID.matiere) ? [{ ch: `/tracabilite?matiere=${ID.matiere}`, roles: ['direction', 'achats', 'alimentation'] }] : []),
  { ch: '/sorties', roles: ['direction', 'achats', 'alimentation'], onglets: ['valide', 'brouillon', 'annule'] },
  { ch: '/ordres/nouveau', roles: ['direction', 'alimentation'] },
  ...fiche('/ordres/:id', 'ordre').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'] })),
  ...fiche('/ordres/:id/retour', 'ordre').map((ch) => ({ ch, roles: ['direction', 'alimentation'] })),
  { ch: '/production', roles: ['direction', 'achats', 'alimentation'], onglets: ['plan', 'glissant', 'realise', 'besoins'] },
  ...fiche('/production/besoins/:id', 'matiere').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'] })),
  { ch: '/plan-achat', roles: ['direction', 'achats'], onglets: ['fournisseurs', 'references'] },
  ...fiche('/plan-achat/preparer/:id', 'fournisseur').map((ch) => ({ ch, roles: ['direction', 'achats'] })),
  { ch: '/commandes', roles: ['direction', 'achats'], onglets: ['brouillon', 'a_approuver', 'envoyee', 'confirmee', 'clos'] },
  { ch: '/commandes/nouvelle', roles: ['direction', 'achats'] },
  ...fiche('/commandes/:id', 'commande').map((ch) => ({ ch, roles: ['direction', 'achats'], onglets: ['lignes', 'prix', 'expedition', 'receptions', 'approbation', 'pieces', 'historique'] })),
  { ch: '/receptions', roles: ['direction', 'achats'], onglets: ['brouillon', 'validee', 'annulee', 'reclamations', 'bobines', 'pesees'] },
  { ch: '/receptions/nouvelle', roles: ['direction', 'achats'] },
  ...fiche('/receptions/:id', 'reception').map((ch) => ({ ch, roles: ['direction', 'achats'], onglets: ['lignes', 'reclamations', 'pieces', 'historique'] })),
  { ch: '/reclamations/nouvelle', roles: ['direction', 'achats'] },
  ...fiche('/reclamations/:id', 'reclamation').map((ch) => ({ ch, roles: ['direction', 'achats'], onglets: ['reponse', 'pieces', 'historique'] })),
  { ch: '/importations', roles: ['direction', 'achats'], onglets: ['ouverts', 'clos', 'rattacher'] },
  { ch: '/dossiers/nouveau', roles: ['direction', 'achats'], onglets: ['facture', 'main'] },
  ...fiche('/dossiers/:id', 'dossier').map((ch) => ({ ch, roles: ['direction', 'achats'], onglets: ['familles', 'marchandises', 'frais', 'echeancier', 'pieces', 'facture', 'historique'] })),
  { ch: '/inventaire', roles: ['direction', 'achats'], onglets: ['cours', 'passes'] },
  { ch: '/inventaires/nouveau', roles: ['direction', 'achats'] },
  ...fiche('/inventaires/:id', 'inventaire').map((ch) => ({ ch, roles: ['direction', 'achats'], onglets: ['lots', 'pieces', 'historique'] })),
  { ch: '/operations', roles: ['direction', 'achats', 'alimentation'], onglets: ['transfert', 'retour_machine', { o: 'ouverture', roles: ['direction', 'achats'] }, { o: 'ajustement', roles: ['direction', 'achats'] }, { o: 'retour_fournisseur', roles: ['direction', 'achats'] }] },
  { ch: '/operations/nouvelle?type=transfert', roles: ['direction', 'achats', 'alimentation'] },
  { ch: '/operations/nouvelle?type=ajustement', roles: ['direction', 'achats'] },
  ...fiche('/operations/:id', 'operation').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'] })),
  { ch: '/catalogue', roles: ['direction', 'achats', 'alimentation'], onglets: ['matieres', { o: 'classification', roles: ['direction', 'achats'] }, { o: 'fournisseurs', roles: ['direction', 'achats'] }] },
  { ch: '/catalogue/tableur', roles: ['direction', 'achats'] },
  { ch: '/matieres/nouvelle', roles: ['direction', 'achats'] },
  ...fiche('/matieres/:id', 'matiere').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'], onglets: ['classification', 'conditionnement', 'historique', { o: 'achat', roles: ['direction', 'achats'] }, { o: 'pieces', roles: ['direction', 'achats'] }] })),
  { ch: '/fournisseurs/nouveau', roles: ['direction', 'achats'] },
  ...fiche('/fournisseurs/:id', 'fournisseur').map((ch) => ({ ch, roles: ['direction', 'achats'], onglets: ['fiche', 'pieces', 'historique'] })),
  { ch: '/qualites', roles: ['direction', 'achats', 'alimentation'], onglets: ['qualites', 'nomenclature'] },
  { ch: '/qualites/nouvelle', roles: ['direction'] },
  ...fiche('/qualites/:id', 'qualite').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'], onglets: ['recette', 'plan', 'versions', 'historique'] })),
  { ch: '/metiers', roles: ['direction', 'achats', 'alimentation'] },
  { ch: '/metiers/nouveau', roles: ['direction'] },
  ...fiche('/metiers/:id', 'metier').map((ch) => ({ ch, roles: ['direction', 'achats', 'alimentation'], onglets: ['fils', 'reglages', 'historique'] })),
  { ch: '/analyse', roles: ['direction', 'achats'], onglets: ['valorisation', 'matrice', 'historique', 'opportunites', 'fournisseurs', 'revient', 'echeancier', 'controles', 'production'] },
  { ch: '/reglages', roles: ['direction', 'achats'], onglets: ['parametres', 'devises', 'magasins', 'postes', 'codes', 'periode'] },
  { ch: '/administration', roles: ['direction'], onglets: ['comptes', 'appareils', 'sauvegardes', 'journal', 'courriel', 'serveur', 'telephone', 'technique', 'reprise', 'donnees'] },
  { ch: '/aide', roles: ['direction', 'achats', 'alimentation'], onglets: ['regles', 'roles', 'pas', 'calculs', 'analyse', 'ecrans', 'telephone'] },
  { ch: '/compte', roles: ['direction', 'achats', 'alimentation'] },
]

const ATELIER = [
  { ch: '/atelier' },
  { ch: '/atelier/envoyer' },
  { ch: '/atelier/ordres' },
  ...fiche('/atelier/ordres/:id', 'ordre').map((ch) => ({ ch })),
  { ch: '/atelier/retour' },
  { ch: '/atelier/chercher' },
  ...fiche('/atelier/lots/:id', 'lot').map((ch) => ({ ch })),
  { ch: '/atelier/deplacer' },
  { ch: '/atelier/montage' },
  { ch: '/atelier/signaler' },
]

// Le mot tapé dans la recherche d'une liste, selon l'écran.
const MOTS = CTX.mots
function motPour(url) {
  if (url.startsWith('/commandes') || url.startsWith('/plan-achat')) return MOTS.fournisseur || MOTS.defaut
  if (url.startsWith('/receptions')) return MOTS.fournisseur || MOTS.defaut
  if (url.startsWith('/stock?onglet=lots') || url.startsWith('/atelier/chercher')) return MOTS.lot || MOTS.defaut
  if (url.startsWith('/catalogue?onglet=fournisseurs')) return MOTS.fournisseur || MOTS.defaut
  return MOTS.defaut
}

// Un MONTANT réel, interdit à l'alimentation partout (A4, § 11.2).
const RE_AMOUNT = /(\d[\d  .,]*\s?(?:MAD|USD|EUR|DH|Dhs|DHS)\b)|(?:\b(?:MAD|USD|EUR)\b\s?\d)|[€$£]\s?\d|\d\s?[€$£]|[€$£]/i
const RE_LABEL = /\b(prix|montant|valoris[ée]|valorisation|budget|cmup|coût de revient|conseil d'achat|à commander pour)\b/i
const ECRAN_EXPLICATIF = (url) => url.startsWith('/aide') || url.startsWith('/compte')

// --- Pilote CDP minimal (un seul onglet). ---
const attendre = (ms) => new Promise((r) => setTimeout(r, ms))
const chrome = spawn(
  CHROME,
  ['--headless=new', `--remote-debugging-port=${PORT_CDP}`, `--user-data-dir=${PROFIL}`, '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--disable-gpu', 'about:blank'],
  { stdio: 'ignore' },
)
let cibles
for (let i = 0; i < 100; i++) {
  try {
    cibles = await (await fetch(`http://127.0.0.1:${PORT_CDP}/json`)).json()
    if (cibles.find((c) => c.type === 'page')) break
  } catch {
    /* pas encore prêt */
  }
  await attendre(200)
}
const page = cibles?.find((c) => c.type === 'page')
if (!page) {
  console.error('ARRÊT : Chrome ne répond pas sur le port CDP.')
  chrome.kill()
  process.exit(2)
}
const ws = new WebSocket(page.webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r))
let n = 0
const attente = new Map()
const jsErreurs = []
const reseau = new Map() // requestId → { url, debut, fin, statut, octets }
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data)
  if (m.id && attente.has(m.id)) {
    attente.get(m.id)(m)
    attente.delete(m.id)
  }
  if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error')
    jsErreurs.push(m.params.args.map((a) => a.value ?? a.description ?? a.type).join(' ').slice(0, 200))
  if (m.method === 'Runtime.exceptionThrown')
    jsErreurs.push((m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 200))
  if (m.method === 'Network.requestWillBeSent' && m.params.request.url.includes('/api/'))
    reseau.set(m.params.requestId, { url: m.params.request.url.replace(BASE, ''), debut: m.params.timestamp, fin: null, statut: 0, octets: 0 })
  if (m.method === 'Network.responseReceived' && reseau.has(m.params.requestId))
    reseau.get(m.params.requestId).statut = m.params.response.status
  if (m.method === 'Network.loadingFinished' && reseau.has(m.params.requestId)) {
    const r = reseau.get(m.params.requestId)
    r.fin = m.params.timestamp
    r.octets = m.params.encodedDataLength
  }
  if (m.method === 'Network.loadingFailed' && reseau.has(m.params.requestId)) {
    // Un appel annulé par la page elle-même (changement de critères) n'est ni en vol ni une faute.
    const r = reseau.get(m.params.requestId)
    r.fin = m.params.timestamp
    r.statut = m.params.canceled ? 'annulé' : r.statut || 'échec'
  }
  if (m.method === 'Page.javascriptDialogOpening') cdp('Page.handleJavaScriptDialog', { accept: true })
})
const cdp = (method, params = {}) =>
  new Promise((r) => {
    const id = ++n
    attente.set(id, r)
    ws.send(JSON.stringify({ id, method, params }))
  })
const evaluer = async (expr) => {
  const r = await cdp('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true })
  return r.result?.result?.value ?? r.result?.exceptionDetails?.exception?.description
}
await cdp('Page.enable')
await cdp('Runtime.enable')
await cdp('Network.enable')
await cdp('Log.enable')

async function taille(w, h, tactile) {
  await cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: !!tactile, screenWidth: w, screenHeight: h })
  await cdp('Emulation.setTouchEmulationEnabled', { enabled: !!tactile, maxTouchPoints: tactile ? 5 : 0 })
}
async function connecter(role) {
  await cdp('Page.navigate', { url: `${BASE}/connexion` })
  await attendre(800)
  const ident = `stress-ecran-${role}`
  const statut = await evaluer(
    `fetch('/api/deconnexion',{method:'POST',headers:{'Content-Type':'application/json','X-Gestion-MP-PRO':'1'}}).catch(()=>0).then(()=>fetch('/api/connexion',{method:'POST',headers:{'Content-Type':'application/json','X-Gestion-MP-PRO':'1'},body:JSON.stringify({identifiant:${JSON.stringify(ident)},code:${JSON.stringify(CODES[ident])}})})).then(r=>r.status).catch((e)=>'REJET '+e.message)`,
  )
  if (statut !== 200) {
    console.error(`ARRÊT : connexion ${role} = ${statut} (le serveur est-il joignable ?).`)
    ws.close()
    chrome.kill()
    process.exit(2)
  }
}

// L'état du DOM après chargement : tableaux, fenêtres, débordements, exports, texte.
const ANALYSE = `(()=>{
  const d=document.documentElement;
  const racine=document.querySelector('main')??document.querySelector('[data-atelier]')??document.body;
  const txt=(racine.innerText||'').trim();
  const desc=(e)=>e.tagName.toLowerCase()+(typeof e.className==='string'&&e.className?'.'+e.className.split(' ')[0]:'')+(e.getAttribute('aria-label')?'['+e.getAttribute('aria-label')+']':'');
  const defile=(e)=>{const s=getComputedStyle(e);return /(auto|scroll)/.test(s.overflowY+s.overflowX)};
  const larges=[...document.querySelectorAll('body *')]
    .filter(e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return r.right>innerWidth+1 && s.position!=='fixed' && s.overflow!=='hidden' && r.width>0})
    .slice(0,6).map(desc);
  const tableaux=[...document.querySelectorAll('table')].map(t=>{
    let cadre=t.parentElement; while(cadre&&cadre!==document.body&&!defile(cadre)) cadre=cadre.parentElement; if(cadre&&cadre.parentElement&&cadre.parentElement.getAttribute('role')==='dialog') cadre=null;
    const enFenetre=!!t.closest('[role=dialog]');
    const boite=t.closest('[class*=dataTable]')??t.parentElement;
    const compteur=boite?.querySelector('[class*=compteur]')?.innerText?.trim()??'';
    const charger=boite?.querySelector('[class*=chargerPlus]')?.innerText?.replace(/\\s+/g,' ').trim()??'';
    const lignes=t.querySelectorAll('tbody tr').length;
    const cellules=[...t.querySelectorAll('tbody tr')].slice(0,150).flatMap(tr=>[...tr.children]);
    const coupees=cellules.filter(c=>c.scrollWidth>c.clientWidth+2&&getComputedStyle(c).overflow==='hidden').length;
    const cw=cadre&&cadre!==document.body?cadre.clientWidth:innerWidth;
    return {libelle:(t.getAttribute('aria-label')||t.querySelector('caption')?.innerText||'').slice(0,60), lignes, colonnes:t.querySelectorAll('thead th').length,
      compteur, charger, enFenetre, hauteurCadre: cadre&&cadre!==document.body?cadre.clientHeight:null,
      defileInterne: !!(cadre&&cadre!==document.body&&cadre.scrollHeight>cadre.clientHeight+1),
      debordeLargeur: t.scrollWidth>cw+1 ? t.scrollWidth+'>'+cw : '', coupees};
  });
  const fenetres=[...document.querySelectorAll('[role=dialog]')].map(f=>{
    const corps=f.querySelector('[class*=corps]');
    const caches=[...f.querySelectorAll('*')].filter(e=>e!==corps&&!e.classList.contains('masque-accessible')&&defile(e)&&e.scrollHeight>e.clientHeight+1&&e.clientHeight>0).map(e=>desc(e)+' '+e.scrollHeight+'/'+e.clientHeight);
    const ecrases=[...f.querySelectorAll('*')].filter(e=>e!==corps&&!e.classList.contains('masque-accessible')&&e.clientHeight>1&&getComputedStyle(e).overflow==='hidden'&&e.scrollHeight>e.clientHeight+2&&e.clientHeight>0&&e.clientHeight<40&&(e.innerText||'').trim().length>0&&!e.closest('td,th')).slice(0,4).map(e=>desc(e)+' '+e.scrollHeight+'/'+e.clientHeight);
    return {titre:(f.querySelector('h2')?.innerText||'').slice(0,60), caches, ecrases, haut:f.scrollHeight>innerHeight};
  });
  const exports=[...document.querySelectorAll('a[href*="/api/export/"]')].map(a=>({href:a.getAttribute('href'),libelle:(a.innerText||a.title||'').trim().slice(0,50)}));
  const documents=[...document.querySelectorAll('a[href*="/api/documents/"]')].map(a=>({href:a.getAttribute('href'),libelle:(a.innerText||a.title||'').trim().slice(0,50)}));
  const recherche=[...document.querySelectorAll('main input[type=search]')].filter(i=>!i.closest('[role=dialog]')&&!i.closest('[role=combobox]')&&i.getAttribute('role')!=='combobox'&&i.getBoundingClientRect().width>0).map(i=>i.getAttribute('aria-label')||'');
  const rechercheFenetre=[...document.querySelectorAll('[role=dialog] input[type=search]')].map(i=>i.getAttribute('aria-label')||'');
  const bandeau=[...document.querySelectorAll('[role=alert]')].map(e=>(e.innerText||'').trim()).join(' | ');
  return {final:location.pathname+location.search, vide:txt.length<2, spinner:!!document.querySelector('[role=status] [class*=roue]'),
    largeurPage:d.scrollWidth+'/'+d.clientWidth, debordeH:d.scrollWidth>d.clientWidth+1, debordent:larges, tableaux, fenetres, exports, documents,
    recherche, rechercheFenetre, bandeau, erreurUI:/La lecture a échoué|Pas de réseau|Une erreur est survenue|went wrong/.test(document.body.innerText),
    texte:txt.slice(0,200000)};
})()`

// Attend le calme : roue disparue, texte présent, aucun appel /api/ en vol (puis 250 ms sans nouvel appel).
async function attendreCalme(t0, delai = DELAI_ECRAN_MS) {
  let pret = null
  while (performance.now() - t0 < delai) {
    const enVol = [...reseau.values()].some((r) => r.fin === null)
    const dom = await evaluer(`(()=>{const m=document.querySelector('main')??document.querySelector('[data-atelier]');return {roue:!!document.querySelector('[role=status] [class*=roue]'), texte:!!(m&&m.innerText.trim().length>1)}})()`)
    const calme = !enVol && dom && !dom.roue && dom.texte
    if (calme) {
      if (pret === null) pret = performance.now()
      else if (performance.now() - pret >= 250) return pret - t0
    } else pret = null
    await attendre(40)
  }
  // Chargement bloqué (délai) : on note pourquoi (appels en vol, roue, texte absent).
  const enVol = [...reseau.values()].filter((r) => r.fin === null).map((r) => r.url)
  const dom = await evaluer(`(()=>{const m=document.querySelector('main')??document.querySelector('[data-atelier]');return {roue:!!document.querySelector('[role=status] [class*=roue]'), texte:!!(m&&m.innerText.trim().length>1)}})()`)
  derniereRaison = `en vol : ${enVol.slice(0, 4).join(', ') || 'aucun'} ; roue : ${dom?.roue} ; texte : ${dom?.texte}`
  return null
}
let derniereRaison = ''

async function ouvrir(url, { tactile } = {}) {
  jsErreurs.length = 0
  reseau.clear()
  const t0 = performance.now()
  await cdp('Page.navigate', { url: BASE + url })
  await attendre(120)
  const tAffiche = await attendreCalme(t0)
  await attendre(tactile ? 300 : 150)
  const info = await evaluer(ANALYSE)
  const appels = [...reseau.values()].filter((r) => !/\/api\/(connexion|deconnexion)$/.test(r.url))
  const durees = appels.filter((r) => r.fin !== null && r.statut !== 'annulé').map((r) => ({ url: r.url, ms: Math.round((r.fin - r.debut) * 1000), statut: r.statut, octets: r.octets }))
  const lent = durees.reduce((a, r) => (a === null || r.ms > a.ms ? r : a), null)
  const fautes = appels.filter((r) => r.statut >= 400 || r.statut === 'échec').map((r) => `${r.statut} ${r.url}`)
  return { ...(info ?? { vide: true, final: url, tableaux: [], fenetres: [], exports: [], documents: [], recherche: [], texte: '' }), tAffiche: tAffiche === null ? null : Math.round(tAffiche), apiLente: lent, nbApi: appels.length, octets: durees.reduce((a, r) => a + r.octets, 0), api: fautes, js: [...jsErreurs] }
}

function problemes(url, role, r) {
  const pbs = []
  if (r.api.length) pbs.push('api: ' + r.api.join(', '))
  if (r.js.length) pbs.push('js: ' + r.js.join(' ; '))
  if (r.erreurUI) pbs.push('écran d’erreur')
  if (r.vide) pbs.push('page vide')
  if (r.tAffiche === null) pbs.push(`chargement bloqué (> ${DELAI_ECRAN_MS / 1000} s) — ${derniereRaison}`)
  else if (r.tAffiche > SEUIL_BLOQUANT_MS) pbs.push(`BLOQUANT ${r.tAffiche} ms`)
  else if (r.tAffiche > SEUIL_LENT_MS) pbs.push(`lent ${r.tAffiche} ms`)
  if (r.debordeH) pbs.push(`défilement horizontal ${r.largeurPage}` + (r.debordent?.length ? ' — ' + r.debordent.join(', ') : ''))
  for (const t of r.tableaux ?? []) {
    if (t.lignes >= 1000 && !t.charger) pbs.push(`tableau sans pagination : ${t.lignes} lignes dans le DOM (${t.libelle || t.compteur})`)
    if (t.debordeLargeur) pbs.push(`tableau plus large que son cadre ${t.debordeLargeur} (${t.libelle || t.compteur || t.colonnes + ' col.'})`)
    if (t.coupees >= 3) pbs.push(`${t.coupees} cellule(s) au texte coupé (${t.libelle || t.compteur})`)
    if (t.enFenetre && t.defileInterne) pbs.push(`tableau qui défile dans une fenêtre (${t.lignes} lignes, cadre ${t.hauteurCadre} px)`)
  }
  for (const f of r.fenetres ?? []) {
    if (f.caches?.length) pbs.push(`défilement caché dans la fenêtre « ${f.titre} » : ${f.caches.slice(0, 3).join(' ; ')}`)
    if (f.ecrases?.length) pbs.push(`écrasé dans la fenêtre « ${f.titre} » : ${f.ecrases.slice(0, 2).join(' ; ')}`)
  }
  if (role === 'alimentation') {
    const re = ECRAN_EXPLICATIF(url) ? RE_AMOUNT : new RegExp(`${RE_AMOUNT.source}|${RE_LABEL.source}`, 'i')
    const m = (r.texte || '').match(re)
    if (m) {
      const i = Math.max(0, m.index - 35)
      pbs.push(`MONTANT CHEZ ALIMENTATION : …${(r.texte || '').slice(i, m.index + 45).replace(/\s+/g, ' ')}…`)
    }
  }
  return pbs
}

// Frappe un mot dans le premier champ de recherche de la page ; mesure le temps jusqu'au calme.
async function chercher(url) {
  const mot = motPour(url)
  const ok = await evaluer(`(()=>{const i=[...document.querySelectorAll('main input[type=search]')].find(i=>!i.closest('[role=dialog]')&&i.getAttribute('role')!=='combobox'&&i.getBoundingClientRect().width>0);if(!i)return false;i.focus();return true})()`)
  if (!ok) return null
  const avant = await evaluer(`[...document.querySelectorAll('table tbody tr')].length`)
  reseau.clear()
  const t0 = performance.now()
  await cdp('Input.insertText', { text: mot })
  await attendre(100)
  const t = await attendreCalme(t0, 15000)
  const apres = await evaluer(`(()=>{const c=document.querySelector('[class*=compteur]');return {lignes:[...document.querySelectorAll('table tbody tr')].length, compteur:c?c.innerText.trim():''}})()`)
  const appels = [...reseau.values()].filter((r) => r.fin !== null)
  const lent = appels.reduce((a, r) => (a === null || r.fin - r.debut > a.fin - a.debut ? r : a), null)
  return { mot, ms: t === null ? null : Math.round(t), avant, apres: apres?.lignes, compteur: apres?.compteur, serveur: appels.some((r) => /[?&]q=/.test(r.url)), apiMs: lent ? Math.round((lent.fin - lent.debut) * 1000) : null }
}

// Lance un export ou un document depuis la page (même session) et le chronomètre.
// Un même lien n'est lancé qu'une fois par rôle ; une même route (sans ses paramètres ni ses
// identifiants) au plus trois fois par rôle et par écran (une liste met un bouton « Étiquettes »
// sur chacune de ses 500 lignes).
const DEJA = new Set()
const PAR_ROUTE = new Map()
async function telecharger(role, href, libelle, genre, ecran) {
  const cle = `${role} ${href}`
  if (DEJA.has(cle)) return null
  DEJA.add(cle)
  const route = `${role} ${ecran} ${href.split('?')[0].replace(/\/\d+(?=\/|$)/g, '/N')}`
  const vus = (PAR_ROUTE.get(route) ?? 0) + 1
  PAR_ROUTE.set(route, vus)
  if (vus > 3) return null
  const r = await evaluer(`(async()=>{const t0=performance.now();const ac=new AbortController();const to=setTimeout(()=>ac.abort(),90000);try{const r=await fetch(${JSON.stringify(href)},{headers:{'X-Gestion-MP-PRO':'1'},signal:ac.signal});const b=await r.arrayBuffer();clearTimeout(to);const type=r.headers.get('content-type')||'';let html='';if(type.includes('html')){html=new TextDecoder().decode(b).slice(0,400000)};return {statut:r.status, ms:Math.round(performance.now()-t0), octets:b.byteLength, type, traceback:/Traceback|Internal Server Error/.test(html), lignesHtml: html ? (html.match(/<tr/g)||[]).length : null}}catch(e){clearTimeout(to);return {statut:'échec '+e.name, ms:Math.round(performance.now()-t0), octets:0, type:'', traceback:false}}})()`)
  const out = { role, genre, href, libelle, ecran, ...(r ?? { statut: 'inconnu', ms: null, octets: 0 }) }
  resultat.telechargements.push(out)
  flush()
  return out
}

async function capture(nom) {
  if (resultat.captures.length >= 80) return
  try {
    const r = await cdp('Page.captureScreenshot', { format: 'png' })
    const fichier = `${CAPTURES}/${nom.replace(/[^a-z0-9-]+/gi, '_').slice(0, 90)}.png`
    writeFileSync(fichier, Buffer.from(r.result.data, 'base64'))
    resultat.captures.push(fichier)
  } catch {
    /* pas de capture */
  }
}

// --- Les passes. ---
const resultat = { base: BASE, etiquette: CTX.etiquette ?? '', jour: CTX.jour, comptes: CTX.comptes, debut: new Date().toISOString(), passes: [], telechargements: [], recherches_globales: [], captures: [] }
const flush = () => writeFileSync(SORTIE, JSON.stringify(resultat))

function ongletsPermis(e, role) {
  return (e.onglets ?? [])
    .map((o) => (typeof o === 'string' ? { o, roles: null } : o))
    .filter((o) => !o.roles || o.roles.includes(role))
    .map((o) => o.o)
}
const avecOnglet = (ch, o) => (ch.includes('?') ? `${ch}&onglet=${o}` : `${ch}?onglet=${o}`)

async function visiter(pass, role, url, { tactile, nom }) {
  const r = await ouvrir(url, { tactile })
  const pbs = problemes(url, role, r)
  const ligne = { url, final: r.final, tAffiche: r.tAffiche, apiLente: r.apiLente, nbApi: r.nbApi, octets: r.octets, tableaux: (r.tableaux ?? []).map((t) => ({ libelle: t.libelle, lignes: t.lignes, compteur: t.compteur, charger: t.charger, enFenetre: t.enFenetre })), fenetres: (r.fenetres ?? []).length, pbs }
  // Recherche de la liste (hors fenêtre), si l'écran en a une.
  if (r.recherche?.length && !r.vide) {
    ligne.recherche = await chercher(url)
    if (ligne.recherche && ligne.recherche.ms !== null && ligne.recherche.ms > SEUIL_LENT_MS) pbs.push(`recherche lente ${ligne.recherche.ms} ms (« ${ligne.recherche.mot} »)`)
    if (ligne.recherche && ligne.recherche.ms === null) pbs.push(`recherche sans fin (« ${ligne.recherche.mot} »)`)
  }
  // Exports et documents vus sur l'écran.
  for (const x of r.exports ?? []) {
    const t = await telecharger(role, x.href, x.libelle, 'export', url)
    if (t && (t.statut !== 200 || t.traceback)) pbs.push(`export ${x.href} → ${t.statut}${t.traceback ? ' (trace)' : ''}`)
    else if (t && t.ms > SEUIL_BLOQUANT_MS) pbs.push(`export BLOQUANT ${t.ms} ms ${x.href}`)
    else if (t && t.ms > SEUIL_LENT_MS) pbs.push(`export lent ${t.ms} ms ${x.href}`)
  }
  for (const x of r.documents ?? []) {
    const t = await telecharger(role, x.href, x.libelle, 'document', url)
    if (t && (t.statut !== 200 || t.traceback)) pbs.push(`document ${x.href} → ${t.statut}${t.traceback ? ' (trace)' : ''}`)
    else if (t && t.ms > SEUIL_BLOQUANT_MS) pbs.push(`document BLOQUANT ${t.ms} ms ${x.href}`)
    else if (t && t.ms > SEUIL_LENT_MS) pbs.push(`document lent ${t.ms} ms ${x.href}`)
  }
  if (pbs.length) await capture(`${nom}-${url}`)
  if (process.env.TOURNEE_VERBEUX) console.error(`  ${url} ${r.tAffiche} ms, ${r.nbApi} appels${pbs.length ? ' — ' + pbs.join(' | ') : ''}`)
  pass.ecrans.push(ligne)
  flush()
  return ligne
}

async function passeBureau(role, w, h, { tactile } = {}) {
  await taille(w, h, !!tactile)
  await connecter(role)
  const pass = { role, taille: `${w}×${h}`, zone: tactile ? 'bureau au téléphone' : 'bureau', ecrans: [] }
  resultat.passes.push(pass)
  for (const e of ECRANS.filter((e) => e.roles.includes(role) && (!FILTRE_ECRANS.length || FILTRE_ECRANS.some((p) => e.ch.startsWith(p))))) {
    const ongs = SANS_ONGLETS ? [] : ongletsPermis(e, role)
    const urls = ongs.length ? ongs.map((o) => avecOnglet(e.ch, o)) : [e.ch]
    for (const url of urls) await visiter(pass, role, url, { tactile, nom: `${CTX.etiquette}-${role}-${w}` })
  }
  const nb = pass.ecrans.reduce((a, e) => a + e.pbs.length, 0)
  console.error(`[${pass.zone}] ${role} ${w}×${h} : ${pass.ecrans.length} écrans, ${nb} anomalie(s)`)
  flush()
}

async function passeAtelier(role, w, h) {
  await taille(w, h, true)
  await connecter(role)
  const pass = { role, taille: `${w}×${h}`, zone: 'atelier', ecrans: [] }
  resultat.passes.push(pass)
  for (const e of ATELIER) await visiter(pass, role, e.ch, { tactile: true, nom: `${CTX.etiquette}-${role}-atelier` })
  // Les documents de l'atelier : étiquettes des lots de la dernière réception (bouton de la fiche).
  if (CTX.lots_etiquettes?.length) {
    const href = `/api/documents/etiquettes?lots=${CTX.lots_etiquettes.join(',')}`
    await telecharger(role, href, 'Étiquettes des lots', 'document', '/atelier')
  }
  const nb = pass.ecrans.reduce((a, e) => a + e.pbs.length, 0)
  console.error(`[atelier] ${role} ${w}×${h} : ${pass.ecrans.length} écrans, ${nb} anomalie(s)`)
  flush()
}

// Documents que l'écran n'affiche qu'après un geste : le bilan du mois (Cockpit / Analyse), les
// étiquettes d'une réception, le bon de la commande d'exemple. Lancés par la route de l'écran.
async function documentsDuRole(role) {
  await taille(1440, 900, false)
  await connecter(role)
  await ouvrir(role === 'direction' ? '/cockpit' : '/accueil')
  for (const mois of CTX.mois ?? []) await telecharger(role, `/api/documents/bilan?mois=${mois}`, `Bilan ${mois}`, 'document', '/analyse')
  if (CTX.lots_etiquettes?.length) await telecharger(role, `/api/documents/etiquettes?lots=${CTX.lots_etiquettes.join(',')}`, 'Étiquettes', 'document', '/receptions')
  if (avec(ID.commande)) {
    await telecharger(role, `/api/documents/commandes/${ID.commande}/bon`, 'Bon de commande (A4)', 'document', `/commandes/${ID.commande}`)
    await telecharger(role, `/api/export/commandes/${ID.commande}/bon`, 'Bon de commande (Excel)', 'export', `/commandes/${ID.commande}`)
  }
  if (avec(ID.inventaire)) {
    await telecharger(role, `/api/documents/inventaires/${ID.inventaire}/feuille`, 'Feuille de comptage', 'document', `/inventaires/${ID.inventaire}`)
    await telecharger(role, `/api/documents/inventaires/${ID.inventaire}/feuille?recomptage=true`, 'Feuille de recomptage', 'document', `/inventaires/${ID.inventaire}`)
    await telecharger(role, `/api/export/inventaires/${ID.inventaire}`, 'Classeur de l’inventaire', 'export', `/inventaires/${ID.inventaire}`)
  }
  // Les exports des onglets que la tournée a pu ne pas voir (bouton hors écran) : la liste complète.
  const exports = ['/api/export/mouvements', '/api/export/lots', '/api/export/journal', '/api/export/commandes', '/api/export/receptions', '/api/export/receptions/pesees', '/api/export/receptions/bobines', '/api/export/dossiers', '/api/export/revient', '/api/export/pilotage', '/api/export/plan-achat?onglet=fournisseurs', '/api/export/plan-achat?onglet=references', '/api/export/ordres', '/api/export/operations', '/api/export/inventaires', '/api/export/matieres', '/api/export/qualites', '/api/export/metiers', '/api/export/fournisseurs', '/api/export/fournisseurs/fiches', '/api/export/controles', '/api/export/valorisation', '/api/export/prix', '/api/export/opportunites', '/api/export/echeancier', '/api/export/production?onglet=glissant', '/api/export/production?onglet=realise', '/api/export/production?onglet=besoins']
  if (role === 'direction') for (const href of exports) await telecharger(role, href, href.replace('/api/export/', ''), 'export', '(liste des exports)')
}

// La recherche globale de la coque : frappe d'un mot, temps jusqu'à la liste de résultats.
async function rechercheGlobale(role) {
  await taille(1440, 900, false)
  await connecter(role)
  await ouvrir(role === 'direction' ? '/cockpit' : '/accueil')
  const champ = await evaluer(`(()=>{const i=document.querySelector('[role=combobox][aria-label="Recherche globale"]');if(!i)return false;i.focus();return true})()`)
  const out = { role, mot: MOTS.global }
  if (!champ) out.etat = 'absente'
  else {
    reseau.clear()
    const t0 = performance.now()
    await cdp('Input.insertText', { text: MOTS.global })
    let liste = null
    while (performance.now() - t0 < 15000) {
      liste = await evaluer(`(()=>{const l=document.querySelector('[role=listbox]');return l?l.querySelectorAll('[role=option]').length:null})()`)
      const enVol = [...reseau.values()].some((r) => r.fin === null)
      const repondu = [...reseau.values()].some((r) => r.url.includes('/api/recherche') && r.fin !== null)
      if (repondu && liste !== null && !enVol) break
      await attendre(50)
    }
    out.ms = Math.round(performance.now() - t0)
    out.resultats = liste
    out.etat = liste === null ? 'pas de liste' : 'ouverte'
    const appels = [...reseau.values()].filter((r) => r.fin !== null)
    out.apiMs = appels.length ? Math.max(...appels.map((r) => Math.round((r.fin - r.debut) * 1000))) : null
  }
  resultat.recherches_globales.push(out)
  flush()
}

// === Exécution ===
const veut = (role) => FILTRE.length === 0 || FILTRE.includes(role)
for (const role of ['direction', 'achats', 'alimentation']) {
  if (!veut(role)) continue
  await passeBureau(role, 1440, 900)
}
for (const role of ['alimentation', 'direction']) {
  if (!veut(role)) continue
  await passeAtelier(role, 375, 812)
}
if (veut('alimentation')) await passeBureau('alimentation', 375, 812, { tactile: true })
for (const role of ['direction', 'achats']) if (veut(role)) await documentsDuRole(role)
for (const role of ['direction', 'achats', 'alimentation']) if (veut(role)) await rechercheGlobale(role)

resultat.fin = new Date().toISOString()
flush()
console.log(JSON.stringify({ ecrans: resultat.passes.reduce((a, p) => a + p.ecrans.length, 0), anomalies: resultat.passes.reduce((a, p) => a + p.ecrans.reduce((b, e) => b + e.pbs.length, 0), 0), telechargements: resultat.telechargements.length }))
ws.close()
chrome.kill()
process.exit(0)
