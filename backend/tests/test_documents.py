"""Documents imprimables (lot D9) : papier à en-tête de l'usine (A22), rendu A4 sans coque,
règle d'affichage des nombres, étiquettes QR des lots (route 114 ; DEFAUTS C-18).
"""

from __future__ import annotations

import base64
import hashlib
import re
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal

import pytest
from fabrique import *  # noqa: F403
from fabriques.documents import SOCIETE, lire_qr, reglages, svgs, textes
from fabriques.stock import entree, lot, matiere, unique
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from gestion_mp_pro.db import fabrique
from gestion_mp_pro.documents import format as fmt
from gestion_mp_pro.documents import rendu
from gestion_mp_pro.modeles import Magasin
from gestion_mp_pro.modeles.enums import TypeMagasin
from gestion_mp_pro.services import horloge

ESSAI = rendu.environnement().from_string(
    '{% extends "_papier_a_en_tete.html" %}{% block contenu %}<h1>Contenu</h1>'
    '<p class="poids">{{ poids|kg }}</p><p class="jour">{{ jour|date }}</p>{% endblock %}'
)
NSP = " "


def _papier(langue: fmt.Langue = "fr", **valeurs: str) -> str:
    societe = rendu.societe_de({**SOCIETE, **valeurs})
    return rendu.rendre(
        ESSAI, societe=societe, titre="Essai", langue=langue, poids=1234.55, jour=date(2026, 10, 8)
    )


def test_le_papier_a_en_tete_est_celui_de_l_usine() -> None:
    """A22 : raison sociale en rouge à grande initiale, secteur dessous, forme et capital, siège,
    ville, téléphone ; pied : banques séparées, ICE, R.C, N.I.F, C.N.S.S, patente."""
    html = _papier()
    assert textes(html, "entete-societe") == [
        "TAPIS ESSAI SA Fabrication de tapis mécaniques "
        "SOCIETE ANONYME AU CAPITAL DE 20 000 000 DH SIÈGE SOCIAL Zone industrielle, lot 12 "
        "FES 05 35 00 00 00"
    ]
    assert textes(html, "nom") == ["TAPIS ESSAI SA"]
    assert textes(html, "banques") == [
        "BANQUES ATTIJARIWAFA BANK : 90D012433 B.M.C.I : 01063 000619 001 82"
    ]
    assert "90D012433&emsp;&emsp;B.M.C.I" in html, "deux banques bien séparées"
    assert textes(html, "identifiants") == [
        "ICE : 001122334455667 R.C : 12345 N.I.F : 4011223 C.N.S.S : 7654321 PATENTE : 13300000"
    ]
    assert ".entete-societe .nom { font-size: 19pt; color: var(--rouge-societe);" in html
    assert "--rouge-societe: #d40000;" in html
    assert ".entete-societe .nom::first-letter { font-size: 28pt; }" in html
    assert '<html lang="fr">' in html and "avertissement" not in textes_classes(html)


def textes_classes(html: str) -> set[str]:
    """Les classes posées sur les éléments du corps du document."""
    corps = html[html.index("<body") :]
    return {c for attribut in re.findall(r'class="([^"]+)"', corps) for c in attribut.split()}


def test_le_document_est_un_a4_aux_tailles_en_points() -> None:
    """A4 (`@page`), polices en points, rien à l'écran seulement qui s'imprime."""
    html = _papier()
    assert "@page { size: A4; margin: 12mm 13mm 10mm; }" in html
    tailles = re.findall(r"font(?:-size)?:\s*(?:\d+\s+)?([\d.]+)(pt|px|em|rem)", html)
    assert tailles and {unite for _, unite in tailles} == {"pt"}
    assert ".ecran-seulement { display: none !important; }" in html
    assert textes(html, "barre") == ["Imprimer / enregistrer en PDF (A4)"]
    assert "ecran-seulement" in re.search(r'<div class="([^"]+)"><button', html).group(1)  # type: ignore[union-attr]


def test_le_bon_fournisseur_a_son_papier_en_anglais() -> None:
    """Le bon de D3 est en anglais : « HEAD OFFICE », « BANKS », nombres et dates à l'anglaise."""
    html = _papier("en")
    assert '<html lang="en">' in html
    assert "HEAD OFFICE" in textes(html, "entete-societe")[0]
    assert textes(html, "banques")[0].startswith("BANKS ")
    assert "SIÈGE" not in html and "BANQUES" not in html
    assert textes(html, "poids") == ["1,234.55 kg"] and textes(html, "jour") == ["08 Oct 2026"]
    fr = _papier()
    assert textes(fr, "poids") == [f"1{NSP}234,55{NSP}kg"] and textes(fr, "jour") == ["08/10/2026"]


