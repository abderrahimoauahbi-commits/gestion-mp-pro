// Recette navigateur de Gestion MP PRO, par rôle et par écran (critère A8 du plan de recette).
//
// Pilote un Chrome sans tête — SON PROPRE profil et SON PROPRE port CDP, jamais le panneau de
// navigateur partagé (cookies de session partagés entre serveurs localhost : F1, RESTES4) — et
// parcourt par de vraies navigations chaque écran ouvert à chaque rôle (direction, achats,
// alimentation, administrateur), puis essaie les écrans interdits, dans plusieurs tailles et dans
// les deux thèmes. Il relève, écran par écran :
//   - les réponses 4xx / 5xx inattendues des routes /api/ ;
//   - les erreurs JavaScript (console.error, exceptions) ;
//   - les écrans d'erreur (« La lecture a échoué », « Pas de réseau ») ;
//   - les pages vides et les chargements bloqués ;
//   - le défilement horizontal de la page (scrollWidth > clientWidth) et les éléments qui débordent ;
//   - pour l'alimentation et l'administrateur : TOUT texte qui ressemble à un montant, un prix, un
//     cours, une valeur ou un conseil d'achat (balayage du texte rendu).
// Un écran interdit doit renvoyer à l'accueil du rôle avec le bandeau « réservé à un autre rôle ».
//
// Usage : node recette_navigateur.mjs <base_url> <codes.json> <dossier_sortie>
//   ex. : node recette_navigateur.mjs http://127.0.0.1:8137 .../codes.json .../captures
// Sortie : un objet JSON sur stdout (repris par resultat-recette-ecran.txt), captures dans le dossier.

import { spawn } from 'node:child_process'
import { readFileSync, mkdirSync, writeFileSync } from 'node:fs'

const BASE = process.argv[2] ?? 'http://127.0.0.1:8137'
const CODES = JSON.parse(readFileSync(process.argv[3], 'utf8'))
const CAPTURES = process.argv[4] ?? '/tmp/recette-captures'
const PROFIL = process.argv[5] ?? '/tmp/recette-profil-chrome'
const PORT_CDP = Number(process.argv[6] ?? 9377)
mkdirSync(CAPTURES, { recursive: true })

const CHROME =
  process.env.CHROME ?? '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

// --- Écrans par rôle, repris de frontend/src/pages/*/ecrans.ts (registre unique, A8). ---
// id : un enregistrement réel de la base reprise, pour les fiches.
const ID = { lot: 21, matiere: 107, commande: 330, reception: 321, dossier: 88, qualite: 14, metier: 1, ordre: 319, fournisseur: 11, inventaire: 13, signalement: 1 }

