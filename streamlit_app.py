import streamlit as st
import pandas as pd
import numpy as np

import plotly.express as px
import graphviz

import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components

from numpy.random import default_rng as rng

#pages
import internal.fromx as fx
import internal.references as ref

st.title("Urdesa ... se vende")

# Multipage app
# https://docs.streamlit.io/get-started/tutorials/create-a-multipage-app

def convertir_nodos_a_str(G):
    H = nx.Graph() if not G.is_directed() else nx.DiGraph()

    # copiar nodos convirtiendo el id a string
    for n, attrs in G.nodes(data=True):
        H.add_node(str(n), **attrs)

    # copiar aristas convirtiendo extremos a string
    for u, v, attrs in G.edges(data=True):
        H.add_edge(str(u), str(v), **attrs)

    return H

def return_pyvis_graph(df):

    # Crear grafo
    G = nx.Graph()

    # Agregar nodos y aristas
    for _, row in df.iterrows():
        origen = row["origen_usuario"]
        destino = row["destino_usuario"]
        G.add_edge(origen, destino)

    # (Opcional) Ver nodos y aristas
    # print("Nodos:", G.nodes())
    # print("Aristas:", G.edges())

    # # Create NetworkX graph
    # G = nx.Graph()
    # G.add_edge("User 1", "User 2")
    # G.add_edge("User 2", "User 3")

    G_pyvis = convertir_nodos_a_str(G)

    # # Generate PyVis graph
    net = Network(height="400px", width="100%", bgcolor="#FFFFFF", font_color="black")
    net.from_nx(G_pyvis)
    net.save_graph("graph.html")

    # Render in Streamlit
    HtmlFile = open("graph.html", 'r', encoding='utf-8')
    source_code = HtmlFile.read()
    components.html(source_code, height=400)


def datos_venta():

    df = pd.read_excel("../data/casas_urdesa_final_expanded.xlsx")
    
    total_rows = len(df)
    media_precio = df["precio"].mean()
    mediana_precio = df["precio"].median()

    media_area = df["m2_total"].mean()
    media_habitaciones = int(df["habitaciones"].mean())
    media_banos = int(df["banos"].mean())
    media_estacionamientos = int(df["estacionamientos"].mean())

    st.header("Plusvalia [31 de marzo de 2026]")
    st.subheader("Precio de venta")
    
    #st.html(f"[31 de marzo de 2026] En <a href='www.plusvalia.com' target='_blank'>Plusvalia</a> existen {total_rows} propiedades en venta en Urdesa.")

    col1, col2 = st.columns(2)

    with col1:
        
        body = f"En [Urdesa](https://es.wikipedia.org/wiki/Urdesa), donde alguna vez las historias se medían en recuerdos más que en cifras, hoy el mercado inmobiliario revela otra realidad por el precio promedio de las propiedades alrededor de los **\\${media_precio:,.0f}**, mientras que la mediana se ubica en **\\${mediana_precio:,.0f}**.\n"
        

        #body += ",  Entre extremos que van desde los $5.000 hasta los $2 millones, la dispersión refleja no solo diferencias económicas, sino también las transformaciones de un barrio que ha visto cambiar su esencia con el tiempo. Esa brecha, donde unos pocos valores elevados influyen en el promedio, sugiere una Urdesa que, sin dejar de ser entrañable, se redefine entre la nostalgia de lo que fue y las nuevas dinámicas de una ciudad en constante evolución."

        st.markdown( body , text_alignment="justify")

        st.badge("Predomino de viviendas de valor medio.", icon=":material/check:", color="green")
        st.badge("Creciente presencia de inmuebles de alto costo.", icon=":material/check:", color="green")

    with col2:

        fig = px.histogram(df, x="precio", 
                   marginal="rug", # adds a rug plot at bottom
                   title="Casas en venta en Urdesa",
                   subtitle="Distribución de precios",
                  )

        # Agregar línea de la media
        fig.add_vline(
            x=media_precio,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Media: ${media_precio:,.0f}",
            annotation_position="top right",
            row=1, col=1
        )

        # Agregar línea de la mediana
        fig.add_vline(
            x=mediana_precio,
            line_dash="dot",
            line_color="green",
            annotation_text=f"Mediana: ${mediana_precio:,.0f}",
            annotation_position="top left",
            row=2, col=1
        )
        
        fig.update_xaxes(title_text="Precio del inmueble (USD)",row=1, col=1)
        fig.update_yaxes(title_text="Número de propiedades",row=1, col=1)
        
        st.plotly_chart(fig)

    st.subheader("Distribución interna")

    body = f"Las casas amplias eran sinónimo de familias numerosas y tardes compartidas en patios generosos, hoy sus dimensiones cuentan otra historia. Con un **área promedio de {media_area:,.2f} m²**, más de **{media_habitaciones} habitaciones**, casi **{media_banos} baños** y al menos **{media_estacionamientos} estacionamientos**.\n"

    st.markdown( body , text_alignment="justify")
    
    col1, col2 = st.columns([3, 1])

    with col2: 
        st.badge("Espacios amplios.", icon=":material/check:", color="green")
        st.badge("Ex viviendas familiares.", icon=":material/check:", color="green")
        st.badge(label="Oficinas o negocios", icon=":material/check:", color="green")
        

    with col1:
        st.image("images/distribucion.png", caption="Imagen generada por ChatGPT a partir de las referencias")

    body = "Así, entre paredes que alguna vez guardaron risas y rutinas cotidianas, Urdesa refleja cómo el paso del tiempo convierte lo residencial en funcional, sin borrar del todo la memoria de lo que fue."

    st.markdown( body , text_alignment="justify")

page_names_to_funcs = {
    "En X": fx.unx,
    "Inmuebles en venta": datos_venta,
    "Referencias": ref.referencias,
}

demo_name = st.sidebar.selectbox("Empieza por aquí", page_names_to_funcs.keys())
page_names_to_funcs[demo_name]()

