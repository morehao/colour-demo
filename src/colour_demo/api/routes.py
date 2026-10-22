"""路由：只做「取参数 → 调 core → 返回」，不含任何色彩算法（方案 7.1）。"""

from __future__ import annotations

import colour
import numpy as np
from fastapi import APIRouter, Header, Response

from .. import SUPPORTED_COLOUR_VERSION
from ..config import MAX_COLOURS
from ..core import (
    adapt,
    appearance,
    catalog,
    chroma,
    chromaticity,
    convert,
    corresponding,
    correction,
    cvd,
    delta_e,
    gallery,
    geometry,
    gradient,
    interpolate,
    invoke,
    lut,
    notation,
    optics,
    phenomena,
    photometry,
    quality,
    recovery,
    spaces,
    spectral,
    temperature,
    transfer,
    volume,
)
from .schemas import (
    AdaptRequest,
    AppearanceRequest,
    CorrectionRequest,
    ChromaRequest,
    ConvertRequest,
    CorrespondingRequest,
    CvdRequest,
    DeltaERequest,
    GeometryRequest,
    GradientRequest,
    InterpolateRequest,
    InvokeRequest,
    LutRequest,
    NotationRequest,
    OpticsRequest,
    PhenomenaRequest,
    PhotometryRequest,
    PlotRequest,
    QualityRequest,
    RecoveryRequest,
    SpectralRequest,
    TemperatureRequest,
    TransferRequest,
    VolumeRequest,
)

router = APIRouter(prefix="/api/v1")


