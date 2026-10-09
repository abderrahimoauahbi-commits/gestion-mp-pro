-- Schéma de Gestion MP corrigé (étapes 1 à 19), figé pour les essais de la reprise (lot R1) :
-- pg_dump --schema-only --no-owner --no-privileges d'une copie de la base gestion_mp (9 octobre 2026).


SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

CREATE TABLE public.article (
    id integer NOT NULL,
    reference character varying(160) NOT NULL,
    designation character varying(160) DEFAULT ''::character varying NOT NULL,
    role character varying(32) NOT NULL,
    composition character varying(32),
    type_fil character varying(32),
    titrage character varying(48),
    couleur character varying(64),
    couleur_code character varying(32) DEFAULT ''::character varying NOT NULL,
    unite character varying(4) DEFAULT 'kg'::character varying NOT NULL,
    densite double precision DEFAULT '0'::double precision NOT NULL,
    fournisseur_id integer,
    prix double precision DEFAULT '0'::double precision NOT NULL,
    devise character varying(3) NOT NULL,
    unite_achat character varying(32) DEFAULT 'kg'::character varying NOT NULL,
    contenance_achat double precision DEFAULT '1'::double precision NOT NULL,
    minimum_commande double precision DEFAULT '0'::double precision NOT NULL,
    poids_bobine double precision DEFAULT '0'::double precision NOT NULL,
    bobines_palette double precision DEFAULT '0'::double precision NOT NULL,
    stock_min double precision DEFAULT '0'::double precision NOT NULL,
    couv_min_mois double precision DEFAULT '0'::double precision NOT NULL,
    groupe_equiv character varying(64) DEFAULT ''::character varying NOT NULL,
    priorite_equiv double precision,
    actif boolean DEFAULT true NOT NULL,
    version integer NOT NULL,
    modifie_le timestamp without time zone,
    modifie_par character varying(80) DEFAULT ''::character varying NOT NULL,
    code_douanier character varying(20),
    unite_prix character varying(4) DEFAULT 'kg'::character varying NOT NULL,
    CONSTRAINT article_check CHECK (((stock_min >= (0)::double precision) AND (poids_bobine >= (0)::double precision) AND (bobines_palette >= (0)::double precision))),
    CONSTRAINT article_check1 CHECK (((contenance_achat >= (0)::double precision) AND (minimum_commande >= (0)::double precision))),
    CONSTRAINT article_prix_check CHECK ((prix >= (0)::double precision)),
    CONSTRAINT ck_article_prix_au_metre CHECK ((((unite_prix)::text = 'kg'::text) OR (densite > (0)::double precision))),
    CONSTRAINT ck_article_unite_kg CHECK (((unite)::text = 'kg'::text)),
    CONSTRAINT ck_article_unite_prix CHECK (((unite_prix)::text = ANY (ARRAY[('kg'::character varying)::text, ('ml'::character varying)::text])))
);

CREATE SEQUENCE public.article_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.article_id_seq OWNED BY public.article.id;

CREATE TABLE public.bon_fabrication (
    id integer NOT NULL,
    bon_id integer NOT NULL,
    qualite_id integer NOT NULL,
    m2 double precision NOT NULL,
    CONSTRAINT bon_fabrication_m2_check CHECK ((m2 > (0)::double precision))
);

CREATE SEQUENCE public.bon_fabrication_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.bon_fabrication_id_seq OWNED BY public.bon_fabrication.id;

CREATE TABLE public.bon_ligne (
    id integer NOT NULL,
    bon_id integer NOT NULL,
    article_id integer NOT NULL,
    lot_id integer NOT NULL,
    quantite double precision NOT NULL,
    CONSTRAINT bon_ligne_quantite_check CHECK ((quantite > (0)::double precision))
);

CREATE SEQUENCE public.bon_ligne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.bon_ligne_id_seq OWNED BY public.bon_ligne.id;

CREATE TABLE public.bon_sortie (
    id integer NOT NULL,
    numero character varying(32),
    statut character varying(12) DEFAULT 'brouillon'::character varying NOT NULL,
    date date NOT NULL,
    magasin_id integer NOT NULL,
    metier_id integer,
    commentaire character varying(300) DEFAULT ''::character varying NOT NULL,
    cree_par character varying(80) DEFAULT ''::character varying NOT NULL,
    cree_le timestamp without time zone NOT NULL,
    valide_par character varying(80) DEFAULT ''::character varying NOT NULL,
    valide_le timestamp without time zone,
    theorique text,
    CONSTRAINT bon_sortie_statut_check CHECK (((statut)::text = ANY (ARRAY[('brouillon'::character varying)::text, ('valide'::character varying)::text, ('annule'::character varying)::text])))
);

CREATE SEQUENCE public.bon_sortie_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.bon_sortie_id_seq OWNED BY public.bon_sortie.id;

CREATE TABLE public.code_douanier (
    code character varying(20) NOT NULL,
    libelle character varying(160) DEFAULT ''::character varying NOT NULL,
    taux_droits double precision DEFAULT 0 NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    CONSTRAINT code_douanier_taux_droits_check CHECK (((taux_droits >= (0)::double precision) AND (taux_droits <= (1)::double precision)))
);

CREATE TABLE public.commande (
    id integer NOT NULL,
    numero character varying(32),
    fournisseur_id integer NOT NULL,
    date_commande date NOT NULL,
    date_livraison_prevue date,
    statut character varying(20) DEFAULT 'brouillon'::character varying NOT NULL,
    devise character varying(3) NOT NULL,
    cours double precision DEFAULT '0'::double precision NOT NULL,
    observations text NOT NULL,
    proforma_le date,
    embarquee_le date,
    eta date,
    au_port_le date,
    dedouanee_le date,
    conteneur character varying(60) DEFAULT ''::character varying NOT NULL,
    navire character varying(80) DEFAULT ''::character varying NOT NULL,
    cree_par character varying(80) DEFAULT ''::character varying NOT NULL,
    cree_le timestamp without time zone NOT NULL,
    approuvee_par character varying(80) DEFAULT ''::character varying NOT NULL,
    approuvee_le timestamp without time zone,
    acompte_le date,
    arrivee_usine_le date,
    montant_approuve double precision DEFAULT 0 NOT NULL,
    version_approuvee text DEFAULT ''::text NOT NULL,
    CONSTRAINT commande_statut_check CHECK (((statut)::text = ANY (ARRAY[('brouillon'::character varying)::text, ('a_approuver'::character varying)::text, ('envoyee'::character varying)::text, ('confirmee'::character varying)::text, ('soldee'::character varying)::text, ('annulee'::character varying)::text])))
);

CREATE SEQUENCE public.commande_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.commande_id_seq OWNED BY public.commande.id;

CREATE TABLE public.commande_ligne (
    id integer NOT NULL,
    commande_id integer NOT NULL,
    article_id integer NOT NULL,
    quantite double precision NOT NULL,
    unite_achat character varying(32) DEFAULT 'kg'::character varying NOT NULL,
    contenance double precision DEFAULT '1'::double precision NOT NULL,
    prix double precision DEFAULT '0'::double precision NOT NULL,
    prix_confirme boolean NOT NULL,
    confirme_le timestamp without time zone,
    confirme_par character varying(80) DEFAULT ''::character varying NOT NULL,
    CONSTRAINT commande_ligne_check CHECK (((quantite > (0)::double precision) AND (contenance > (0)::double precision) AND (prix >= (0)::double precision)))
);

