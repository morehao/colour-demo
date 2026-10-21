"""路由：只做「取参数 → 调 core → 返回」，不含任何色彩算法（方案 7.1）。"""

from __future__ import annotations

import numpy as np
import colour
from fastapi import APIRouter

from .. import SUPPORTED_COLOUR_VERSION
from ..config import MAX_COLOURS
from ..core import chroma, convert, delta_e, gradient, photometry, spaces, spectral
from .schemas import (
    ChromaRequest,
    ConvertRequest,
    DeltaERequest,
    GradientRequest,
    PhotometryRequest,
    SpectralRequest,
)

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "colour_version": colour.__version__,
        "expected_colour_version": SUPPORTED_COLOUR_VERSION,
        "numpy_version": np.__version__,
    }


@router.get("/meta")
def meta() -> dict:
    """元信息：版本、口径、可选方法枚举（前端下拉框直接读这里）。"""

    return {
        "app": "colour-demo",
        "colour_version": colour.__version__,
        "numpy_version": np.__version__,
        "limits": {"max_colours": MAX_COLOURS},
        "methods": {
            "delta_e": delta_e.METHODS,
            "lightness": photometry.LIGHTNESS_METHODS,
            "whiteness": photometry.WHITENESS_METHODS,
            "yellowness": photometry.YELLOWNESS_METHODS,
        },
        "counts": {
            "rgb_colourspaces": len(colour.RGB_COLOURSPACES),
            "illuminants": len(colour.SDS_ILLUMINANTS),
            "cmfs": len(colour.MSDS_CMFS),
            "conversion_graph_nodes": len(getattr(colour.graph.conversion.CONVERSION_GRAPH, "nodes", []) or []),
        },
        "endpoints": [
            "GET /api/v1/health",
            "GET /api/v1/meta",
            "GET /api/v1/spaces",
            "POST /api/v1/convert",
            "POST /api/v1/chroma",
            "POST /api/v1/spectral",
            "POST /api/v1/photometry",
            "POST /api/v1/delta-e",
            "POST /api/v1/gradient",
        ],
    }


@router.get("/spaces")
def list_spaces(limit: int | None = None) -> dict:
    return spaces.spaces_index(limit=limit)


@router.post("/convert")
def post_convert(payload: ConvertRequest) -> dict:
    return convert.convert_colours(
        payload.colors,
        target_spaces=payload.target_spaces,
        source=payload.source,
        target=payload.target,
    )


@router.post("/chroma")
def post_chroma(payload: ChromaRequest) -> dict:
    return chroma.chroma_data(payload.colors, illuminant=payload.illuminant)


@router.post("/spectral")
def post_spectral(payload: SpectralRequest) -> dict:
    return spectral.spectral_data(
        illuminant=payload.illuminant,
        start=payload.start,
        end=payload.end,
        interval=payload.interval,
        blackbody_temperature=payload.blackbody_temperature,
    )


@router.post("/photometry")
def post_photometry(payload: PhotometryRequest) -> dict:
    return photometry.photometry_data(payload.colors, white=payload.white)


@router.post("/delta-e")
def post_delta_e(payload: DeltaERequest) -> dict:
    return delta_e.delta_e_matrix(payload.colors, method=payload.method)


@router.post("/gradient")
def post_gradient(payload: GradientRequest) -> dict:
    return gradient.gradient_data(
        payload.start_colour,
        payload.end_colour,
        space=payload.space,
        steps=payload.steps,
        method=payload.method,
    )
