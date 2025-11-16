import base64
from io import BytesIO
import numpy as np
from dataclasses import dataclass
from PIL import Image
import streamlit.components.v1 as components
import os

# ---------------------------------------------------------------------
# Configuração do componente
# ---------------------------------------------------------------------

_RELEASE = True  # ou False se estiver desenvolvendo o frontend

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


def _data_url_to_image(data_url: str) -> Image.Image:
    """Converte data URL (data:image/png;base64,...) em PIL.Image"""
    _, _data_url = data_url.split(";base64,")
    return Image.open(BytesIO(base64.b64decode(_data_url)))


def _resize_img(img: Image.Image, new_height: int = 700, new_width: int = 700) -> Image.Image:
    """Redimensiona preservando proporção a partir de altura e largura alvo."""
    h_ratio = new_height / img.height
    w_ratio = new_width / img.width
    img = img.resize((int(img.width * w_ratio), int(img.height * h_ratio)))
    return img


def _pil_to_data_url(img: Image.Image, format: str = "PNG") -> str:
    """Converte PIL.Image em data URL (string) usando bytes/base64."""
    buf = BytesIO()
    img.save(buf, format=format)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/{format.lower()};base64,{b64}"


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
    """
    Cria o canvas e retorna:
      - image_data: numpy array (h, w, 4)
      - json_data: desenho em formato JSON (para reinjetar em initial_drawing)
    """

    # -----------------------------------------------------------------
    # 1) Trata background_image -> data URL via bytes
    # -----------------------------------------------------------------
    background_image_url = None

    if background_image is not None:
        # garante que é um PIL.Image
        if isinstance(background_image, bytes):
            background_image = Image.open(BytesIO(background_image))

        # redimensiona para o tamanho do canvas (mantendo sua função)
        background_image = _resize_img(background_image, height, width)

        # converte para data URL usando bytes/base64
        background_image_url = _pil_to_data_url(background_image, format="PNG")

        # se tem imagem de fundo, background_color fica transparente
        background_color = ""

    # -----------------------------------------------------------------
    # 2) initial_drawing default + background
    # -----------------------------------------------------------------
    initial_drawing = {"version": "4.4.0"} if initial_drawing is None else initial_drawing
    initial_drawing["background"] = background_color

    # -----------------------------------------------------------------
    # 3) Chamada ao componente React
    # -----------------------------------------------------------------
    component_value = _component_func(
        fillColor=fill_color,
        strokeWidth=stroke_width,
        strokeColor=stroke_color,
        backgroundColor=background_color,
        # IMPORTANTE: usar backgroundImageURL, não backgroundImage
        backgroundImageURL=background_image_url,
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

    # Primeira renderização: nada ainda
    if component_value is None:
        return CanvasResult()

    # -----------------------------------------------------------------
    # 4) Converte o retorno (data URL -> numpy array)
    # -----------------------------------------------------------------
    img = _data_url_to_image(component_value["data"])
    img_np = np.asarray(img)

    return CanvasResult(
        image_data=img_np,
        json_data=component_value["raw"],
    )