CREATE SEQUENCE public.commande_ligne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.commande_ligne_id_seq OWNED BY public.commande_ligne.id;

CREATE TABLE public.composition (
    code character varying(32) NOT NULL,
    libelle character varying(120) DEFAULT ''::character varying NOT NULL,
    famille character varying(64) DEFAULT ''::character varying NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    composition_detaillee character varying(160) DEFAULT ''::character varying NOT NULL,
    commentaire text DEFAULT ''::text NOT NULL
);

CREATE TABLE public.compteur (
    id integer NOT NULL,
    serie character varying(10) NOT NULL,
    annee integer NOT NULL,
    dernier integer NOT NULL
);

CREATE SEQUENCE public.compteur_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.compteur_id_seq OWNED BY public.compteur.id;

CREATE TABLE public.couleur (
    code character varying(64) NOT NULL,
    libelle character varying(120) DEFAULT ''::character varying NOT NULL,
    famille character varying(64) DEFAULT ''::character varying NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    commentaire text DEFAULT ''::text NOT NULL
);

CREATE TABLE public.devise (
    code character varying(3) NOT NULL,
    nom character varying(40) DEFAULT ''::character varying NOT NULL,
    taux double precision NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    CONSTRAINT devise_taux_check CHECK ((taux > (0)::double precision))
);

CREATE TABLE public.dossier (
    id integer NOT NULL,
    numero character varying(16) NOT NULL,
    libelle character varying(160) DEFAULT ''::character varying NOT NULL,
    date_arrivee date,
    banque character varying(32) DEFAULT ''::character varying NOT NULL,
    statut character varying(8) DEFAULT 'ouvert'::character varying NOT NULL,
    clos_le timestamp without time zone,
    commentaire text NOT NULL,
    facture_id integer,
    CONSTRAINT dossier_statut_check CHECK (((statut)::text = ANY (ARRAY[('ouvert'::character varying)::text, ('clos'::character varying)::text])))
);

CREATE TABLE public.dossier_charge (
    id integer NOT NULL,
    dossier_id integer NOT NULL,
    poste character varying(16) NOT NULL,
    montant double precision DEFAULT '0'::double precision NOT NULL,
    ligne_id integer,
    piece character varying(64) DEFAULT ''::character varying NOT NULL,
    commentaire character varying(300) DEFAULT ''::character varying NOT NULL,
    prestataire character varying(120) DEFAULT ''::character varying NOT NULL,
    date_piece date,
    echeance date,
    payee_le date
);

CREATE SEQUENCE public.dossier_charge_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.dossier_charge_id_seq OWNED BY public.dossier_charge.id;

CREATE TABLE public.dossier_charge_part (
    charge_id integer NOT NULL,
    ligne_id integer NOT NULL,
    montant double precision DEFAULT '0'::double precision NOT NULL
);

CREATE SEQUENCE public.dossier_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.dossier_id_seq OWNED BY public.dossier.id;

CREATE TABLE public.dossier_ligne (
    id integer NOT NULL,
    dossier_id integer NOT NULL,
    reception_ligne_id integer,
    article_id integer NOT NULL,
    lot_id integer,
    fournisseur_id integer,
    quantite double precision DEFAULT '0'::double precision NOT NULL,
    valeur_devise double precision DEFAULT '0'::double precision NOT NULL,
    devise character varying(3) DEFAULT 'MAD'::character varying NOT NULL,
    cours double precision DEFAULT '0'::double precision NOT NULL,
    commentaire character varying(300) DEFAULT ''::character varying NOT NULL,
    poids_kg double precision,
    cours_fige_cloture boolean DEFAULT false NOT NULL,
    CONSTRAINT dossier_ligne_check CHECK (((quantite >= (0)::double precision) AND (valeur_devise >= (0)::double precision) AND (cours >= (0)::double precision)))
);

CREATE SEQUENCE public.dossier_ligne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.dossier_ligne_id_seq OWNED BY public.dossier_ligne.id;

CREATE TABLE public.facture (
    id integer NOT NULL,
    fournisseur_id integer NOT NULL,
    numero character varying(64) NOT NULL,
    date date,
    montant double precision DEFAULT '0'::double precision NOT NULL,
    devise character varying(3) NOT NULL,
    echeance date,
    payee_le date,
    CONSTRAINT facture_montant_check CHECK ((montant >= (0)::double precision))
);

CREATE SEQUENCE public.facture_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.facture_id_seq OWNED BY public.facture.id;

CREATE TABLE public.fil_monte (
    id integer NOT NULL,
    metier_id integer NOT NULL,
    etage integer NOT NULL,
    article_id integer NOT NULL,
    metres double precision DEFAULT '0'::double precision NOT NULL,
    pourcentage double precision DEFAULT '100'::double precision NOT NULL,
    commentaire character varying(300) DEFAULT ''::character varying NOT NULL,
    CONSTRAINT fil_monte_check CHECK (((metres >= (0)::double precision) AND ((pourcentage >= (0)::double precision) AND (pourcentage <= (100)::double precision))))
);

CREATE SEQUENCE public.fil_monte_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.fil_monte_id_seq OWNED BY public.fil_monte.id;

CREATE TABLE public.fournisseur (
    id integer NOT NULL,
    nom character varying(160) NOT NULL,
    code character varying(32) DEFAULT ''::character varying NOT NULL,
    pays character varying(80) DEFAULT ''::character varying NOT NULL,
    contact character varying(120) DEFAULT ''::character varying NOT NULL,
    telephone character varying(60) DEFAULT ''::character varying NOT NULL,
    email character varying(160) DEFAULT ''::character varying NOT NULL,
    devise character varying(3) NOT NULL,
    delai_jours double precision DEFAULT '60'::double precision NOT NULL,
    couverture_commande_jours double precision DEFAULT '0'::double precision NOT NULL,
    mode_paiement character varying(40) DEFAULT ''::character varying NOT NULL,
    delai_paiement_jours double precision DEFAULT '0'::double precision NOT NULL,
    conditions_paiement character varying(160) DEFAULT ''::character varying NOT NULL,
    incoterm character varying(20) DEFAULT ''::character varying NOT NULL,
    notes text NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    port_chargement character varying(80) DEFAULT ''::character varying NOT NULL,
    banque character varying(120) DEFAULT ''::character varying NOT NULL,
    CONSTRAINT fournisseur_couverture_commande_jours_check CHECK ((couverture_commande_jours >= (0)::double precision)),
    CONSTRAINT fournisseur_delai_jours_check CHECK ((delai_jours > (0)::double precision)),
    CONSTRAINT fournisseur_delai_paiement_jours_check CHECK ((delai_paiement_jours >= (0)::double precision))
);

CREATE SEQUENCE public.fournisseur_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.fournisseur_id_seq OWNED BY public.fournisseur.id;