// Les écrans de bureau et leurs onglets (?onglet=…). roles : qui y a droit.
const ECRANS = [
  { ch: '/cockpit', roles: ['direction'], onglets: ['faire', 'alertes', 'ensemble', 'evolution', 'economies'] },
  { ch: '/accueil', roles: ['achats', 'alimentation'] },
  { ch: '/stock', roles: ['direction', 'achats', 'alimentation'], onglets: ['matieres', 'lots', 'mouvements', 'ordres', 'a-valider'] },
  { ch: `/stock/matieres/${ID.matiere}`, roles: ['direction', 'achats', 'alimentation'] },
  { ch: `/lots/${ID.lot}`, roles: ['direction', 'achats', 'alimentation'] },
  { ch: `/tracabilite?lot=${ID.lot}`, roles: ['direction', 'achats', 'alimentation'] },
  { ch: '/sorties', roles: ['direction', 'achats', 'alimentation'], onglets: ['valide', 'brouillon', 'annule'] },
  { ch: `/ordres/${ID.ordre}`, roles: ['direction', 'achats', 'alimentation'] },
  { ch: '/production', roles: ['direction', 'achats', 'alimentation'], onglets: ['plan', 'glissant', 'realise', 'besoins'] },
  { ch: `/production/besoins/${ID.matiere}`, roles: ['direction', 'achats', 'alimentation'] },
  { ch: '/plan-achat', roles: ['direction', 'achats'], onglets: ['fournisseurs', 'references'] },
  { ch: `/plan-achat/preparer/${ID.fournisseur}`, roles: ['direction', 'achats'] },
  { ch: '/commandes', roles: ['direction', 'achats'], onglets: ['brouillon', 'a_approuver', 'envoyee', 'confirmee', 'clos'] },
  { ch: `/commandes/${ID.commande}`, roles: ['direction', 'achats'], onglets: ['lignes', 'prix', 'expedition', 'receptions', 'approbation', 'pieces', 'historique'] },
  { ch: '/receptions', roles: ['direction', 'achats'], onglets: ['brouillon', 'validee', 'annulee', 'reclamations', 'bobines', 'pesees'] },
  { ch: `/receptions/${ID.reception}`, roles: ['direction', 'achats'], onglets: ['lignes', 'reclamations', 'pieces', 'historique'] },
  { ch: '/importations', roles: ['direction', 'achats'], onglets: ['ouverts', 'clos', 'rattacher'] },
  { ch: `/dossiers/${ID.dossier}`, roles: ['direction', 'achats'], onglets: ['familles', 'marchandises', 'frais', 'echeancier', 'pieces', 'facture', 'historique'] },
  { ch: '/inventaire', roles: ['direction', 'achats'], onglets: ['cours', 'passes'] },
  { ch: `/inventaires/${ID.inventaire}`, roles: ['direction', 'achats'], onglets: ['lots', 'pieces', 'historique'] },
  { ch: '/operations', roles: ['direction', 'achats', 'alimentation'], onglets: ['transfert', 'retour_machine', { o: 'ouverture', roles: ['direction', 'achats'] }, { o: 'ajustement', roles: ['direction', 'achats'] }, { o: 'retour_fournisseur', roles: ['direction', 'achats'] }] },
  { ch: '/catalogue', roles: ['direction', 'achats', 'alimentation'], onglets: ['matieres', { o: 'classification', roles: ['direction', 'achats'] }, { o: 'fournisseurs', roles: ['direction', 'achats'] }] },
  { ch: `/matieres/${ID.matiere}`, roles: ['direction', 'achats', 'alimentation'], onglets: ['classification', 'conditionnement', 'historique', { o: 'achat', roles: ['direction', 'achats'] }, { o: 'pieces', roles: ['direction', 'achats'] }] },
  { ch: `/fournisseurs/${ID.fournisseur}`, roles: ['direction', 'achats'], onglets: ['fiche', 'pieces', 'historique'] },
  { ch: '/qualites', roles: ['direction', 'achats', 'alimentation'], onglets: ['qualites', 'nomenclature'] },
  { ch: `/qualites/${ID.qualite}`, roles: ['direction', 'achats', 'alimentation'], onglets: ['recette', 'plan', 'versions', 'historique'] },
  { ch: '/metiers', roles: ['direction', 'achats', 'alimentation'] },
  { ch: `/metiers/${ID.metier}`, roles: ['direction', 'achats', 'alimentation'], onglets: ['fils', 'reglages', 'historique'] },
  { ch: '/analyse', roles: ['direction', 'achats'], onglets: ['valorisation', 'matrice', 'historique', 'opportunites', 'fournisseurs', 'revient', 'echeancier', 'controles', 'production'] },
  { ch: '/reglages', roles: ['direction', 'achats'], onglets: ['parametres', 'devises', 'magasins', 'postes', 'codes', 'periode'] },
  { ch: '/administration', roles: ['direction', 'administrateur'], onglets: ['comptes', 'appareils', 'sauvegardes', 'journal', 'courriel', 'serveur', 'telephone', 'technique', 'reprise', { o: 'donnees', roles: ['direction'] }] },
  { ch: '/aide', roles: ['direction', 'achats', 'alimentation', 'administrateur'], onglets: ['regles', 'roles', 'pas', 'calculs', 'analyse', 'ecrans', 'telephone'] },
  { ch: '/compte', roles: ['direction', 'achats', 'alimentation', 'administrateur'] },
]

// Les écrans de l'atelier au téléphone (hors coque du bureau) : direction et alimentation.
const ATELIER = [
  { ch: '/atelier', roles: ['direction', 'alimentation'] },
  { ch: '/atelier/envoyer', roles: ['direction', 'alimentation'] },
  { ch: '/atelier/ordres', roles: ['direction', 'alimentation'] },
  { ch: `/atelier/ordres/${ID.ordre}`, roles: ['direction', 'alimentation'] },
  { ch: '/atelier/retour', roles: ['direction', 'alimentation'] },
  { ch: '/atelier/chercher', roles: ['direction', 'alimentation'] },
  { ch: `/atelier/lots/${ID.lot}`, roles: ['direction', 'alimentation'] },
  { ch: '/atelier/deplacer', roles: ['direction', 'alimentation'] },
  { ch: '/atelier/montage', roles: ['direction', 'alimentation'] },
  { ch: '/atelier/signaler', roles: ['direction', 'alimentation'] },
]