def test_un_en_tete_non_regle_se_dit_a_l_ecran_seulement() -> None:
    """Sans raison sociale : un bandeau, hors impression ; aucune ligne vide sur le papier."""
    html = rendu.rendre(ESSAI, societe=rendu.Societe(), titre="Essai", poids=None, jour=None)
    (bandeau,) = textes(html, "avertissement")
    assert bandeau.startswith("En-tête non réglé")
    assert "ecran-seulement" in re.search(r'<p class="([^"]+)">En-tête', html).group(1)  # type: ignore[union-attr]
    assert "entete-societe" not in textes_classes(html)
    assert "pied-societe" not in textes_classes(html)
    assert textes(html, "poids") == ["—"] and textes(html, "jour") == ["—"]


def test_les_lignes_vides_du_papier_sont_omises() -> None:
    """Un réglage vide n'imprime ni sa ligne ni son libellé ; les banques vides non plus."""
    html = _papier(adresse="", telephone="", banques=" · ", cnss="", secteur="")
    assert "SIÈGE SOCIAL" not in html and "BANQUES" not in html and "C.N.S.S" not in html
    assert textes(html, "identifiants") == [
        "ICE : 001122334455667 R.C : 12345 N.I.F : 4011223 PATENTE : 13300000"
    ]


def test_le_papier_echappe_les_reglages() -> None:
    """Un réglage n'injecte rien dans la page (échappement automatique)."""
    html = _papier(nom_entreprise="<script>alert(1)</script>", ville='"><b>')
    assert "<script>alert(1)" not in html and "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert html.count("<script>") == 1


def test_le_papier_se_lit_dans_les_reglages() -> None:
    """`rendu.societe(s)` lit les réglages « Société » ; « · » sépare les banques."""
    with reglages(SOCIETE), fabrique()() as s:
        lu = rendu.societe(s)
    assert lu.nom == "TAPIS ESSAI SA" and lu.reglee
    assert lu.banques == ("ATTIJARIWAFA BANK : 90D012433", "B.M.C.I : 01063 000619 001 82")
    assert [x for x, _ in lu.identifiants] == ["ICE", "R.C", "N.I.F", "C.N.S.S", "PATENTE"]


def test_un_document_s_imprime_sans_coque() -> None:
    """Ouvert dans un onglet (`inline`), seul script permis par son empreinte, rien d'extérieur."""
    html = _papier()
    r = rendu.reponse(html)
    assert r.headers["content-disposition"] == "inline"
    assert r.media_type == "text/html"
    (script,) = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
    empreinte = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
    assert f"script-src 'sha256-{empreinte}'" in r.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    assert not re.search(r'(src|href)="(https?:)?//', html), "aucune ressource extérieure"


def test_plusieurs_feuilles_en_paysage() -> None:
    """Une feuille par magasin (D5) : chacune son en-tête ; A4 paysage."""
    gabarit = rendu.environnement().from_string(
        '{% extends "_papier_a_en_tete.html" %}{% import "_papier.html" as papier %}'
        "{% block pages %}{% for m in magasins %}{% call papier.feuille(societe, mots) %}"
        "<h1>{{ m }}</h1>{% endcall %}{% endfor %}{% endblock %}"
    )
    html = rendu.rendre(
        gabarit, societe=rendu.societe_de(SOCIETE), titre="F", paysage=True, magasins=["A", "B"]
    )
    assert "@page { size: A4 landscape;" in html and '<body class="paysage">' in html
    assert len(textes(html, "page")) == 2 and len(textes(html, "nom")) == 2


@pytest.mark.parametrize(
    ("valeur", "attendu"),
    [
        ((17398184,), f"17{NSP}398{NSP}184"),
        ((1234.5, 1), f"1{NSP}234,5"),
        ((-3,), "−3"),
        ((-0.04, 1), "0,0"),
        ((2.675, 2), "2,68"),
        ((2.5,), "3"),
        ((-2.5,), "−3"),
        ((Decimal("2.4952"), 0, 4), "2,4952"),
        ((2.5, 0, 4), "2,5"),
        ((None,), "—"),
        ((float("nan"),), "—"),
    ],
)
def test_les_nombres_s_ecrivent_comme_a_l_ecran(valeur: tuple[object, ...], attendu: str) -> None:
    """Jumeau de `format.ts` : espace insécable, virgule, « − », jamais « -0 », ARRONDI d'Excel."""
    assert fmt.nombre(*valeur) == attendu  # type: ignore[arg-type]