CREATE TABLE public.indicateur_jour (
    jour date NOT NULL,
    contenu text NOT NULL
);

CREATE TABLE public.inventaire (
    id integer NOT NULL,
    numero character varying(32) NOT NULL,
    libelle character varying(120) DEFAULT ''::character varying NOT NULL,
    statut character varying(10) DEFAULT 'ouvert'::character varying NOT NULL,
    date date NOT NULL,
    magasin_id integer,
    tolerance double precision DEFAULT '0.02'::double precision NOT NULL,
    cree_par character varying(80) DEFAULT ''::character varying NOT NULL,
    valide_par character varying(80) DEFAULT ''::character varying NOT NULL,
    valide_le timestamp without time zone,
    CONSTRAINT ck_inventaire_statut CHECK (((statut)::text = ANY (ARRAY[('ouvert'::character varying)::text, ('valide'::character varying)::text, ('abandonne'::character varying)::text, ('annule'::character varying)::text])))
);

CREATE SEQUENCE public.inventaire_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.inventaire_id_seq OWNED BY public.inventaire.id;

CREATE TABLE public.inventaire_ligne (
    id integer NOT NULL,
    inventaire_id integer NOT NULL,
    lot_id integer,
    magasin_id integer NOT NULL,
    theorique double precision DEFAULT '0'::double precision NOT NULL,
    compte double precision,
    justification character varying(300) DEFAULT ''::character varying NOT NULL,
    nb_palettes double precision,
    nb_bobines double precision,
    second_compte double precision,
    second_par character varying(80) DEFAULT ''::character varying NOT NULL,
    article_id integer,
    lot_numero character varying(80) DEFAULT ''::character varying NOT NULL
);

CREATE SEQUENCE public.inventaire_ligne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.inventaire_ligne_id_seq OWNED BY public.inventaire_ligne.id;

CREATE TABLE public.journal (
    id integer NOT NULL,
    quand timestamp without time zone NOT NULL,
    utilisateur character varying(80) DEFAULT ''::character varying NOT NULL,
    role character varying(20) DEFAULT ''::character varying NOT NULL,
    action character varying(80) DEFAULT ''::character varying NOT NULL,
    objet character varying(40) DEFAULT ''::character varying NOT NULL,
    objet_id integer,
    detail text NOT NULL
);

CREATE SEQUENCE public.journal_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.journal_id_seq OWNED BY public.journal.id;

CREATE TABLE public.lot (
    id integer NOT NULL,
    article_id integer NOT NULL,
    numero character varying(80) NOT NULL,
    fournisseur_id integer,
    entre_le date NOT NULL,
    poids_bobine double precision DEFAULT '0'::double precision NOT NULL,
    commentaire character varying(300) DEFAULT ''::character varying NOT NULL
);

CREATE SEQUENCE public.lot_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.lot_id_seq OWNED BY public.lot.id;

CREATE TABLE public.magasin (
    id integer NOT NULL,
    code character varying(64) NOT NULL,
    nom character varying(120) DEFAULT ''::character varying NOT NULL,
    type character varying(20) DEFAULT 'Stock courant'::character varying NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    contenu character varying(120) DEFAULT ''::character varying NOT NULL,
    CONSTRAINT magasin_type_check CHECK (((type)::text = ANY (ARRAY[('Stock courant'::character varying)::text, ('Quarantaine'::character varying)::text])))
);

CREATE SEQUENCE public.magasin_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.magasin_id_seq OWNED BY public.magasin.id;

CREATE TABLE public.metier (
    id integer NOT NULL,
    code character varying(32) NOT NULL,
    nom character varying(120) DEFAULT ''::character varying NOT NULL,
    laize double precision DEFAULT '4.2'::double precision NOT NULL,
    densite double precision DEFAULT '0'::double precision NOT NULL,
    etages integer NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    commentaire text DEFAULT ''::text NOT NULL,
    CONSTRAINT metier_check CHECK (((laize >= (0)::double precision) AND (densite >= (0)::double precision))),
    CONSTRAINT metier_etages_check CHECK (((etages >= 1) AND (etages <= 40)))
);

CREATE SEQUENCE public.metier_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.metier_id_seq OWNED BY public.metier.id;

CREATE TABLE public.mouvement (
    id integer NOT NULL,
    date_effet date NOT NULL,
    date_saisie timestamp without time zone NOT NULL,
    type character varying(20) NOT NULL,
    article_id integer NOT NULL,
    lot_id integer NOT NULL,
    magasin_id integer NOT NULL,
    quantite double precision NOT NULL,
    prix double precision DEFAULT '0'::double precision NOT NULL,
    devise character varying(3) DEFAULT 'MAD'::character varying NOT NULL,
    document character varying(20) DEFAULT ''::character varying NOT NULL,
    document_id integer,
    document_numero character varying(40) DEFAULT ''::character varying NOT NULL,
    ordre_id integer,
    paire integer,
    motif character varying(80) DEFAULT ''::character varying NOT NULL,
    commentaire character varying(300) DEFAULT ''::character varying NOT NULL,
    auteur character varying(80) DEFAULT ''::character varying NOT NULL,
    contrepasse_id integer,
    cours double precision DEFAULT 0 NOT NULL,
    CONSTRAINT mouvement_quantite_check CHECK ((quantite <> (0)::double precision)),
    CONSTRAINT mouvement_type_check CHECK (((type)::text = ANY (ARRAY[('OUVERTURE'::character varying)::text, ('RECEPTION'::character varying)::text, ('SORTIE'::character varying)::text, ('RETOUR_MACHINE'::character varying)::text, ('RETOUR_FOURNISSEUR'::character varying)::text, ('AJUSTEMENT'::character varying)::text, ('TRANSFERT'::character varying)::text])))
);

CREATE SEQUENCE public.mouvement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.mouvement_id_seq OWNED BY public.mouvement.id;

CREATE TABLE public.operation (
    id integer NOT NULL,
    numero character varying(32),
    type character varying(20) NOT NULL,
    statut character varying(12) DEFAULT 'brouillon'::character varying NOT NULL,
    date date NOT NULL,
    bon_id integer,
    fournisseur_id integer,
    motif character varying(80) DEFAULT ''::character varying NOT NULL,
    commentaire character varying(300) DEFAULT ''::character varying NOT NULL,
    cree_par character varying(80) DEFAULT ''::character varying NOT NULL,
    cree_le timestamp without time zone NOT NULL,
    validee_par character varying(80) DEFAULT ''::character varying NOT NULL,
    validee_le timestamp without time zone,
    CONSTRAINT operation_statut_check CHECK (((statut)::text = ANY (ARRAY[('brouillon'::character varying)::text, ('validee'::character varying)::text, ('annulee'::character varying)::text]))),
    CONSTRAINT operation_type_check CHECK (((type)::text = ANY (ARRAY[('ouverture'::character varying)::text, ('retour_machine'::character varying)::text, ('transfert'::character varying)::text, ('ajustement'::character varying)::text, ('retour_fournisseur'::character varying)::text])))
);

CREATE SEQUENCE public.operation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.operation_id_seq OWNED BY public.operation.id;