const TOUS = ['direction', 'achats', 'alimentation', 'administrateur']
const accueilDe = (role, tel) =>
  role === 'direction' ? '/cockpit' : role === 'administrateur' ? '/administration' : role === 'alimentation' && tel ? '/atelier' : '/accueil'
// Qui ne voit AUCUN montant : alimentation, administrateur.
const SANS_PRIX = (role) => role === 'alimentation' || role === 'administrateur'
// Un MONTANT réel : un nombre collé à une devise, ou un symbole monétaire (A4, § 11.2). Ceci ne
// doit JAMAIS être visible à l'alimentation ni à l'administrateur, nulle part, y compris l'aide.
const RE_AMOUNT = /(\d[\d  .,]*\s?(?:MAD|USD|EUR|DH|Dhs|DHS)\b)|(?:\b(?:MAD|USD|EUR)\b\s?\d)|[€$£]\s?\d|\d\s?[€$£]|[€$£]/i
// Une ÉTIQUETTE de prix (colonne, libellé, conseil d'achat) qui ne désigne QUE de l'argent.
// Interdite à l'alimentation sur un écran de données ; tolérée dans le texte explicatif du Mode
// d'emploi et de la fiche compte. On exclut sciemment les mots ambigus « revient » (verbe revenir)
// et « cours » (« en cours »), qui ne portent aucune valeur ; un vrai montant est pris par RE_AMOUNT.
const RE_LABEL = /\b(prix|montant|valoris[ée]|valorisation|budget|cmup|coût de revient|conseil d'achat|à commander pour)\b/i
// Écrans où un mot comme « prix » peut apparaître sans valeur (texte d'aide, nom d'une action du
// journal des actions — écran technique de l'administrateur, lecture du journal approuvée par la
// matrice des droits) : on n'y applique que la détection d'un MONTANT réel, pas des étiquettes.
const ECRAN_EXPLICATIF = (url) => url.startsWith('/aide') || url.startsWith('/compte') || url.startsWith('/administration')

function ecransDuRole(role) {
  const bureau = ECRANS.filter((e) => e.roles.includes(role))
  const atelier = ATELIER.filter((e) => e.roles.includes(role))
  return { bureau, atelier }
}
function interditsDuRole(role) {
  const permis = new Set([...ECRANS, ...ATELIER].filter((e) => e.roles.includes(role)).map((e) => e.ch.split('?')[0]))
  return [...ECRANS, ...ATELIER].filter((e) => !permis.has(e.ch.split('?')[0])).map((e) => e.ch.split('?')[0])
}

// --- Pilote CDP minimal (un seul onglet). ---
const attendre = (ms) => new Promise((r) => setTimeout(r, ms))
const chrome = spawn(
  CHROME,
  ['--headless=new', `--remote-debugging-port=${PORT_CDP}`, `--user-data-dir=${PROFIL}`, '--no-first-run', '--no-default-browser-check', '--hide-scrollbars', '--disable-gpu', 'about:blank'],
  { stdio: 'ignore' },
)
let cibles
for (let i = 0; i < 80; i++) {
  try {
    cibles = await (await fetch(`http://127.0.0.1:${PORT_CDP}/json`)).json()
    if (cibles.find((c) => c.type === 'page')) break
  } catch {
    /* pas encore prêt */
  }
  await attendre(200)
}
const page = cibles.find((c) => c.type === 'page')
const ws = new WebSocket(page.webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r))
let n = 0
const attente = new Map()
const jsErreurs = []
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
// Toute boîte de dialogue JS (dont `beforeunload` d'une saisie en cours) est acceptée d'office,
// pour qu'une navigation au niveau du navigateur ne bloque jamais le pilote.
ws.addEventListener('message', (e) => {
  const m = JSON.parse(e.data)
  if (m.method === 'Page.javascriptDialogOpening') cdp('Page.handleJavaScriptDialog', { accept: true })
})

