import base64
from io import BytesIO
from dataclasses import dataclass

import numpy as np
from PIL import Image
import streamlit.components.v1 as components
import os

# -------------------------------------------------------
# Componente
# -------------------------------------------------------

_RELEASE = True  # ou False se estiver desenvolvendo

if not _RELEASE:
    _component_func = components.declare_component(
        "st_canvas",
        url="http://localhost:3001",
    )
else:
    parent_dir = os.path.dirname(os.path.abspath(__file__))
    build_dir = os.path.join(parent_dir, "frontend/build")
    _component_func = components.declare_component("st_canvas", path=build_dir)


@dataclass
class CanvasResult:
    image_data: np.array = None
    json_data: dict = None


# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def _data_url_to_image(data_url: str) -> Image.Image:
    """Converte data URL (data:image/png;base64,...) em PIL.Image."""
    _, _data_url = data_url.split(";base64,")
    return Image.open(BytesIO(base64.b64decode(_data_url)))


def _resize_img(img: Image.Image, new_height: int = 700, new_width: int = 700) -> Image.Image:
    h_ratio = new_height / img.height
    w_ratio = new_width / img.width
    img = img.resize((int(img.width * w_ratio), int(img.height * h_ratio)))
    return img

def _pil_to_rgba_array(img: Image.Image) -> list:
    # igual à 0.8, mas garantindo ints
    return np.array(img.convert("RGBA")).flatten().astype(int).tolist()

def _pil_to_data_url(img: Image.Image, format: str = "PNG") -> str:
    buf = BytesIO()
    img.save(buf, format=format)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/{format.lower()};base64,{b64}"

# -------------------------------------------------------
# st_canvas compatível
# -------------------------------------------------------

def st_canvas(
    fill_color: str = "#eee",
    stroke_width: int = 20,
    stroke_color: str = "black",
    background_color: str = "",
    background_image: Image.Image = None,
    update_streamlit: bool = True,
    height: int = 400,
    width: int = 600,
    drawing_mode: str = "freedraw",
    initial_drawing: dict = None,
    display_toolbar: bool = True,
    point_display_radius: int = 3,
    key=None,
) -> CanvasResult:

    # --- 1) tratar background_image ---
    background_image_array = None   # estilo 0.8
    background_image_url = None     # para frontends que esperam URL/data URL

    if background_image is not None:
        # se vier em bytes, garante que vira PIL
        if isinstance(background_image, bytes):
            background_image = Image.open(BytesIO(background_image))

        # redimensiona pro tamanho do canvas
        background_image = _resize_img(background_image, height, width)

        # A) array RGBA flatten (como na 0.8)
        background_image_array = _pil_to_rgba_array(background_image)

        # B) data URL (pra quem usa URL)
        background_image_url = _pil_to_data_url(background_image, format="PNG")

        # se tem imagem, cor de fundo vira transparente
        background_color = ""

    # --- 2) initial_drawing ---
    initial_drawing = {"version": "4.4.0"} if initial_drawing is None else initial_drawing
    initial_drawing["background"] = background_color

    # --- 3) chamada do componente ---
    component_value = _component_func(
        fillColor=fill_color,
        strokeWidth=stroke_width,
        strokeColor=stroke_color,
        backgroundColor=background_color,

        # cobre todas as possibilidades:
        backgroundImage=background_image_array,   # compat antigo 0.8
        backgroundImageURL=background_image_url,  # compat forks recentes
        img_bytes=background_image_array,         # alguns forks usam só isso

        realtimeUpdateStreamlit=update_streamlit and (drawing_mode != "polygon"),
        canvasHeight=height,
        canvasWidth=width,
        drawingMode=drawing_mode,
        initialDrawing=initial_drawing,
        displayToolbar=display_toolbar,
        displayRadius=point_display_radius,
        key=key,
        default=None,
    )

    if component_value is None:
        return CanvasResult()   # importante: instância, não a classe

    # --- 4) saída (manter estilo atual, se você já usa _data_url_to_image) ---
    data = component_value["data"]

    if isinstance(data, str) and data.startswith("data:image"):
        img = _data_url_to_image(data)
        img_np = np.asarray(img)
    else:
        # fallback estilo 0.8
        w = component_value.get("width", width)
        h = component_value.get("height", height)
        arr = np.array(data, dtype=np.uint8)
        img_np = np.reshape(arr, (h, w, 4))

    return CanvasResult(
        image_data=img_np,
        json_data=component_value.get("raw"),
    )