CREATE TABLE public.operation_ligne (
    id integer NOT NULL,
    operation_id integer NOT NULL,
    article_id integer NOT NULL,
    lot_id integer,
    lot_numero character varying(80) DEFAULT ''::character varying NOT NULL,
    magasin_id integer NOT NULL,
    magasin_destination_id integer,
    quantite double precision NOT NULL,
    prix double precision DEFAULT '0'::double precision NOT NULL,
    devise character varying(3) DEFAULT 'MAD'::character varying NOT NULL,
    CONSTRAINT operation_ligne_check CHECK (((quantite <> (0)::double precision) AND (prix >= (0)::double precision)))
);

CREATE SEQUENCE public.operation_ligne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.operation_ligne_id_seq OWNED BY public.operation_ligne.id;

CREATE TABLE public.parametre (
    cle character varying(60) NOT NULL,
    valeur text NOT NULL,
    modifie_le timestamp without time zone NOT NULL,
    modifie_par character varying(80) DEFAULT ''::character varying NOT NULL
);

CREATE TABLE public.parametre_historique (
    id integer NOT NULL,
    cle character varying(60) NOT NULL,
    valeur text NOT NULL,
    quand timestamp without time zone NOT NULL,
    par character varying(80) DEFAULT ''::character varying NOT NULL
);

CREATE SEQUENCE public.parametre_historique_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.parametre_historique_id_seq OWNED BY public.parametre_historique.id;

CREATE TABLE public.piece_jointe (
    id integer NOT NULL,
    objet character varying(20) NOT NULL,
    objet_id integer NOT NULL,
    nom character varying(200) DEFAULT ''::character varying NOT NULL,
    type_mime character varying(100) DEFAULT ''::character varying NOT NULL,
    taille integer NOT NULL,
    chemin character varying(300) DEFAULT ''::character varying NOT NULL,
    par character varying(80) DEFAULT ''::character varying NOT NULL,
    quand timestamp without time zone NOT NULL
);

CREATE SEQUENCE public.piece_jointe_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.piece_jointe_id_seq OWNED BY public.piece_jointe.id;

CREATE TABLE public.poste_frais (
    code character varying(16) NOT NULL,
    libelle character varying(80) DEFAULT ''::character varying NOT NULL,
    recuperable boolean NOT NULL,
    ordre integer NOT NULL,
    cle character varying(8) DEFAULT 'valeur'::character varying NOT NULL
);

CREATE TABLE public.qualite (
    id integer NOT NULL,
    code character varying(32) NOT NULL,
    nom character varying(120) DEFAULT ''::character varying NOT NULL,
    base_mensuelle double precision DEFAULT '0'::double precision NOT NULL,
    actif boolean DEFAULT true NOT NULL
);

CREATE SEQUENCE public.qualite_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.qualite_id_seq OWNED BY public.qualite.id;

CREATE TABLE public.qualite_poids (
    id integer NOT NULL,
    qualite_id integer NOT NULL,
    role character varying(32) NOT NULL,
    poids double precision DEFAULT '0'::double precision NOT NULL,
    CONSTRAINT qualite_poids_poids_check CHECK ((poids >= (0)::double precision))
);

CREATE SEQUENCE public.qualite_poids_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.qualite_poids_id_seq OWNED BY public.qualite_poids.id;

CREATE TABLE public.qualite_saison (
    id integer NOT NULL,
    qualite_id integer NOT NULL,
    mois integer NOT NULL,
    coefficient double precision DEFAULT '1'::double precision NOT NULL,
    CONSTRAINT qualite_saison_coefficient_check CHECK ((coefficient >= (0)::double precision)),
    CONSTRAINT qualite_saison_mois_check CHECK (((mois >= 1) AND (mois <= 12)))
);

CREATE SEQUENCE public.qualite_saison_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.qualite_saison_id_seq OWNED BY public.qualite_saison.id;

CREATE TABLE public.reception (
    id integer NOT NULL,
    numero character varying(32),
    statut character varying(12) DEFAULT 'brouillon'::character varying NOT NULL,
    date date NOT NULL,
    fournisseur_id integer NOT NULL,
    numero_bl character varying(64) DEFAULT ''::character varying NOT NULL,
    facture_id integer,
    observations text NOT NULL,
    cree_par character varying(80) DEFAULT ''::character varying NOT NULL,
    cree_le timestamp without time zone NOT NULL,
    validee_par character varying(80) DEFAULT ''::character varying NOT NULL,
    validee_le timestamp without time zone,
    controle_par character varying(80) DEFAULT ''::character varying NOT NULL,
    CONSTRAINT reception_statut_check CHECK (((statut)::text = ANY (ARRAY[('brouillon'::character varying)::text, ('validee'::character varying)::text, ('annulee'::character varying)::text])))
);

CREATE SEQUENCE public.reception_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.reception_id_seq OWNED BY public.reception.id;

CREATE TABLE public.reception_ligne (
    id integer NOT NULL,
    reception_id integer NOT NULL,
    commande_ligne_id integer,
    article_id integer NOT NULL,
    lot_numero character varying(80) DEFAULT ''::character varying NOT NULL,
    quantite_attendue double precision DEFAULT '0'::double precision NOT NULL,
    quantite_bl double precision DEFAULT '0'::double precision NOT NULL,
    quantite_pesee double precision DEFAULT '0'::double precision NOT NULL,
    nb_palettes double precision DEFAULT '0'::double precision NOT NULL,
    bobines_en_plus double precision DEFAULT '0'::double precision NOT NULL,
    nb_bobines double precision DEFAULT '0'::double precision NOT NULL,
    magasin_id integer,
    qualite character varying(10) DEFAULT 'conforme'::character varying NOT NULL,
    observations character varying(300) DEFAULT ''::character varying NOT NULL,
    prix double precision DEFAULT '0'::double precision NOT NULL,
    devise character varying(3) DEFAULT 'MAD'::character varying NOT NULL,
    lot_id integer,
    CONSTRAINT reception_ligne_check CHECK (((quantite_pesee >= (0)::double precision) AND (quantite_bl >= (0)::double precision) AND (nb_palettes >= (0)::double precision) AND (bobines_en_plus >= (0)::double precision))),
    CONSTRAINT reception_ligne_qualite_check CHECK (((qualite)::text = ANY (ARRAY[('conforme'::character varying)::text, ('reserve'::character varying)::text, ('refuse'::character varying)::text])))
);

CREATE SEQUENCE public.reception_ligne_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.reception_ligne_id_seq OWNED BY public.reception_ligne.id;

CREATE TABLE public.recette (
    id integer NOT NULL,
    qualite_id integer NOT NULL,
    article_id integer NOT NULL,
    pourcentage double precision DEFAULT '0'::double precision NOT NULL,
    CONSTRAINT recette_pourcentage_check CHECK (((pourcentage >= (0)::double precision) AND (pourcentage <= (100)::double precision)))
);

CREATE SEQUENCE public.recette_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.recette_id_seq OWNED BY public.recette.id;

CREATE TABLE public.recette_version (
    id integer NOT NULL,
    qualite_id integer NOT NULL,
    quand timestamp without time zone NOT NULL,
    par character varying(80) DEFAULT ''::character varying NOT NULL,
    contenu text NOT NULL,
    poids text
);

