import streamlit as st
import folium

from streamlit_folium import st_folium

import internal.tweet as tw


def unx():

    coordUrdesa = [-2.1644604613264744, -79.90294668773116]

    st.header("Un recuerdo que unió a miles")

    col1, col2 = st.columns(2)

    with col1:
        tw.Tweet("https://x.com/DiegoArcos14/status/2037145702506119642").component()

    with col2:
        body =  "Hubo un tiempo en el que [Urdesa](https://es.wikipedia.org/wiki/Urdesa) no era solo un sector de la ciudad, sino un punto de encuentro donde la vida transcurría entre cines de barrio, caminatas al atardecer y conversaciones que parecían no tener prisa.\n\n"
        
        body += "[@DiegoArcos14](https://x.com/DiegoArcos14/status/2037145702506119642) revive la memoria colectiva de lugares que ya no existen, rutinas que marcaron generaciones y una forma de habitar la ciudad que hoy se siente lejana."

        st.markdown( body , text_alignment="justify")

        m = folium.Map(location=coordUrdesa, zoom_start=15)
        st_folium(m, height=320) 
    
    #st.subheader("La historia detrás de la nostalgia")

    # Cargar archivo
    #df = pd.read_csv("../data/interacciones_hilo.csv")

    #return_pyvis_graph(df)