def _csv(value: str | None) -> tuple[str, ...]:
    """`?colors=#fff,#000` → `("#fff", "#000")`；坏值留给 core 统一报 422。"""

    if not value:
        return ()
    return tuple(part.strip() for part in value.split(",") if part.strip())


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
            "chromatic_adaptation": list(adapt.METHODS),
            "appearance_models": list(appearance.MODELS),
            "corresponding_models": list(corresponding.MODELS),
            "cvd_types": list(cvd.DEFICIENCIES),
            "temperature": {
                "xy_to_cct": list(temperature.XY_TO_CCT_METHODS),
                "uv_to_cct": list(temperature.UV_TO_CCT_METHODS),
                "cct_to_xy": list(temperature.CCT_TO_XY_METHODS),
                "cct_to_uv": list(temperature.CCT_TO_UV_METHODS),
            },
            "chromaticity_diagrams": list(chromaticity.DIAGRAMS),
            "lut_interpolators": list(lut.INTERPOLATORS),
            "transfer_encodings": {
                "default": list(transfer.DEFAULT_ENCODINGS),
                "luma": list(transfer.LUMA_PRESETS),
            },
            "quality": {
                "cri": list(quality.CRI_METHODS),
                "cqs": list(quality.CQS_METHODS),
                "fidelity": list(quality.FIDELITY_METHODS),
            },
            "recovery": list(recovery.METHODS),
            "correction": list(correction.METHODS),
            "interpolators": list(interpolate.INTERPOLATORS),
            "plots": list(gallery.PLOTS),
            "invoke_whitelist": list(invoke.WHITELIST),
        },
        "counts": {
            "rgb_colourspaces": len(colour.RGB_COLOURSPACES),
            "illuminants": len(colour.SDS_ILLUMINANTS),
            "cmfs": len(colour.MSDS_CMFS),
            "cat_matrices": len(adapt.CAT_ATTRIBUTES),
            "appearance_models": len(appearance.MODELS),
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
            "POST /api/v1/transfer",
            "GET /api/v1/chromaticity",
            "GET /api/v1/chromaticity.svg",
            "POST /api/v1/volume",
            "POST /api/v1/temperature",
            "POST /api/v1/quality",
            "POST /api/v1/lut",
            "POST /api/v1/adapt",
            "POST /api/v1/appearance",
            "POST /api/v1/phenomena-vision",
            "POST /api/v1/corresponding",
            "POST /api/v1/cvd",
            "POST /api/v1/recovery",
            "POST /api/v1/correction",
            "POST /api/v1/notation",
            "POST /api/v1/interpolate",
            "POST /api/v1/geometry",
            "POST /api/v1/optics",
            "POST /api/v1/plot",
            "GET /api/v1/catalog",
            "POST /api/v1/catalog/invoke",
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


# --------------------------------------------------------------------------- #
# M2：面板 09–18
# --------------------------------------------------------------------------- #
@router.get("/chromaticity")
def get_chromaticity(
    diagram: str = "CIE 1931",
    gamuts: str | None = None,
    colors: str | None = None,
) -> dict:
    return chromaticity.chromaticity_data(diagram, _csv(gamuts) or chromaticity.DEFAULT_GAMUTS, _csv(colors))


@router.get("/chromaticity.svg")
def get_chromaticity_svg(
    diagram: str = "CIE 1931",
    gamuts: str | None = None,
    colors: str | None = None,
    if_none_match: str | None = Header(default=None),
) -> Response:
    """色度图（唯一的图端点）：ETag 由参数算出，命中就回 304，不重画。"""

    names = _csv(gamuts) or chromaticity.DEFAULT_GAMUTS
    specs = _csv(colors)
    etag = chromaticity.svg_etag(diagram, names, specs)
    cache_headers = {"ETag": etag, "Cache-Control": "public, max-age=86400, immutable"}

    if if_none_match and if_none_match == etag:
        return Response(status_code=304, headers=cache_headers)

    return Response(
        content=chromaticity.render_svg(diagram, names, specs),
        media_type="image/svg+xml",
        headers={**cache_headers, "Content-Disposition": 'inline; filename="chromaticity.svg"'},
    )


@router.post("/transfer")
def post_transfer(payload: TransferRequest) -> dict:
    return transfer.transfer_data(
        colours=payload.colors,
        encodings=payload.encodings,
        samples=payload.samples,
        luma=payload.luma,
        bits=payload.bits,
        limited_range=payload.limited_range,
    )


@router.post("/volume")
def post_volume(payload: VolumeRequest) -> dict:
    return volume.volume_data(
        spaces=payload.spaces, samples=payload.samples, seed=payload.seed, colours=payload.colors
    )


@router.post("/temperature")
def post_temperature(payload: TemperatureRequest) -> dict:
    return temperature.temperature_data(
        colours=payload.colors, cct=payload.cct, duv=payload.duv, locus_points=payload.locus_points
    )


@router.post("/quality")
def post_quality(payload: QualityRequest) -> dict:
    return quality.quality_data(
        illuminants=payload.illuminants, reference=payload.reference, include_special=payload.include_special
    )


@router.post("/lut")
def post_lut(payload: LutRequest) -> dict:
    return lut.lut_data(
        colours=payload.colors,
        size=payload.size,
        gains=payload.gains,
        interpolators=payload.interpolators,
        ramp_steps=payload.ramp_steps,
    )


@router.post("/adapt")
def post_adapt(payload: AdaptRequest) -> dict:
    return adapt.adapt_data(
        payload.colors,
        source=payload.source,
        target=payload.target,
        methods=payload.methods,
        include_matrices=payload.include_matrices,
    )


@router.post("/appearance")
def post_appearance(payload: AppearanceRequest) -> dict:
    return appearance.appearance_data(
        payload.colors,
        models=payload.models,
        L_A=payload.L_A,
        Y_b=payload.Y_b,
        surround=payload.surround,
    )


@router.post("/phenomena-vision")
def post_phenomena_vision(payload: PhenomenaRequest) -> dict:
    return phenomena.phenomena_data(
        colours=payload.colors,
        luminances=payload.luminances,
        chroma_max=payload.chroma_max,
        points=payload.points,
    )


@router.post("/corresponding")
def post_corresponding(payload: CorrespondingRequest) -> dict:
    return corresponding.corresponding_data(
        experiment=payload.experiment,
        models=payload.models,
        include_leaderboard=payload.include_leaderboard,
    )


@router.post("/cvd")
def post_cvd(payload: CvdRequest) -> dict:
    return cvd.cvd_data(
        payload.colors,
        deficiency=payload.deficiency,
        severity=payload.severity,
        severities=payload.severities,
    )


# --------------------------------------------------------------------------- #
# M3：面板 19–25
# --------------------------------------------------------------------------- #
@router.post("/recovery")
def post_recovery(payload: RecoveryRequest) -> dict:
    return recovery.recovery_data(colours=payload.colors, methods=payload.methods, step=payload.step)


@router.post("/correction")
def post_correction(payload: CorrectionRequest) -> dict:
    return correction.correction_data(methods=payload.methods)


@router.post("/notation")
def post_notation(payload: NotationRequest) -> dict:
    return notation.notation_data(
        munsell=payload.munsell,
        keyword=payload.keyword,
        hex_value=payload.hex_color,
        value_y=payload.value_y,
    )


@router.post("/interpolate")
def post_interpolate(payload: InterpolateRequest) -> dict:
    return interpolate.interpolate_data(
        illuminant=payload.illuminant,
        coarse_step=payload.coarse_step,
        target_step=payload.target_step,
        start=payload.start,
        end=payload.end,
        interpolators=payload.interpolators,
    )


@router.post("/geometry")
def post_geometry(payload: GeometryRequest) -> dict:
    return geometry.geometry_data(ellipse_index=payload.ellipse_index, include_all=payload.include_all)


@router.post("/optics")
def post_optics(payload: OpticsRequest) -> dict:
    return optics.optics_data(
        thicknesses=payload.thicknesses,
        start=payload.start,
        end=payload.end,
        step=payload.step,
        substrate_points=payload.substrate_points,
    )


@router.post("/plot")
def post_plot(payload: PlotRequest) -> dict:
    return gallery.gallery_data(names=payload.plots)


# --------------------------------------------------------------------------- #
# M4：面板 26–28
# --------------------------------------------------------------------------- #
@router.get("/catalog")
def get_catalog(
    q: str | None = None,
    status: str | None = None,
    module: str | None = None,
    limit: int = catalog.DEFAULT_LIMIT,
    offset: int = 0,
) -> dict:
    """能力目录：1284 条子模块导出 × 归属状态（面板 / 数据集 / 内部），可按关键字与状态过滤。"""

    return catalog.catalog_index(query=q, status=status, module=module, limit=limit, offset=offset)


@router.post("/catalog/invoke")
def post_catalog_invoke(payload: InvokeRequest) -> dict:
    """白名单参数化调用（方案 11：不用 eval / 动态导入，白名单是静态表）。"""

    return invoke.invoke(payload.model_dump(exclude_none=True))