CREATE SEQUENCE public.recette_version_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.recette_version_id_seq OWNED BY public.recette_version.id;

CREATE TABLE public.reclamation (
    id integer NOT NULL,
    numero character varying(32) NOT NULL,
    fournisseur_id integer NOT NULL,
    reception_id integer,
    lot_id integer,
    motif character varying(80) DEFAULT ''::character varying NOT NULL,
    description text NOT NULL,
    quantite double precision DEFAULT '0'::double precision NOT NULL,
    montant_demande double precision DEFAULT '0'::double precision NOT NULL,
    devise character varying(3) DEFAULT 'MAD'::character varying NOT NULL,
    reponse text NOT NULL,
    issue character varying(40) DEFAULT ''::character varying NOT NULL,
    montant_obtenu double precision DEFAULT '0'::double precision NOT NULL,
    statut character varying(8) DEFAULT 'ouverte'::character varying NOT NULL,
    ouverte_le date NOT NULL,
    close_le date,
    cree_par character varying(80) DEFAULT ''::character varying NOT NULL,
    reception_ligne_id integer,
    CONSTRAINT reclamation_statut_check CHECK (((statut)::text = ANY (ARRAY[('ouverte'::character varying)::text, ('close'::character varying)::text])))
);

CREATE SEQUENCE public.reclamation_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.reclamation_id_seq OWNED BY public.reclamation.id;

CREATE TABLE public.role_nomenclature (
    code character varying(32) NOT NULL,
    lineaire boolean NOT NULL,
    ordre integer NOT NULL
);

CREATE TABLE public.schema_version (
    numero integer NOT NULL,
    libelle text NOT NULL,
    applique_le timestamp without time zone DEFAULT now() NOT NULL
);

CREATE TABLE public.session_ouverte (
    empreinte character varying(64) NOT NULL,
    utilisateur_id integer NOT NULL,
    expire_le timestamp without time zone NOT NULL
);

CREATE TABLE public.signalement (
    id integer NOT NULL,
    quand timestamp without time zone NOT NULL,
    par character varying(80) DEFAULT ''::character varying NOT NULL,
    article_id integer,
    texte character varying(500) DEFAULT ''::character varying NOT NULL,
    urgence character varying(12) DEFAULT 'normale'::character varying NOT NULL,
    traite_par character varying(80) DEFAULT ''::character varying NOT NULL,
    traite_le timestamp without time zone,
    reponse character varying(500) DEFAULT ''::character varying NOT NULL,
    par_id integer
);

CREATE SEQUENCE public.signalement_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.signalement_id_seq OWNED BY public.signalement.id;

CREATE TABLE public.solde (
    lot_id integer NOT NULL,
    magasin_id integer NOT NULL,
    quantite double precision DEFAULT '0'::double precision NOT NULL,
    CONSTRAINT ck_solde_positif CHECK ((quantite >= ('-0.0005'::numeric)::double precision))
);

CREATE TABLE public.tentative (
    identifiant character varying(40) NOT NULL,
    echecs integer NOT NULL,
    bloque_jusqua timestamp without time zone
);

CREATE TABLE public.titrage (
    code character varying(48) NOT NULL,
    valeur character varying(32) DEFAULT ''::character varying NOT NULL,
    unite character varying(16) DEFAULT ''::character varying NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    commentaire text DEFAULT ''::text NOT NULL
);

CREATE TABLE public.type_fil (
    code character varying(32) NOT NULL,
    libelle character varying(120) DEFAULT ''::character varying NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    commentaire text DEFAULT ''::text NOT NULL
);

CREATE TABLE public.utilisateur (
    id integer NOT NULL,
    identifiant character varying(40) NOT NULL,
    nom character varying(80) DEFAULT ''::character varying NOT NULL,
    role character varying(20) NOT NULL,
    email character varying(120) DEFAULT ''::character varying NOT NULL,
    empreinte character varying(200) DEFAULT ''::character varying NOT NULL,
    actif boolean DEFAULT true NOT NULL,
    cree_le timestamp without time zone NOT NULL,
    vu_le timestamp without time zone,
    CONSTRAINT utilisateur_role_check CHECK (((role)::text = ANY (ARRAY[('direction'::character varying)::text, ('achats'::character varying)::text, ('alimentation'::character varying)::text])))
);

CREATE SEQUENCE public.utilisateur_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

ALTER SEQUENCE public.utilisateur_id_seq OWNED BY public.utilisateur.id;

ALTER TABLE ONLY public.article ALTER COLUMN id SET DEFAULT nextval('public.article_id_seq'::regclass);

ALTER TABLE ONLY public.bon_fabrication ALTER COLUMN id SET DEFAULT nextval('public.bon_fabrication_id_seq'::regclass);

ALTER TABLE ONLY public.bon_ligne ALTER COLUMN id SET DEFAULT nextval('public.bon_ligne_id_seq'::regclass);

ALTER TABLE ONLY public.bon_sortie ALTER COLUMN id SET DEFAULT nextval('public.bon_sortie_id_seq'::regclass);

ALTER TABLE ONLY public.commande ALTER COLUMN id SET DEFAULT nextval('public.commande_id_seq'::regclass);

ALTER TABLE ONLY public.commande_ligne ALTER COLUMN id SET DEFAULT nextval('public.commande_ligne_id_seq'::regclass);

ALTER TABLE ONLY public.compteur ALTER COLUMN id SET DEFAULT nextval('public.compteur_id_seq'::regclass);

ALTER TABLE ONLY public.dossier ALTER COLUMN id SET DEFAULT nextval('public.dossier_id_seq'::regclass);

ALTER TABLE ONLY public.dossier_charge ALTER COLUMN id SET DEFAULT nextval('public.dossier_charge_id_seq'::regclass);

ALTER TABLE ONLY public.dossier_ligne ALTER COLUMN id SET DEFAULT nextval('public.dossier_ligne_id_seq'::regclass);

ALTER TABLE ONLY public.facture ALTER COLUMN id SET DEFAULT nextval('public.facture_id_seq'::regclass);

ALTER TABLE ONLY public.fil_monte ALTER COLUMN id SET DEFAULT nextval('public.fil_monte_id_seq'::regclass);

ALTER TABLE ONLY public.fournisseur ALTER COLUMN id SET DEFAULT nextval('public.fournisseur_id_seq'::regclass);

ALTER TABLE ONLY public.inventaire ALTER COLUMN id SET DEFAULT nextval('public.inventaire_id_seq'::regclass);

ALTER TABLE ONLY public.inventaire_ligne ALTER COLUMN id SET DEFAULT nextval('public.inventaire_ligne_id_seq'::regclass);

ALTER TABLE ONLY public.journal ALTER COLUMN id SET DEFAULT nextval('public.journal_id_seq'::regclass);

ALTER TABLE ONLY public.lot ALTER COLUMN id SET DEFAULT nextval('public.lot_id_seq'::regclass);

ALTER TABLE ONLY public.magasin ALTER COLUMN id SET DEFAULT nextval('public.magasin_id_seq'::regclass);

