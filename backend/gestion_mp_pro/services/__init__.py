"""Services métier : un module par domaine, transactions et règles, sans HTTP (ARCHITECTURE § 3.1).

Un service reçoit une `Session` SQLAlchemy et l'acteur, refuse par `Refus` (`api/erreurs.py`),
écrit le journal ; il n'importe jamais FastAPI et ne lit jamais la requête. Typage strict (mypy).
"""
