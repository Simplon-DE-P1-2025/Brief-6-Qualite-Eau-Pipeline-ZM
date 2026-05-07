"""
Dashboard Streamlit — Qualité de l'eau en France
Visualisation des données Gold depuis Databricks SQL Warehouse
"""

import streamlit as st
import pandas as pd
from databricks import sql
from dotenv import load_dotenv
import os
import plotly.express as px

load_dotenv()

st.set_page_config(
    page_title="Qualité de l'eau en France",
    page_icon="💧",
    layout="wide"
)

# ─── Connexion Databricks ───────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    return sql.connect(
        server_hostname=os.getenv("DATABRICKS_HOST", "").replace("https://", "").rstrip("/"),
        http_path=os.getenv("DATABRICKS_HTTP_PATH"),
        access_token=os.getenv("DATABRICKS_TOKEN"),
    )


@st.cache_data(ttl=3600)
def query(sql_query: str) -> pd.DataFrame:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql_query)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)


CATALOG = "workspace"
DB = "qualite_eau"

# ─── Chargement des données ─────────────────────────────────────────────────

df_conformite = query(f"SELECT * FROM {CATALOG}.{DB}.gold_conformite_commune")
df_non_conformites = query(f"SELECT * FROM {CATALOG}.{DB}.gold_non_conformites")
df_evolution = query(f"SELECT * FROM {CATALOG}.{DB}.gold_evolution_parametres")
df_top_meilleures = query(f"SELECT * FROM {CATALOG}.{DB}.gold_top10_meilleures")
df_top_pires = query(f"SELECT * FROM {CATALOG}.{DB}.gold_top10_pires")

# Forcer les types string pour éviter les axes numériques
df_conformite["_departement"] = df_conformite["_departement"].astype(str)
df_non_conformites["_departement"] = df_non_conformites["_departement"].astype(str)
df_evolution["_departement"] = df_evolution["_departement"].astype(str)

# ─── Header ────────────────────────────────────────────────────────────────

st.title("💧 Qualité de l'eau en France")
st.caption("Données du contrôle sanitaire — Départements 31, 33, 40, 64, 65 — 2023 à 2025")
st.divider()

# ─── KPIs ──────────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Communes analysées", f"{df_conformite['code_commune'].nunique():,}")
with col2:
    taux_moyen = df_conformite["taux_conformite_pct"].mean()
    st.metric("Taux de conformité moyen", f"{taux_moyen:.1f}%")
with col3:
    st.metric("Total prélèvements", f"{df_conformite['nb_prelevements'].sum():,}")
with col4:
    st.metric("Non-conformités", f"{df_non_conformites['nb_non_conformites'].sum():,}")

st.divider()

# ─── Section 1 : Conformité par département ────────────────────────────────

st.subheader("📊 Taux de conformité par département et par année")

df_dept = (
    df_conformite
    .groupby(["_departement", "annee"])
    .agg(taux_moyen=("taux_conformite_pct", "mean"))
    .reset_index()
)
df_dept["annee"] = df_dept["annee"].astype(str)
df_dept["_departement"] = df_dept["_departement"].astype(str)
df_dept = df_dept.sort_values("_departement")

fig1 = px.bar(
    df_dept,
    x="_departement",
    y="taux_moyen",
    color="annee",
    barmode="group",
    text_auto=".1f",
    labels={
        "_departement": "Département",
        "taux_moyen": "Taux de conformité (%)",
        "annee": "Année"
    },
    color_discrete_sequence=px.colors.qualitative.Set2
)
fig1.update_layout(
    yaxis_range=[70, 100],
    xaxis_type="category",
    xaxis_title="Département",
)
st.plotly_chart(fig1, use_container_width=True)

st.divider()

# ─── Section 2 : Evolution temporelle ─────────────────────────────────────

st.subheader("📈 Evolution mensuelle des paramètres clés")

if df_evolution.empty:
    st.warning("Aucune donnée disponible pour l'évolution des paramètres.")