ALTER TABLE ONLY public.metier ALTER COLUMN id SET DEFAULT nextval('public.metier_id_seq'::regclass);

ALTER TABLE ONLY public.mouvement ALTER COLUMN id SET DEFAULT nextval('public.mouvement_id_seq'::regclass);

ALTER TABLE ONLY public.operation ALTER COLUMN id SET DEFAULT nextval('public.operation_id_seq'::regclass);

ALTER TABLE ONLY public.operation_ligne ALTER COLUMN id SET DEFAULT nextval('public.operation_ligne_id_seq'::regclass);

ALTER TABLE ONLY public.parametre_historique ALTER COLUMN id SET DEFAULT nextval('public.parametre_historique_id_seq'::regclass);

ALTER TABLE ONLY public.piece_jointe ALTER COLUMN id SET DEFAULT nextval('public.piece_jointe_id_seq'::regclass);

ALTER TABLE ONLY public.qualite ALTER COLUMN id SET DEFAULT nextval('public.qualite_id_seq'::regclass);

ALTER TABLE ONLY public.qualite_poids ALTER COLUMN id SET DEFAULT nextval('public.qualite_poids_id_seq'::regclass);

ALTER TABLE ONLY public.qualite_saison ALTER COLUMN id SET DEFAULT nextval('public.qualite_saison_id_seq'::regclass);

ALTER TABLE ONLY public.reception ALTER COLUMN id SET DEFAULT nextval('public.reception_id_seq'::regclass);

ALTER TABLE ONLY public.reception_ligne ALTER COLUMN id SET DEFAULT nextval('public.reception_ligne_id_seq'::regclass);

ALTER TABLE ONLY public.recette ALTER COLUMN id SET DEFAULT nextval('public.recette_id_seq'::regclass);

ALTER TABLE ONLY public.recette_version ALTER COLUMN id SET DEFAULT nextval('public.recette_version_id_seq'::regclass);

ALTER TABLE ONLY public.reclamation ALTER COLUMN id SET DEFAULT nextval('public.reclamation_id_seq'::regclass);

ALTER TABLE ONLY public.signalement ALTER COLUMN id SET DEFAULT nextval('public.signalement_id_seq'::regclass);

ALTER TABLE ONLY public.utilisateur ALTER COLUMN id SET DEFAULT nextval('public.utilisateur_id_seq'::regclass);

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_reference_key UNIQUE (reference);

ALTER TABLE ONLY public.bon_fabrication
    ADD CONSTRAINT bon_fabrication_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.bon_ligne
    ADD CONSTRAINT bon_ligne_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.bon_sortie
    ADD CONSTRAINT bon_sortie_numero_key UNIQUE (numero);

ALTER TABLE ONLY public.bon_sortie
    ADD CONSTRAINT bon_sortie_pkey PRIMARY KEY (id);

ALTER TABLE public.qualite
    ADD CONSTRAINT ck_qualite_base_nombre CHECK ((base_mensuelle <> 'NaN'::double precision)) NOT VALID;

ALTER TABLE public.qualite_poids
    ADD CONSTRAINT ck_qualite_poids_nombre CHECK ((poids <> 'NaN'::double precision)) NOT VALID;

ALTER TABLE public.qualite_saison
    ADD CONSTRAINT ck_qualite_saison_nombre CHECK ((coefficient <> 'NaN'::double precision)) NOT VALID;

ALTER TABLE ONLY public.code_douanier
    ADD CONSTRAINT code_douanier_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.commande_ligne
    ADD CONSTRAINT commande_ligne_commande_id_article_id_key UNIQUE (commande_id, article_id);

ALTER TABLE ONLY public.commande_ligne
    ADD CONSTRAINT commande_ligne_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.commande
    ADD CONSTRAINT commande_numero_key UNIQUE (numero);

ALTER TABLE ONLY public.commande
    ADD CONSTRAINT commande_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.composition
    ADD CONSTRAINT composition_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.compteur
    ADD CONSTRAINT compteur_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.compteur
    ADD CONSTRAINT compteur_serie_annee_key UNIQUE (serie, annee);

ALTER TABLE ONLY public.couleur
    ADD CONSTRAINT couleur_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.devise
    ADD CONSTRAINT devise_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.dossier_charge_part
    ADD CONSTRAINT dossier_charge_part_pkey PRIMARY KEY (charge_id, ligne_id);

ALTER TABLE ONLY public.dossier_charge
    ADD CONSTRAINT dossier_charge_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dossier_ligne
    ADD CONSTRAINT dossier_ligne_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.dossier_ligne
    ADD CONSTRAINT dossier_ligne_reception_ligne_id_key UNIQUE (reception_ligne_id);

ALTER TABLE ONLY public.dossier
    ADD CONSTRAINT dossier_numero_key UNIQUE (numero);

ALTER TABLE ONLY public.dossier
    ADD CONSTRAINT dossier_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.facture
    ADD CONSTRAINT facture_fournisseur_id_numero_key UNIQUE (fournisseur_id, numero);

ALTER TABLE ONLY public.facture
    ADD CONSTRAINT facture_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.fil_monte
    ADD CONSTRAINT fil_monte_metier_id_etage_article_id_key UNIQUE (metier_id, etage, article_id);

ALTER TABLE ONLY public.fil_monte
    ADD CONSTRAINT fil_monte_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.fournisseur
    ADD CONSTRAINT fournisseur_nom_key UNIQUE (nom);

ALTER TABLE ONLY public.fournisseur
    ADD CONSTRAINT fournisseur_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.indicateur_jour
    ADD CONSTRAINT indicateur_jour_pkey PRIMARY KEY (jour);

ALTER TABLE ONLY public.inventaire_ligne
    ADD CONSTRAINT inventaire_ligne_inventaire_id_lot_id_magasin_id_key UNIQUE (inventaire_id, lot_id, magasin_id);

ALTER TABLE ONLY public.inventaire_ligne
    ADD CONSTRAINT inventaire_ligne_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.inventaire
    ADD CONSTRAINT inventaire_numero_key UNIQUE (numero);

ALTER TABLE ONLY public.inventaire
    ADD CONSTRAINT inventaire_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.journal
    ADD CONSTRAINT journal_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.lot
    ADD CONSTRAINT lot_article_id_numero_key UNIQUE (article_id, numero);

ALTER TABLE ONLY public.lot
    ADD CONSTRAINT lot_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.magasin
    ADD CONSTRAINT magasin_code_key UNIQUE (code);

ALTER TABLE ONLY public.magasin
    ADD CONSTRAINT magasin_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.metier
    ADD CONSTRAINT metier_code_key UNIQUE (code);

ALTER TABLE ONLY public.metier
    ADD CONSTRAINT metier_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.mouvement
    ADD CONSTRAINT mouvement_contrepasse_id_key UNIQUE (contrepasse_id);

ALTER TABLE ONLY public.mouvement
    ADD CONSTRAINT mouvement_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.operation_ligne
    ADD CONSTRAINT operation_ligne_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.operation
    ADD CONSTRAINT operation_numero_key UNIQUE (numero);

ALTER TABLE ONLY public.operation
    ADD CONSTRAINT operation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.parametre_historique
    ADD CONSTRAINT parametre_historique_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.parametre
    ADD CONSTRAINT parametre_pkey PRIMARY KEY (cle);