def test_les_grandeurs_ont_leur_regle() -> None:
    """Kilos, montants, prix, cours, parts, dates (ARCHITECTURE § 9.3)."""
    assert fmt.kg(1234.56) == f"1{NSP}234,56{NSP}kg"
    # Kilos : jusqu'à deux décimales, zéros inutiles enlevés, plafonné à deux (comme l'écran).
    assert fmt.kg(3.15) == f"3,15{NSP}kg" and fmt.kg(3.2) == f"3,2{NSP}kg"
    assert fmt.kg(3) == f"3{NSP}kg" and fmt.kg(26000) == f"26{NSP}000{NSP}kg"
    assert fmt.kg(3.152) == f"3,15{NSP}kg"
    assert fmt.kg_entier(5029.4) == f"5{NSP}029{NSP}kg"
    assert fmt.montant_precis(1234.5, "MAD") == f"1{NSP}234,50{NSP}MAD"
    assert fmt.montant(1234.5, "MAD") == f"1{NSP}235{NSP}MAD"
    assert fmt.prix(0.0011) == "0,0011" and fmt.prix(2.8) == "2,80"
    assert fmt.cours(10.05) == "10,0500" and fmt.part(0.125) == f"12,5{NSP}%"
    assert fmt.nombre(1234.5, 1, langue="en") == "1,234.5"
    assert fmt.nombre(-1234.5, 1, langue="en") == "-1,234.5"
    assert fmt.date_en(date(2026, 10, 8)) == "08 Oct 2026"
    assert fmt.date_fr(date(2026, 10, 8)) == "08/10/2026"
    instant = datetime.fromisoformat("2026-10-08T13:05:00+05:00")
    usine = instant.astimezone(horloge.FUSEAU)
    assert fmt.horodatage(instant) == f"{usine:%d/%m/%Y %H:%M}" != "08/10/2026 13:05"
    assert fmt.horodatage(datetime(2026, 10, 8, 13, 5)) == "08/10/2026 13:05"  # noqa: DTZ001


# ── Étiquettes (route 114) ───────────────────────────────────────────────────────────────────


@pytest.fixture
def base() -> Iterator[Session]:
    """Une session dont les écritures sont validées (la route les lit)."""
    with fabrique()() as s:
        yield s


def _etiquettes(client: TestClient, ids: str) -> tuple[int, str]:
    r = client.get("/api/documents/etiquettes", params={"lots": ids})
    assert r.headers["content-type"].startswith("text/html"), r.text[:200]
    assert r.headers["content-disposition"] == "inline"
    return r.status_code, r.text


def test_l_etiquette_porte_un_qr(base: Session, alimentation: TestClient) -> None:
    """Hérité : test_parcours::test_l_etiquette_porte_un_qr — le QR **décodé** est l'adresse du
    lot (réglage « adresse pour les téléphones ») ; le scan (route 110) de ce texte rend le lot."""
    m = matiere(base, unique("Fil étiqueté"))
    x = lot(base, m, numero=unique("ETQ"))
    entree(base, x, "120.5")
    base.commit()
    with reglages({"adresse_publique": "http://mac-usine:8050/"}):
        statut, html = _etiquettes(alimentation, str(x.id))
    assert statut == 200
    (svg,) = svgs(html)
    lu = lire_qr(svg)
    assert lu == f"http://mac-usine:8050/lot/{x.id}"
    (trouve,) = alimentation.get("/api/lots/scan", params={"code": lu}).json()
    assert trouve["lot_id"] == x.id
    (texte,) = textes(html, "texte")
    assert x.numero in texte and m.reference in texte and "Entré le 08/10/2026" in texte
    assert f"Reste 120,5{NSP}kg à l'impression N° {x.id}" in texte
    assert "@page { size: 100mm 70mm; margin: 4mm; }" in html
    assert "QUARANTAINE" not in html and "MAD" not in html and "prix" not in html.lower()


