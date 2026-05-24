# pip install snscrape pandas

import re
from urllib.parse import urlparse
import pandas as pd
#import snscrape.modules.twitter as sntwitter

import importlib

sntwitter = importlib.import_module("snscrape.modules.twitter")


def extraer_info_url_tweet(url: str):
    """
    Extrae el username y el tweet_id desde una URL tipo:
    https://twitter.com/usuario/status/123...
    https://x.com/usuario/status/123...
    """
    patron = r"https?://(?:www\.)?(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)"
    m = re.search(patron, url)
    if not m:
        raise ValueError("La URL no tiene un formato válido de tweet/status.")
    username = m.group(1)
    tweet_id = m.group(2)
    return username, tweet_id


def obtener_atributo(obj, nombre, default=None):
    """Devuelve un atributo si existe; caso contrario, default."""
    return getattr(obj, nombre, default)


def tweet_a_dict(tweet):
    """
    Convierte un objeto tweet de snscrape en diccionario seguro.
    Algunos campos pueden no existir según la versión.
    """
    user = obtener_atributo(tweet, "user")
    return {
        "tweet_id": obtener_atributo(tweet, "id"),
        "conversation_id": obtener_atributo(tweet, "conversationId"),
        "reply_to_tweet_id": (
            tweet.inReplyToTweetId
            if hasattr(tweet, "inReplyToTweetId")
            else None
        ),
        "reply_to_user": (
            tweet.inReplyToUser.username
            if hasattr(tweet, "inReplyToUser") and tweet.inReplyToUser
            else None
        ),
        "nombre_usuario": obtener_atributo(user, "displayname"),
        "usuario": obtener_atributo(user, "username"),
        "fecha": obtener_atributo(tweet, "date"),
        "comentarios": obtener_atributo(tweet, "replyCount"),
        "reposts": obtener_atributo(tweet, "retweetCount"),
        "likes": obtener_atributo(tweet, "likeCount"),
        "reproducciones": obtener_atributo(tweet, "viewCount"),
        "texto": obtener_atributo(tweet, "rawContent"),
        "url": obtener_atributo(tweet, "url"),
    }


def extraer_hilo_desde_url(url_tweet: str, incluir_toda_la_conversacion=True):
    """
    A partir de una URL de tweet:
    - obtiene el tweet original
    - identifica el conversationId
    - descarga los tweets relacionados con esa conversación
    """
    _, tweet_id = extraer_info_url_tweet(url_tweet)

    # 1) Buscar el tweet exacto
    consulta_origen = f"url:{url_tweet}"
    tweet_origen = None

    for t in sntwitter.TwitterSearchScraper(consulta_origen).get_items():
        if str(getattr(t, "id", "")) == tweet_id:
            tweet_origen = t
            break

    if tweet_origen is None:
        raise RuntimeError("No se pudo recuperar el tweet original desde la URL.")

    conversation_id = getattr(tweet_origen, "conversationId", None)
    if conversation_id is None:
        raise RuntimeError("No se pudo determinar el conversationId del tweet.")

    # 2) Buscar toda la conversación
    # conversation_id:<id> devuelve publicaciones asociadas a esa conversación
    consulta_conv = f"conversation_id:{conversation_id}"
    registros = []

    for t in sntwitter.TwitterSearchScraper(consulta_conv).get_items():
        registros.append(tweet_a_dict(t))

    if not registros:
        raise RuntimeError("No se encontraron publicaciones para la conversación.")

    df = pd.DataFrame(registros)

    # Normalizar fecha
    if "fecha" in df.columns:
        df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # Orden sugerido
    columnas = [
        "tweet_id",
        "conversation_id",
        "reply_to_tweet_id",
        "reply_to_user",
        "nombre_usuario",
        "usuario",
        "fecha",
        "comentarios",
        "reposts",
        "likes",
        "reproducciones",
        "texto",
        "url",
    ]
    df = df[[c for c in columnas if c in df.columns]]

    df = df.sort_values(by=["fecha", "tweet_id"], ascending=[True, True]).reset_index(drop=True)

    return tweet_origen, df


