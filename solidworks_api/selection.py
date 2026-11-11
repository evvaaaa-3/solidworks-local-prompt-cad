"""SolidWorks COM selection wrappers for structured reference selectors."""

from __future__ import annotations

from typing import Any

from cad_tools.cad_schemas import ReferenceSpec
from solidworks_api.geometry import (
    resolve_cylindrical_axis,
    resolve_planar_face_frame,
    select_face,
)


class SolidWorksReferenceResolver:
    """Resolve structured selectors against inserted SolidWorks components."""

    def resolve(self, component: Any, selector: ReferenceSpec, append: bool = True) -> Any:
        if selector.entity_type in {"component_origin", "center"}:
            return component
        if selector.entity_type in {"front_plane", "top_plane", "right_plane"}:
            return self._select_named_reference(component, selector.reference_name or selector.entity_type)
        return self._select_by_rule(component, selector, append=append)

    def _select_named_reference(self, component: Any, name: str) -> Any:
        try:
            selected = component.Select4(False, None, False)
            print(f"[SolidWorks] Selected component for named reference {name}: {selected}")
        except Exception as exc:
            raise RuntimeError(f"Could not select component reference {name}") from exc
        return component if selected is not False else None

    def _select_by_rule(self, component: Any, selector: ReferenceSpec, append: bool) -> Any:
        if selector.entity_type == "planar_face":
            frame = resolve_planar_face_frame(component, selector.selection_rule)
            if not select_face(frame.face, append=append):
                raise RuntimeError(
                    f"Resolved planar face {selector.selection_rule}, but SolidWorks refused face selection."
                )
            print(
                "[SolidWorks] Selected planar face "
                f"{selector.selection_rule}: point={frame.point_mm} normal={frame.normal}"
            )
            return frame.face
        if selector.entity_type in {"cylindrical_face", "axis"} or selector.selection_rule in {"axis", "largest_radius"}:
            cylinder = resolve_cylindrical_axis(component)
            if not select_face(cylinder.face, append=append):
                raise RuntimeError("Resolved cylindrical face, but SolidWorks refused face selection.")
            print(f"[SolidWorks] Selected cylindrical axis face: point={cylinder.point_mm} axis={cylinder.axis}")
            return cylinder.face
        raise RuntimeError(
            "Structured geometry selection is not implemented for "
            f"{selector.entity_type}/{selector.selection_rule}; refusing to mate whole component."
        )
