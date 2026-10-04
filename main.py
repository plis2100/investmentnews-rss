import requests
from bs4 import BeautifulSoup
from email.utils import format_datetime
from datetime import datetime, timezone
from xml.etree import ElementTree as ET
from xml.dom import minidom

# ============================================================
# CONFIGURACIÓN
# ============================================================

CHANNEL = "InvestmentNewsEsp"

SOURCE_URL = f"https://t.me/s/{CHANNEL}"

FEED_FILE = "feed.xml"

FEED_TITLE = "Investment News ESP"

FEED_DESCRIPTION = (
    "Noticias de inversión, economía y mercados publicadas "
    "en el canal InvestmentNewsEsp de Telegram."
)


# ============================================================
# DESCARGAR TELEGRAM
# ============================================================

def download_channel():

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/140.0 Safari/537.36"
        )
    }

    response = requests.get(
        SOURCE_URL,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.text


# ============================================================
# EXTRAER PUBLICACIONES
# ============================================================

def extract_messages(html):

    soup = BeautifulSoup(html, "html.parser")

    messages = []

    posts = soup.select(
        "div.tgme_widget_message_wrap"
    )

    for post in posts:

        message = post.select_one(
            "div.tgme_widget_message"
        )

        if not message:
            continue

        data_post = message.get("data-post")

        if not data_post:
            continue

        try:
            channel_name, message_id = data_post.split("/")
        except ValueError:
            continue

        # ----------------------------------------------------
        # TEXTO
        # ----------------------------------------------------

        text_element = message.select_one(
            "div.tgme_widget_message_text"
        )

        if text_element:

            # Conservamos saltos de línea
            text = text_element.get_text(
                "\n",
                strip=True
            )

        else:
            text = ""

        if not text:
            continue

        # ----------------------------------------------------
        # FECHA
        # ----------------------------------------------------

        time_element = message.select_one(
            "time.datetime"
        )

        publication_date = None

        if time_element:

            date_string = time_element.get(
                "datetime"
            )

            if date_string:

                try:

                    publication_date = (
                        datetime.fromisoformat(
                            date_string.replace(
                                "Z",
                                "+00:00"
                            )
                        )
                    )

                except Exception:
                    publication_date = None

        # ----------------------------------------------------
        # URL ORIGINAL
        # ----------------------------------------------------

        message_url = (
            f"https://t.me/{channel_name}/"
            f"{message_id}"
        )

        # ----------------------------------------------------
        # TÍTULO
        # ----------------------------------------------------

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if lines:
            title = lines[0]
        else:
            title = "Nueva noticia"

        # Evitar títulos excesivamente largos
        if len(title) > 220:
            title = title[:217] + "..."

        messages.append(
            {
                "id": message_id,
                "title": title,
                "text": text,
                "url": message_url,
                "date": publication_date
            }
        )

    return messages


# ============================================================
# CREAR RSS
# ============================================================

def create_rss(messages):

    rss = ET.Element(
        "rss",
        {
            "version": "2.0"
        }
    )

    channel = ET.SubElement(
        rss,
        "channel"
    )

    ET.SubElement(
        channel,
        "title"
    ).text = FEED_TITLE

    ET.SubElement(
        channel,
        "link"
    ).text = SOURCE_URL

    ET.SubElement(
        channel,
        "description"
    ).text = FEED_DESCRIPTION

    ET.SubElement(
        channel,
        "language"
    ).text = "es"

    ET.SubElement(
        channel,
        "lastBuildDate"
    ).text = format_datetime(
        datetime.now(timezone.utc)
    )

    # ========================================================
    # ELEMENTOS RSS
    # ========================================================

    # Primero los más recientes
    messages = sorted(
        messages,
        key=lambda x: int(x["id"]),
        reverse=True
    )

    for message in messages:

        item = ET.SubElement(
            channel,
            "item"
        )

        # ----------------------------------------------------
        # TÍTULO
        # ----------------------------------------------------

        title = message["title"]

        # Añadir fecha visible al título
        if message["date"]:

            local_date = message["date"]

            date_text = local_date.strftime(
                "%d/%m/%Y %H:%M"
            )

            title = (
                f"{title} | "
                f"{date_text}"
            )

        ET.SubElement(
            item,
            "title"
        ).text = title

        # ----------------------------------------------------
        # LINK
        # ----------------------------------------------------

        ET.SubElement(
            item,
            "link"
        ).text = message["url"]

        # ----------------------------------------------------
        # GUID
        # ----------------------------------------------------

        guid = ET.SubElement(
            item,
            "guid",
            {
                "isPermaLink": "true"
            }
        )

        guid.text = message["url"]

        # ----------------------------------------------------
        # DESCRIPCIÓN
        # ----------------------------------------------------

        ET.SubElement(
            item,
            "description"
        ).text = message["text"]

        # ----------------------------------------------------
        # FECHA RSS
        # ----------------------------------------------------

        if message["date"]:

            date = message["date"]

            if date.tzinfo is None:
                date = date.replace(
                    tzinfo=timezone.utc
                )

            ET.SubElement(
                item,
                "pubDate"
            ).text = format_datetime(date)

    # ========================================================
    # XML BONITO
    # ========================================================

    raw_xml = ET.tostring(
        rss,
        encoding="utf-8"
    )

    pretty_xml = minidom.parseString(
        raw_xml
    ).toprettyxml(
        indent="  ",
        encoding="utf-8"
    )

    with open(
        FEED_FILE,
        "wb"
    ) as file:

        file.write(pretty_xml)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)

    print(
        "InvestmentNewsEsp → RSS"
    )

    print("=" * 60)

    print(
        f"Descargando {SOURCE_URL}"
    )

    html = download_channel()

    print(
        "Extrayendo publicaciones..."
    )

    messages = extract_messages(html)

    print(
        f"Publicaciones encontradas: "
        f"{len(messages)}"
    )

    if not messages:

        raise RuntimeError(
            "No se encontraron publicaciones "
            "en el canal."
        )

    create_rss(messages)

    print(
        f"RSS creado correctamente: "
        f"{FEED_FILE}"
    )


if __name__ == "__main__":
    main()
