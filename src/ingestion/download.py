"""
Ingestion des données qualité de l'eau via l'API Hub'Eau.
Documentation : https://hubeau.eaufrance.fr/page/api-qualite-eau-potable
"""

import requests
import logging
import json
import time
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

API_BASE = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"
OUTPUT_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"

DEPARTEMENTS = ["64"]
ANNEES = [2025, 2026]


def fetch_resultats(code_departement: str, annee: int) -> list[dict]:
    """Récupère les résultats d'analyses pour un département et une année."""
    url = f"{API_BASE}/resultats_dis"
    params = {
        "code_departement": code_departement,
        "date_min_prelevement": f"{annee}-01-01",
        "date_max_prelevement": f"{annee}-12-31",
        "size": 5000,
        "page": 1,
        "fields": (
            "code_departement,nom_departement,"
            "code_commune,nom_commune,"
            "code_reseau,nom_reseau,"
            "date_prelevement,code_parametre,libelle_parametre,"
            "resultat_alphanumerique,unite_mesure,"
            "limite_qualite_parametre,reference_qualite_parametre,"
            "conclusion_conformite_prelevement,"
            "coordonnee_x,coordonnee_y"
        ),
    }
    results = []
    while True:
        try:
            r = requests.get(url, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            batch = data.get("data", [])
            results.extend(batch)
            total = data.get("count", "?")
            logger.info(f"  dept {code_departement} {annee} : {len(results)} / {total}")
            if not data.get("next"):
                break
            params["page"] += 1
            time.sleep(0.2)  # on respecte l'API
        except requests.exceptions.Timeout:
            logger.warning(f"  Timeout page {params['page']}, retry dans 5s...")
            time.sleep(5)
            continue
        except requests.exceptions.RequestException as e:
            logger.error(f"  Erreur : {e}")
            break
    return results


def save_json(data: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"  ✅ {path.name} — {len(data)} enregistrements")


def ingest_departement(code_dept: str, annees: list[int]) -> None:
    dept_dir = OUTPUT_DIR / f"dept_{code_dept}"
    dept_dir.mkdir(parents=True, exist_ok=True)

    for annee in annees:
        output_path = dept_dir / f"resultats_{annee}.json"
        if output_path.exists():
            logger.info(f"  Déjà présent : {output_path.name}")
            continue
        logger.info(f"\n🔬 dept {code_dept} — {annee}")
        data = fetch_resultats(code_dept, annee)
        if data:
            save_json(data, output_path)


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for dept in DEPARTEMENTS:
        ingest_departement(dept, ANNEES)
    logger.info("\n🎉 Ingestion terminée")
