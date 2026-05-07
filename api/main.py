"""
API Qualité de l'eau — expose les tables Gold via Databricks SQL Warehouse.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from databricks import sql
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(
    title="API Qualité de l'eau",
    description="Données du contrôle sanitaire de l'eau distribuée en France",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

HOST = os.getenv("DATABRICKS_HOST", "").replace("https://", "").rstrip("/")
TOKEN = os.getenv("DATABRICKS_TOKEN")
HTTP_PATH = os.getenv("DATABRICKS_HTTP_PATH")
CATALOG = "workspace"
DB = "qualite_eau"


def query(sql_query: str, params: dict = None) -> list[dict]:
    with sql.connect(
        server_hostname=HOST,
        http_path=HTTP_PATH,
        access_token=TOKEN,
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(sql_query, params or {})
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]


@app.get("/")
def root():
    return {
        "message": "API Qualité de l'eau",
        "version": "1.0.0",
        "endpoints": [
            "/health",
            "/communes/{code}/conformite",
            "/departements/{code}/conformite",
            "/top/meilleures",
            "/top/pires",
            "/non-conformites/{code_dept}",
        ],
    }


@app.get("/health")
def health():
    try:
        query("SELECT 1 as ok")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(503, f"Warehouse indisponible : {e}")


@app.get("/communes/{code_commune}/conformite")
def get_conformite_commune(code_commune: str, annee: int = None):
    if not code_commune.isdigit() or len(code_commune) != 5:
        raise HTTPException(400, "Code INSEE invalide (5 chiffres)")

    q = f"""
        SELECT * FROM {CATALOG}.{DB}.gold_conformite_commune
        WHERE code_commune = '{code_commune}'
    """
    if annee:
        q += f" AND annee = {annee}"
    q += " ORDER BY annee DESC"

    rows = query(q)
    if not rows:
        raise HTTPException(404, f"Aucune donnée pour la commune {code_commune}")
    return rows


@app.get("/departements/{code_dept}/conformite")
def get_conformite_departement(code_dept: str):
    rows = query(
        f"""
        SELECT
            annee,
            COUNT(*) as nb_communes,
            ROUND(AVG(taux_conformite_pct), 2) as taux_moyen,
            SUM(nb_prelevements) as total_prelevements
        FROM {CATALOG}.{DB}.gold_conformite_commune
        WHERE _departement = '{code_dept}'
        GROUP BY annee
        ORDER BY annee DESC
    """
    )
    if not rows:
        raise HTTPException(404, f"Département {code_dept} non trouvé")
    return rows


@app.get("/top/meilleures")
def top_meilleures():
    return query(
        f"SELECT * FROM {CATALOG}.{DB}.gold_top10_meilleures ORDER BY taux_conformite_pct DESC"
    )


@app.get("/top/pires")
def top_pires():
    return query(
        f"SELECT * FROM {CATALOG}.{DB}.gold_top10_pires ORDER BY taux_conformite_pct ASC"
    )


@app.get("/non-conformites/{code_dept}")
def non_conformites(code_dept: str):
    rows = query(
        f"""
        SELECT * FROM {CATALOG}.{DB}.gold_non_conformites
        WHERE _departement = '{code_dept}'
        ORDER BY nb_non_conformites DESC
    """
    )
    if not rows:
        raise HTTPException(
            404, f"Aucune non-conformité pour le département {code_dept}"
        )
    return rows