async function taille(w, h, tactile) {
  await cdp('Emulation.setDeviceMetricsOverride', { width: w, height: h, deviceScaleFactor: 1, mobile: !!tactile, screenWidth: w, screenHeight: h })
  await cdp('Emulation.setTouchEmulationEnabled', { enabled: !!tactile, maxTouchPoints: tactile ? 5 : 0 })
}
async function theme(valeur) {
  await cdp('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: valeur }] })
}
async function connecter(role) {
  await cdp('Page.navigate', { url: `${BASE}/connexion` })
  await attendre(1200)
  const ident = `essai-${role}`
  const code = CODES[ident]
  const statut = await evaluer(
    `fetch('/api/deconnexion',{method:'POST',headers:{'Content-Type':'application/json','X-Gestion-MP-PRO':'1'}}).catch(()=>0).then(()=>fetch('/api/connexion',{method:'POST',headers:{'Content-Type':'application/json','X-Gestion-MP-PRO':'1'},body:JSON.stringify({identifiant:${JSON.stringify(ident)},code:${JSON.stringify(code)}})})).then(r=>r.status).catch((e)=>'REJET '+e.message)`,
  )
  if (statut !== 200) {
    console.error(`ARRÊT : connexion ${role} = ${statut} (le serveur est-il joignable ?).`)
    ws.close()
    chrome.kill()
    process.exit(2)
  }
  return statut
}

// Capture l'état d'un écran après navigation à `url`.
async function ouvrir(url, { tactile } = {}) {
  jsErreurs.length = 0
  const reponses = []
  const capteur = (e) => {
    const m = JSON.parse(e.data)
    if (m.method === 'Network.responseReceived') {
      const r = m.params.response
      if (r.url.includes('/api/') && r.status >= 400 && !r.url.endsWith('/api/connexion') && !r.url.endsWith('/api/deconnexion'))
        reponses.push(`${r.status} ${r.url.replace(BASE, '')}`)
    }
  }
  ws.addEventListener('message', capteur)
  await cdp('Page.navigate', { url: BASE + url })
  // Attendre la fin du chargement (spinner [role=status].roue disparu), max 12 s.
  let t = 0
  await attendre(500)
  while (t < 12000) {
    const enCours = await evaluer(`!!document.querySelector('[role=status] [aria-hidden=true]') && !document.querySelector('main')?.innerText.trim()`)
    if (!enCours) break
    await attendre(300)
    t += 300
  }
  await attendre(tactile ? 900 : 600)
  const info = await evaluer(`(()=>{
    const d=document.documentElement;
    const racine=document.querySelector('main')??document.querySelector('[data-atelier]')??document.body;
    const txt=(racine.innerText||'').trim();
    const larges=[...document.querySelectorAll('body *')]
      .filter(e=>{const r=e.getBoundingClientRect();const s=getComputedStyle(e);return r.right>innerWidth+1 && s.position!=='fixed' && s.overflow!=='hidden' && r.width>0})
      .slice(0,6).map(e=>e.tagName.toLowerCase()+(e.className&&typeof e.className==='string'?'.'+e.className.split(' ')[0]:''));
    const bandeau=[...document.querySelectorAll('[role=alert]')].map(e=>(e.innerText||'').trim()).join(' | ');
    const erreurUI=/La lecture a échoué|Pas de réseau|Une erreur est survenue|went wrong/.test(document.body.innerText);
    return {
      final: location.pathname,
      vide: txt.length < 2,
      spinner: !!document.querySelector('[role=status] [aria-hidden=true]'),
      largeurPage: d.scrollWidth+'/'+d.clientWidth,
      debordeH: d.scrollWidth > d.clientWidth + 1,
      debordent: larges,
      bandeau,
      erreurUI,
      texte: txt.slice(0, 200000),
    }
  })()`)
  ws.removeEventListener('message', capteur)
  return { ...info, api: reponses, js: [...jsErreurs] }
}

function problemes(url, role, r, { interdit, tactile } = {}) {
  const pbs = []
  if (r.api.length) pbs.push('api: ' + r.api.join(', '))
  if (r.js.length) pbs.push('js: ' + r.js.join(' ; '))
  if (r.erreurUI) pbs.push('écran d’erreur')
  if (r.vide && !interdit) pbs.push('page vide')
  if (r.spinner && r.vide) pbs.push('chargement bloqué')
  if (r.debordeH) pbs.push(`défilement horizontal ${r.largeurPage}` + (r.debordent.length ? ' — ' + r.debordent.join(', ') : ''))
  if (SANS_PRIX(role)) {
    const txt = r.texte || ''
    const re = ECRAN_EXPLICATIF(url) ? RE_AMOUNT : new RegExp(`${RE_AMOUNT.source}|${RE_LABEL.source}`, 'i')
    const m = txt.match(re)
    if (m) {
      const i = Math.max(0, m.index - 35)
      pbs.push(`MONTANT CHEZ ${role.toUpperCase()} : …${txt.slice(i, m.index + 45).replace(/\s+/g, ' ')}…`)
    }
  }
  return pbs
}

// --- Les passes. ---
const resultat = { base: BASE, debut: new Date().toISOString(), passes: [] }
const SORTIE = process.argv[7] ?? `${CAPTURES}/resultat.json`
const flush = () => writeFileSync(SORTIE, JSON.stringify(resultat))

// Les onglets d'un écran permis à ce rôle (un onglet peut avoir ses propres rôles).
function ongletsPermis(e, role) {
  return (e.onglets ?? [])
    .map((o) => (typeof o === 'string' ? { o, roles: null } : o))
    .filter((o) => !o.roles || o.roles.includes(role))
    .map((o) => o.o)
}

async function passeBureau(role, w, h, themeValeur, { baseSeulement } = {}) {
  await taille(w, h, false)
  await theme(themeValeur)
  const statut = await connecter(role)
  const { bureau } = ecransDuRole(role)
  const pass = { role, taille: `${w}×${h}`, theme: themeValeur, zone: 'bureau', connexion: statut, ecrans: [], interdits: [] }
  for (const e of bureau) {
    const ongs = baseSeulement ? [] : ongletsPermis(e, role)
    const variantes = ongs.length ? ongs.map((o) => (e.ch.includes('?') ? `${e.ch}&onglet=${o}` : `${e.ch}?onglet=${o}`)) : [e.ch]
    for (const url of variantes) {
      const r = await ouvrir(url)
      const pbs = problemes(url, role, r)
      pass.ecrans.push({ url, final: r.final, largeur: r.largeurPage, pbs })
    }
  }
  // Écrans interdits : doivent renvoyer à l'accueil du rôle avec le bandeau.
  for (const ch of interditsDuRole(role)) {
    if (ch.startsWith('/atelier')) continue // l'atelier se teste au téléphone
    const r = await ouvrir(ch)
    const attendu = accueilDe(role, false)
    const ok = r.final === attendu && /réservé à un autre rôle/.test(r.bandeau)
    pass.interdits.push({ ch, final: r.final, attendu, bandeau: /réservé à un autre rôle/.test(r.bandeau), ok })
  }
  const nb = pass.ecrans.reduce((a, e) => a + e.pbs.length, 0) + pass.interdits.filter((i) => !i.ok).length
  console.error(`[bureau] ${role} ${w}×${h} ${themeValeur} : ${pass.ecrans.length} écrans, ${pass.interdits.length} interdits, ${nb} anomalie(s)`)
  resultat.passes.push(pass)
  flush()
  return pass
}

async function passeAtelier(role, w, h, themeValeur) {
  await taille(w, h, true)
  await theme(themeValeur)
  const statut = await connecter(role)
  const { atelier } = ecransDuRole(role)
  const pass = { role, taille: `${w}×${h}`, theme: themeValeur, zone: 'atelier', connexion: statut, ecrans: [], interdits: [] }
  for (const e of atelier) {
    const r = await ouvrir(e.ch, { tactile: true })
    const pbs = problemes(e.ch, role, r, { tactile: true })
    pass.ecrans.push({ url: e.ch, final: r.final, largeur: r.largeurPage, pbs })
  }
  // Un écran de bureau interdit au rôle renvoie à son accueil (alimentation → /atelier). La
  // direction voit tout : seul l'atelier a des écrans qui lui restent, aucun écran de bureau n'est
  // interdit, donc on ne teste les refus que pour l'alimentation.
  const interditsBureau = { alimentation: ['/cockpit', '/plan-achat', '/commandes', '/analyse', '/reglages', '/receptions', '/importations', '/inventaire'], direction: [] }
  for (const ch of interditsBureau[role] ?? []) {
    const r = await ouvrir(ch, { tactile: true })
    const attendu = accueilDe(role, true)
    const ok = r.final === attendu
    pass.interdits.push({ ch, final: r.final, attendu, bandeau: /réservé à un autre rôle/.test(r.bandeau), ok })
  }
  const nb = pass.ecrans.reduce((a, e) => a + e.pbs.length, 0) + pass.interdits.filter((i) => !i.ok).length
  console.error(`[atelier] ${role} ${w}×${h} ${themeValeur} : ${pass.ecrans.length} écrans, ${nb} anomalie(s)`)
  resultat.passes.push(pass)
  flush()
  return pass
}

// Contrôle des interactions de la coque (recherche globale, cloche, aide) pour un rôle de bureau.
async function passeInteractions(role) {
  await taille(1366, 768, false)
  await theme('light')
  await connecter(role)
  await ouvrir(accueilDe(role, false))
  const out = { role }
  // Recherche globale (direction, achats, alimentation seulement) : vraie frappe clavier (CDP),
  // car affecter `input.value` ne réveille pas l'état React.
  const champ = await evaluer(`(()=>{const i=document.querySelector('[role=combobox][aria-label="Recherche globale"]');if(!i)return false;i.focus();return true})()`)
  if (!champ) out.recherche = 'absente'
  else {
    await cdp('Input.insertText', { text: 'bande' })
    await attendre(1200)
    out.recherche = await evaluer(`(()=>{const l=document.querySelector('[role=listbox]');return l?('ouverte, '+l.querySelectorAll('[role=option]').length+' résultats'):'pas de liste'})()`)
  }
  // Cloche (notifications).
  out.cloche = await evaluer(`(async()=>{
    const b=[...document.querySelectorAll('button')].find(x=>/notification|cloche|alerte/i.test(x.getAttribute('aria-label')||x.title||''));
    if(!b) return 'absente';
    b.click(); await new Promise(r=>setTimeout(r,500));
    return document.querySelector('[role=dialog][aria-label="Notifications"]') ? 'panneau ouvert' : 'pas de panneau';
  })()`)
  // Aide de l'écran (menu du compte → « Aide de l'écran »).
  out.aide = await evaluer(`(async()=>{
    const m=[...document.querySelectorAll('button')].find(x=>/compte|menu du compte/i.test(x.getAttribute('aria-label')||x.title||''))||document.querySelector('header button:last-of-type');
    if(m) { m.click(); await new Promise(r=>setTimeout(r,400)); }
    const a=[...document.querySelectorAll('button,a')].find(x=>/Aide de l.écran/i.test(x.textContent||''));
    if(!a) return 'entrée absente';
    a.click(); await new Promise(r=>setTimeout(r,500));
    return /Mode d.emploi|Aide/.test(document.body.innerText) ? 'ouverte' : 'rien';
  })()`)
  resultat.interactions = resultat.interactions || []
  resultat.interactions.push(out)
  flush()
  return out
}

async function capture(role, url, nom, { tactile } = {}) {
  await taille(tactile ? 375 : 1366, tactile ? 812 : 768, !!tactile)
  await connecter(role)
  await ouvrir(url, { tactile })
  const r = await cdp('Page.captureScreenshot', { format: 'png' })
  writeFileSync(`${CAPTURES}/${nom}.png`, Buffer.from(r.result.data, 'base64'))
}

// Parcours par de vrais clics : les défauts de Gestion MP observables au navigateur (§ 9.2).
async function passeParcours() {
  const out = { quoi: 'parcours (vrais clics)', checks: [] }
  const dire = (nom, ok, detail) => out.checks.push({ nom, ok, detail })

  // H-08 : le QR `/lot/:id` mène à la fiche qui convient à l'appareil et au rôle.
  await taille(1366, 768, false)
  await connecter('achats')
  let r = await ouvrir(`/lot/${ID.lot}`)
  dire('H-08 QR achats bureau → /lots/:id', r.final === `/lots/${ID.lot}`, r.final)
  await connecter('direction')
  r = await ouvrir(`/lot/${ID.lot}`)
  dire('H-08 QR direction bureau → /lots/:id', r.final === `/lots/${ID.lot}`, r.final)
  await taille(375, 812, true)
  await connecter('alimentation')
  r = await ouvrir(`/lot/${ID.lot}`, { tactile: true })
  dire('H-08 QR alimentation téléphone → /atelier/lots/:id', r.final === `/atelier/lots/${ID.lot}`, r.final)

  // H-06 : le fil monté n'est plus dit « hors stock » ni « pour information » (décision U8).
  await taille(1366, 768, false)
  await connecter('direction')
  await ouvrir(`/metiers/${ID.metier}?onglet=fils`)
  const filTexte = await evaluer(`/hors stock|pour information/i.test(document.querySelector('main').innerText)`)
  dire('H-06 fil monté sans « hors stock »/« pour information »', filTexte === false, filTexte ? 'texte interdit trouvé' : 'ok')

  // H-10 : une saisie n'est jamais perdue — modifier un réglage puis cliquer un lien du menu
  // déclenche la question « Saisie non enregistrée ».
  await ouvrir('/reglages?onglet=parametres')
  const champOk = await evaluer(`(()=>{const i=document.querySelector('main input[type=text], main input:not([type])');if(!i)return 'pas de champ';i.focus();return 'ok'})()`)
  let gardeDetail = champOk
  if (champOk === 'ok') {
    await cdp('Input.insertText', { text: 'X' })
    await attendre(400)
    await evaluer(`(()=>{const a=document.querySelector('nav a[href="/stock"], aside a[href="/stock"]');if(a)a.click();return !!a})()`)
    await attendre(700)
    gardeDetail = await evaluer(`document.querySelector('[role=alertdialog][aria-label="Saisie non enregistrée"]') ? 'question posée' : 'AUCUNE question (saisie perdue)'`)
    // Abandonner (et non « continuer ») pour laisser une page propre : la saisie est alors quittée,
    // et la navigation suivante n'ouvre pas de boîte « quitter la page ? ».
    await evaluer(`(()=>{const b=[...document.querySelectorAll('[role=alertdialog] button')].find(x=>/abandonner/i.test(x.textContent));if(b)b.click()})()`)
    await attendre(600)
  }
  dire('H-10 saisie jamais perdue (réglages)', gardeDetail === 'question posée', gardeDetail)

  // Atelier « Envoyer » : la page s'ouvre, propose, sans aucun montant (alimentation, téléphone).
  await taille(375, 812, true)
  await connecter('alimentation')
  r = await ouvrir('/atelier/envoyer', { tactile: true })
  const montant = (r.texte || '').match(new RegExp(`${RE_AMOUNT.source}|${RE_LABEL.source}`, 'i'))
  dire('Atelier Envoyer : page pleine, sans montant', !r.vide && !montant, r.vide ? 'vide' : montant ? 'montant: ' + montant[0] : 'ok')

  resultat.parcours = out
  flush()
  console.error(`[parcours] ${out.checks.filter((c) => c.ok).length}/${out.checks.length} réussis`)
  return out
}

// === Exécution ===
// Filtre optionnel : V3_ROLES="alimentation,administrateur" pour rejouer un sous-ensemble.
const FILTRE = (process.env.V3_ROLES ?? '').split(',').filter(Boolean)
const veut = (role) => FILTRE.length === 0 || FILTRE.includes(role)
// 1) Bureau en 1366×768, clair puis sombre, pour chaque rôle.
for (const role of TOUS) {
  if (!veut(role)) continue
  await passeBureau(role, 1366, 768, 'light')
  await passeBureau(role, 1366, 768, 'dark', { baseSeulement: true })
}
// 2) Bureau en 1920×1080 (clair) pour la direction (le rôle au menu le plus large).
if (veut('direction')) await passeBureau('direction', 1920, 1080, 'light')
// 3) Atelier en 360×640 et 375×812, clair puis sombre, pour l'alimentation et la direction.
for (const role of ['alimentation', 'direction']) {
  if (!veut(role)) continue
  await passeAtelier(role, 360, 640, 'light')
  await passeAtelier(role, 375, 812, 'light')
  await passeAtelier(role, 375, 812, 'dark')
}
// 4) Interactions de la coque.
for (const role of ['direction', 'achats', 'alimentation']) if (veut(role)) await passeInteractions(role)
// 5) Parcours par de vrais clics.
if (FILTRE.length === 0) await passeParcours()
// 6) Quelques captures témoins.
if (FILTRE.length === 0) {
  await capture('direction', '/cockpit?onglet=ensemble', 'cockpit-direction')
  await capture('alimentation', '/stock', 'stock-alimentation')
  await capture('alimentation', '/atelier/envoyer', 'atelier-envoyer', { tactile: true })
  await capture('achats', '/commandes', 'commandes-achats')
}

resultat.fin = new Date().toISOString()
flush()
console.log(JSON.stringify(resultat))
ws.close()
chrome.kill()
process.exit(0)