else:
    col_filtre1, col_filtre2 = st.columns(2)
    with col_filtre1:
        categories = sorted(df_evolution["categorie_parametre"].unique().tolist())
        categorie = st.selectbox("Catégorie", categories)

    with col_filtre2:
        params_filtres = sorted(df_evolution[
            df_evolution["categorie_parametre"] == categorie
        ]["libelle_parametre"].unique().tolist())
        parametre = st.selectbox("Paramètre", params_filtres)

    df_param = df_evolution[
        df_evolution["libelle_parametre"] == parametre
    ].copy()
    df_param["periode"] = (
        df_param["annee"].astype(str) + "-" +
        df_param["mois"].astype(str).str.zfill(2)
    )
    df_param = df_param.sort_values("periode")

    fig2 = px.line(
        df_param,
        x="periode",
        y="valeur_moyenne",
        color="_departement",
        markers=True,
        labels={
            "periode": "Période",
            "valeur_moyenne": "Valeur moyenne",
            "_departement": "Département"
        }
    )
    fig2.update_layout(xaxis_type="category")
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ─── Section 3 : Top 10 ────────────────────────────────────────────────────

st.subheader("🏆 Top 10 communes")

col_top1, col_top2 = st.columns(2)

with col_top1:
    st.markdown("**✅ Meilleures communes**")
    fig3 = px.bar(
        df_top_meilleures.sort_values("taux_conformite_pct"),
        x="taux_conformite_pct",
        y="nom_commune",
        orientation="h",
        color="taux_conformite_pct",
        color_continuous_scale="Greens",
        text_auto=".1f",
        labels={
            "taux_conformite_pct": "Taux (%)",
            "nom_commune": "Commune"
        }
    )
    fig3.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total ascending"}
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_top2:
    st.markdown("**❌ Communes les moins conformes**")
    fig4 = px.bar(
        df_top_pires.sort_values("taux_conformite_pct", ascending=False),
        x="taux_conformite_pct",
        y="nom_commune",
        orientation="h",
        color="taux_conformite_pct",
        color_continuous_scale="Reds_r",
        text_auto=".1f",
        labels={
            "taux_conformite_pct": "Taux (%)",
            "nom_commune": "Commune"
        }
    )
    fig4.update_layout(
        showlegend=False,
        coloraxis_showscale=False,
        yaxis={"categoryorder": "total descending"},
        xaxis_range=[0, 100]  # ← force l'axe de 0 à 100
    )
    st.plotly_chart(fig4, use_container_width=True)

st.divider()

# ─── Section 4 : Non-conformités ───────────────────────────────────────────

st.subheader("⚠️ Analyse des non-conformités")

col_nc1, col_nc2 = st.columns(2)

with col_nc1:
    st.markdown("**Par catégorie**")
    df_cat = (
        df_non_conformites
        .groupby("categorie_parametre")
        .agg(total=("nb_non_conformites", "sum"))
        .reset_index()
    )
    fig5 = px.pie(
        df_cat,
        values="total",
        names="categorie_parametre",
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig5.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig5, use_container_width=True)

with col_nc2:
    st.markdown("**Par département**")
    df_dept_nc = (
        df_non_conformites
        .groupby("_departement")
        .agg(total=("nb_non_conformites", "sum"))
        .reset_index()
        .sort_values("total", ascending=True)
    )
    df_dept_nc["_departement"] = df_dept_nc["_departement"].astype(str)
    fig6 = px.bar(
        df_dept_nc,
        x="total",
        y="_departement",
        orientation="h",
        color="total",
        color_continuous_scale="Oranges",
        text_auto=True,
        labels={
            "total": "Nombre de non-conformités",
            "_departement": "Département"
        }
    )
    fig6.update_layout(
        coloraxis_showscale=False,
        yaxis_type="category"
    )
    st.plotly_chart(fig6, use_container_width=True)

st.divider()
st.caption("Source : Hub'Eau — API Qualité de l'eau potable | Pipeline : Databricks Free Edition")