ALTER TABLE ONLY public.piece_jointe
    ADD CONSTRAINT piece_jointe_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.poste_frais
    ADD CONSTRAINT poste_frais_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.qualite
    ADD CONSTRAINT qualite_code_key UNIQUE (code);

ALTER TABLE ONLY public.qualite
    ADD CONSTRAINT qualite_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.qualite_poids
    ADD CONSTRAINT qualite_poids_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.qualite_poids
    ADD CONSTRAINT qualite_poids_qualite_id_role_key UNIQUE (qualite_id, role);

ALTER TABLE ONLY public.qualite_saison
    ADD CONSTRAINT qualite_saison_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.qualite_saison
    ADD CONSTRAINT qualite_saison_qualite_id_mois_key UNIQUE (qualite_id, mois);

ALTER TABLE ONLY public.reception_ligne
    ADD CONSTRAINT reception_ligne_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.reception
    ADD CONSTRAINT reception_numero_key UNIQUE (numero);

ALTER TABLE ONLY public.reception
    ADD CONSTRAINT reception_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.recette
    ADD CONSTRAINT recette_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.recette
    ADD CONSTRAINT recette_qualite_id_article_id_key UNIQUE (qualite_id, article_id);

ALTER TABLE ONLY public.recette_version
    ADD CONSTRAINT recette_version_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.reclamation
    ADD CONSTRAINT reclamation_numero_key UNIQUE (numero);

ALTER TABLE ONLY public.reclamation
    ADD CONSTRAINT reclamation_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.role_nomenclature
    ADD CONSTRAINT role_nomenclature_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.schema_version
    ADD CONSTRAINT schema_version_pkey PRIMARY KEY (numero);

ALTER TABLE ONLY public.session_ouverte
    ADD CONSTRAINT session_ouverte_pkey PRIMARY KEY (empreinte);

ALTER TABLE ONLY public.signalement
    ADD CONSTRAINT signalement_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.solde
    ADD CONSTRAINT solde_pkey PRIMARY KEY (lot_id, magasin_id);

ALTER TABLE ONLY public.tentative
    ADD CONSTRAINT tentative_pkey PRIMARY KEY (identifiant);

ALTER TABLE ONLY public.titrage
    ADD CONSTRAINT titrage_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.type_fil
    ADD CONSTRAINT type_fil_pkey PRIMARY KEY (code);

ALTER TABLE ONLY public.utilisateur
    ADD CONSTRAINT utilisateur_identifiant_key UNIQUE (identifiant);

ALTER TABLE ONLY public.utilisateur
    ADD CONSTRAINT utilisateur_pkey PRIMARY KEY (id);

CREATE UNIQUE INDEX dossier_facture_id_key ON public.dossier USING btree (facture_id);

CREATE INDEX ix_journal_quand ON public.journal USING btree (quand);

CREATE INDEX ix_lot_article_id ON public.lot USING btree (article_id);

CREATE INDEX ix_mouvement_article_date ON public.mouvement USING btree (article_id, date_effet);

CREATE INDEX ix_mouvement_date_effet ON public.mouvement USING btree (date_effet);

CREATE INDEX ix_mouvement_document_id ON public.mouvement USING btree (document_id);

CREATE INDEX ix_mouvement_lot_id ON public.mouvement USING btree (lot_id);

CREATE INDEX ix_parametre_historique_cle ON public.parametre_historique USING btree (cle);

CREATE INDEX ix_piece_jointe_objet_id ON public.piece_jointe USING btree (objet_id);

CREATE INDEX ix_recette_version_qualite_id ON public.recette_version USING btree (qualite_id);

CREATE UNIQUE INDEX uq_bon_fabrication_bon_qualite ON public.bon_fabrication USING btree (bon_id, qualite_id);

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_code_douanier_fkey FOREIGN KEY (code_douanier) REFERENCES public.code_douanier(code) ON UPDATE CASCADE;

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_composition_fkey FOREIGN KEY (composition) REFERENCES public.composition(code) ON UPDATE CASCADE;

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_couleur_fkey FOREIGN KEY (couleur) REFERENCES public.couleur(code) ON UPDATE CASCADE;

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_devise_fkey FOREIGN KEY (devise) REFERENCES public.devise(code);

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_role_fkey FOREIGN KEY (role) REFERENCES public.role_nomenclature(code);

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_titrage_fkey FOREIGN KEY (titrage) REFERENCES public.titrage(code) ON UPDATE CASCADE;

ALTER TABLE ONLY public.article
    ADD CONSTRAINT article_type_fil_fkey FOREIGN KEY (type_fil) REFERENCES public.type_fil(code) ON UPDATE CASCADE;