def construir_tabla_publicaciones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Devuelve la tabla principal de publicaciones lista para copiar.
    """
    columnas = [
        "nombre_usuario",
        "usuario",
        "fecha",
        "comentarios",
        "reposts",
        "likes",
        "reproducciones",
        "texto",
    ]
    salida = df[columnas].copy()

    # Formatear fecha para visualización
    if "fecha" in salida.columns:
        salida["fecha"] = salida["fecha"].dt.strftime("%Y-%m-%d %H:%M:%S")

    return salida


def construir_tabla_interacciones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construye una tabla de interacción entre publicaciones.
    Cada fila representa una relación de respuesta.
    """
    base = df.copy()

    # Mapa tweet_id -> usuario/texto
    mapa_usuario = dict(zip(base["tweet_id"], base["usuario"]))
    mapa_nombre = dict(zip(base["tweet_id"], base["nombre_usuario"]))
    mapa_texto = dict(zip(base["tweet_id"], base["texto"]))

    interacciones = []

    for _, row in base.iterrows():
        tweet_id = row["tweet_id"]
        reply_to = row["reply_to_tweet_id"]

        if pd.notna(reply_to):
            interacciones.append({
                "tweet_origen_id": reply_to,
                "tweet_respuesta_id": tweet_id,
                "usuario_origen": mapa_usuario.get(reply_to),
                "nombre_origen": mapa_nombre.get(reply_to),
                "usuario_responde": row["usuario"],
                "nombre_responde": row["nombre_usuario"],
                "tipo_interaccion": "respuesta",
                "texto_origen": mapa_texto.get(reply_to),
                "texto_respuesta": row["texto"],
            })

    df_inter = pd.DataFrame(interacciones)

    if df_inter.empty:
        # Devuelve estructura vacía consistente
        df_inter = pd.DataFrame(columns=[
            "tweet_origen_id",
            "tweet_respuesta_id",
            "usuario_origen",
            "nombre_origen",
            "usuario_responde",
            "nombre_responde",
            "tipo_interaccion",
            "texto_origen",
            "texto_respuesta",
        ])

    return df_inter


def mostrar_tablas_copiables(df_publicaciones: pd.DataFrame, df_interacciones: pd.DataFrame):
    """
    Muestra tablas en formato Markdown para copiar fácilmente.
    """
    print("\n=== TABLA DE PUBLICACIONES ===\n")
    print(df_publicaciones.to_markdown(index=False))

    print("\n=== TABLA DE INTERACCIONES ===\n")
    if len(df_interacciones) > 0:
        print(df_interacciones.to_markdown(index=False))
    else:
        print("No se detectaron relaciones de respuesta dentro de las publicaciones recuperadas.")


def guardar_resultados_excel(df_publicaciones: pd.DataFrame, df_interacciones: pd.DataFrame, archivo="hilo_twitter.xlsx"):
    with pd.ExcelWriter(archivo, engine="openpyxl") as writer:
        df_publicaciones.to_excel(writer, sheet_name="publicaciones", index=False)
        df_interacciones.to_excel(writer, sheet_name="interacciones", index=False)
    print(f"\nArchivo guardado: {archivo}")


if __name__ == "__main__":
    #url = input("Ingresa la URL del tweet/hilo: ").strip()
    url = "https://x.com/DiegoArcos14/status/2037145702506119642"

    try:
        tweet_origen, df_hilo = extraer_hilo_desde_url(url)

        df_publicaciones = construir_tabla_publicaciones(df_hilo)
        df_interacciones = construir_tabla_interacciones(df_hilo)

        mostrar_tablas_copiables(df_publicaciones, df_interacciones)

        # Opcional: guardar en Excel
        guardar_resultados_excel(df_publicaciones, df_interacciones, "hilo_twitter.xlsx")

    except Exception as e:
        print(f"Error: {e}")