def test_un_lot_en_quarantaine_ne_sort_pas(base: Session, achats: TestClient) -> None:
    """« QUARANTAINE — NE PAS SORTIR » encadré ; en partie seulement : « dont … en quarantaine »."""
    m = matiere(base, unique("Fil bloqué"))
    tout, part = lot(base, m, numero=unique("QT")), lot(base, m, numero=unique("QP"))
    quarantaine = Magasin(
        code=unique("QUAR"), nom="Quarantaine d'essai", type=TypeMagasin.quarantaine
    )
    base.add(quarantaine)  # à soi : le magasin semé reste vide (essais des référentiels)
    base.flush()
    entree(base, tout, 50, g=quarantaine)
    entree(base, part, 70)
    entree(base, part, 30, g=quarantaine)
    base.commit()
    statut, html = _etiquettes(achats, f"{tout.id},{part.id}")
    assert statut == 200
    assert textes(html, "quarantaine") == [
        "QUARANTAINE — NE PAS SORTIR",
        f"QUARANTAINE — NE PAS SORTIR (dont 30{NSP}kg en quarantaine)",
    ]


def test_etiquette_kilos_a_la_regle_et_bobines(base: Session, achats: TestClient) -> None:
    """ECRANS-PRO « Étiquettes » (an. 28) et § 9.3 : kilos des documents (jusqu'à deux décimales,
    zéros inutiles enlevés, espaces insécables), mètres indicatifs d'un ruban, « ≈ N bobines » au
    poids de bobine du lot (sinon du catalogue) ; rien sans poids de bobine."""
    fil = matiere(base, unique("Fil bobiné"), poids_bobine=Decimal("2.5"))
    mesure = lot(base, fil, numero=unique("BB"), poids_bobine=Decimal("2.4952"))
    catalogue = lot(base, fil, numero=unique("BC"))
    ruban = matiere(base, unique("Ruban"), role_code="Ruban")
    au_metre = lot(base, ruban, numero=unique("RB"))
    entree(base, mesure, "1234.56")
    entree(base, catalogue, "5")
    entree(base, au_metre, "14.3")
    base.commit()
    statut, html = _etiquettes(achats, f"{mesure.id},{catalogue.id},{au_metre.id}")
    assert statut == 200
    reste = [t for x in textes(html, "texte") for t in [x.split("Reste ", 1)[1].split(" N° ")[0]]]
    assert reste == [
        f"1{NSP}234,56{NSP}kg à l'impression ≈{NSP}495{NSP}bobines",
        f"5{NSP}kg à l'impression ≈{NSP}2{NSP}bobines",
        f"14,3{NSP}kg ≈{NSP}1{NSP}021{NSP}ml à l'impression",
    ]
    assert textes(html, "bobines") == [f"≈{NSP}495{NSP}bobines", f"≈{NSP}2{NSP}bobines"]


def test_etiquettes_id_inconnu_signale(base: Session, achats: TestClient) -> None:
    """Hérité : test_defauts_c::test_etiquettes_id_inconnu_signale (C-18) — les identifiants
    inconnus sont dits (écran seulement) ; aucun lot : page HTML 404, jamais un JSON brut."""
    statut, html = _etiquettes(achats, "999999,abc")
    assert statut == 404
    assert textes(html, "aucun") == ["Aucun lot à étiqueter."]
    assert textes(html, "ignores") == ["Ignorés (lots inconnus, sans étiquette) : abc, 999999"]
    assert "<script>" not in html and "imprimer" not in html
    m = matiere(base, unique("Fil connu"))
    x = lot(base, m)
    entree(base, x, 10)
    base.commit()
    statut, html = _etiquettes(achats, f"{x.id},999998")
    assert statut == 200 and "999998" in textes(html, "ignores")[0]
    assert len(svgs(html)) == 1
    assert _etiquettes(achats, "")[0] == 404


def test_l_adresse_localhost_est_signalee(base: Session, direction: TestClient) -> None:
    """Un QR qui mènerait à `localhost` est imprimé, mais l'écran le signale (hors impression)."""
    m = matiere(base, unique("Fil local"))
    x = lot(base, m)
    entree(base, x, 5)
    base.commit()
    with reglages({"adresse_publique": "http://localhost:8050"}):
        _, html = _etiquettes(direction, str(x.id))
    (alerte,) = textes(html, "avertissement")
    assert "un téléphone ne joindrait pas cette adresse" in alerte
    assert lire_qr(svgs(html)[0]) == f"http://localhost:8050/lot/{x.id}"


def test_les_etiquettes_sont_aux_roles_metier(
    administrateur: TestClient, anonyme: TestClient, alimentation: TestClient
) -> None:
    """Route 114 : C ; l'administrateur et l'anonyme en sont exclus."""
    assert administrateur.get("/api/documents/etiquettes?lots=1").status_code == 403
    assert anonyme.get("/api/documents/etiquettes?lots=1").status_code == 401
    r = alimentation.get("/api/documents/etiquettes", params={"lots": "x" * 4001})
    assert r.status_code == 422