ALTER TABLE ONLY public.bon_fabrication
    ADD CONSTRAINT bon_fabrication_bon_id_fkey FOREIGN KEY (bon_id) REFERENCES public.bon_sortie(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.bon_fabrication
    ADD CONSTRAINT bon_fabrication_qualite_id_fkey FOREIGN KEY (qualite_id) REFERENCES public.qualite(id);

ALTER TABLE ONLY public.bon_ligne
    ADD CONSTRAINT bon_ligne_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.bon_ligne
    ADD CONSTRAINT bon_ligne_bon_id_fkey FOREIGN KEY (bon_id) REFERENCES public.bon_sortie(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.bon_ligne
    ADD CONSTRAINT bon_ligne_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.bon_sortie
    ADD CONSTRAINT bon_sortie_magasin_id_fkey FOREIGN KEY (magasin_id) REFERENCES public.magasin(id);

ALTER TABLE ONLY public.bon_sortie
    ADD CONSTRAINT bon_sortie_metier_id_fkey FOREIGN KEY (metier_id) REFERENCES public.metier(id);

ALTER TABLE ONLY public.commande
    ADD CONSTRAINT commande_devise_fkey FOREIGN KEY (devise) REFERENCES public.devise(code);

ALTER TABLE ONLY public.commande
    ADD CONSTRAINT commande_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.commande_ligne
    ADD CONSTRAINT commande_ligne_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.commande_ligne
    ADD CONSTRAINT commande_ligne_commande_id_fkey FOREIGN KEY (commande_id) REFERENCES public.commande(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dossier_charge
    ADD CONSTRAINT dossier_charge_dossier_id_fkey FOREIGN KEY (dossier_id) REFERENCES public.dossier(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dossier_charge
    ADD CONSTRAINT dossier_charge_ligne_id_fkey FOREIGN KEY (ligne_id) REFERENCES public.dossier_ligne(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dossier_charge_part
    ADD CONSTRAINT dossier_charge_part_charge_id_fkey FOREIGN KEY (charge_id) REFERENCES public.dossier_charge(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dossier_charge_part
    ADD CONSTRAINT dossier_charge_part_ligne_id_fkey FOREIGN KEY (ligne_id) REFERENCES public.dossier_ligne(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dossier_charge
    ADD CONSTRAINT dossier_charge_poste_fkey FOREIGN KEY (poste) REFERENCES public.poste_frais(code);

ALTER TABLE ONLY public.dossier
    ADD CONSTRAINT dossier_facture_id_fkey FOREIGN KEY (facture_id) REFERENCES public.facture(id);

ALTER TABLE ONLY public.dossier_ligne
    ADD CONSTRAINT dossier_ligne_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.dossier_ligne
    ADD CONSTRAINT dossier_ligne_dossier_id_fkey FOREIGN KEY (dossier_id) REFERENCES public.dossier(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.dossier_ligne
    ADD CONSTRAINT dossier_ligne_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.dossier_ligne
    ADD CONSTRAINT dossier_ligne_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.dossier_ligne
    ADD CONSTRAINT dossier_ligne_reception_ligne_id_fkey FOREIGN KEY (reception_ligne_id) REFERENCES public.reception_ligne(id);

ALTER TABLE ONLY public.facture
    ADD CONSTRAINT facture_devise_fkey FOREIGN KEY (devise) REFERENCES public.devise(code);

ALTER TABLE ONLY public.facture
    ADD CONSTRAINT facture_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.fil_monte
    ADD CONSTRAINT fil_monte_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.fil_monte
    ADD CONSTRAINT fil_monte_metier_id_fkey FOREIGN KEY (metier_id) REFERENCES public.metier(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.fournisseur
    ADD CONSTRAINT fournisseur_devise_fkey FOREIGN KEY (devise) REFERENCES public.devise(code);

ALTER TABLE ONLY public.inventaire_ligne
    ADD CONSTRAINT inventaire_ligne_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.inventaire_ligne
    ADD CONSTRAINT inventaire_ligne_inventaire_id_fkey FOREIGN KEY (inventaire_id) REFERENCES public.inventaire(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.inventaire_ligne
    ADD CONSTRAINT inventaire_ligne_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.inventaire_ligne
    ADD CONSTRAINT inventaire_ligne_magasin_id_fkey FOREIGN KEY (magasin_id) REFERENCES public.magasin(id);

ALTER TABLE ONLY public.inventaire
    ADD CONSTRAINT inventaire_magasin_id_fkey FOREIGN KEY (magasin_id) REFERENCES public.magasin(id);

ALTER TABLE ONLY public.lot
    ADD CONSTRAINT lot_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.lot
    ADD CONSTRAINT lot_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.mouvement
    ADD CONSTRAINT mouvement_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.mouvement
    ADD CONSTRAINT mouvement_contrepasse_id_fkey FOREIGN KEY (contrepasse_id) REFERENCES public.mouvement(id);

ALTER TABLE ONLY public.mouvement
    ADD CONSTRAINT mouvement_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.mouvement
    ADD CONSTRAINT mouvement_magasin_id_fkey FOREIGN KEY (magasin_id) REFERENCES public.magasin(id);

ALTER TABLE ONLY public.mouvement
    ADD CONSTRAINT mouvement_ordre_id_fkey FOREIGN KEY (ordre_id) REFERENCES public.bon_sortie(id);

ALTER TABLE ONLY public.operation
    ADD CONSTRAINT operation_bon_id_fkey FOREIGN KEY (bon_id) REFERENCES public.bon_sortie(id);

ALTER TABLE ONLY public.operation
    ADD CONSTRAINT operation_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.operation_ligne
    ADD CONSTRAINT operation_ligne_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.operation_ligne
    ADD CONSTRAINT operation_ligne_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.operation_ligne
    ADD CONSTRAINT operation_ligne_magasin_destination_id_fkey FOREIGN KEY (magasin_destination_id) REFERENCES public.magasin(id);

ALTER TABLE ONLY public.operation_ligne
    ADD CONSTRAINT operation_ligne_magasin_id_fkey FOREIGN KEY (magasin_id) REFERENCES public.magasin(id);

ALTER TABLE ONLY public.operation_ligne
    ADD CONSTRAINT operation_ligne_operation_id_fkey FOREIGN KEY (operation_id) REFERENCES public.operation(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.qualite_poids
    ADD CONSTRAINT qualite_poids_qualite_id_fkey FOREIGN KEY (qualite_id) REFERENCES public.qualite(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.qualite_poids
    ADD CONSTRAINT qualite_poids_role_fkey FOREIGN KEY (role) REFERENCES public.role_nomenclature(code);

ALTER TABLE ONLY public.qualite_saison
    ADD CONSTRAINT qualite_saison_qualite_id_fkey FOREIGN KEY (qualite_id) REFERENCES public.qualite(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.reception
    ADD CONSTRAINT reception_facture_id_fkey FOREIGN KEY (facture_id) REFERENCES public.facture(id);

ALTER TABLE ONLY public.reception
    ADD CONSTRAINT reception_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.reception_ligne
    ADD CONSTRAINT reception_ligne_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.reception_ligne
    ADD CONSTRAINT reception_ligne_commande_ligne_id_fkey FOREIGN KEY (commande_ligne_id) REFERENCES public.commande_ligne(id);

ALTER TABLE ONLY public.reception_ligne
    ADD CONSTRAINT reception_ligne_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.reception_ligne
    ADD CONSTRAINT reception_ligne_magasin_id_fkey FOREIGN KEY (magasin_id) REFERENCES public.magasin(id);

ALTER TABLE ONLY public.reception_ligne
    ADD CONSTRAINT reception_ligne_reception_id_fkey FOREIGN KEY (reception_id) REFERENCES public.reception(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.recette
    ADD CONSTRAINT recette_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.recette
    ADD CONSTRAINT recette_qualite_id_fkey FOREIGN KEY (qualite_id) REFERENCES public.qualite(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.recette_version
    ADD CONSTRAINT recette_version_qualite_id_fkey FOREIGN KEY (qualite_id) REFERENCES public.qualite(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.reclamation
    ADD CONSTRAINT reclamation_fournisseur_id_fkey FOREIGN KEY (fournisseur_id) REFERENCES public.fournisseur(id);

ALTER TABLE ONLY public.reclamation
    ADD CONSTRAINT reclamation_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.reclamation
    ADD CONSTRAINT reclamation_reception_id_fkey FOREIGN KEY (reception_id) REFERENCES public.reception(id);

ALTER TABLE ONLY public.reclamation
    ADD CONSTRAINT reclamation_reception_ligne_id_fkey FOREIGN KEY (reception_ligne_id) REFERENCES public.reception_ligne(id);

ALTER TABLE ONLY public.session_ouverte
    ADD CONSTRAINT session_ouverte_utilisateur_id_fkey FOREIGN KEY (utilisateur_id) REFERENCES public.utilisateur(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.signalement
    ADD CONSTRAINT signalement_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.article(id);

ALTER TABLE ONLY public.signalement
    ADD CONSTRAINT signalement_par_id_fkey FOREIGN KEY (par_id) REFERENCES public.utilisateur(id) ON DELETE SET NULL;

ALTER TABLE ONLY public.solde
    ADD CONSTRAINT solde_lot_id_fkey FOREIGN KEY (lot_id) REFERENCES public.lot(id);

ALTER TABLE ONLY public.solde
    ADD CONSTRAINT solde_magasin_id_fkey FOREIGN KEY (magasin_id) REFERENCES public.magasin(id);
