"""SolidWorks COM selection wrappers for structured reference selectors."""

from __future__ import annotations

from typing import Any

from cad_tools.cad_schemas import ReferenceSpec


class SolidWorksReferenceResolver:
    """Resolve structured selectors against inserted SolidWorks components."""

    def resolve(self, component: Any, selector: ReferenceSpec) -> Any:
        if selector.entity_type in {"component_origin", "axis", "center"}:
            return component
        if selector.entity_type in {"front_plane", "top_plane", "right_plane"}:
            return self._select_named_reference(component, selector.reference_name or selector.entity_type)
        return self._select_by_rule(component, selector)

    def _select_named_reference(self, component: Any, name: str) -> Any:
        try:
            selected = component.Select4(False, None, False)
            print(f"[SolidWorks] Selected component for named reference {name}: {selected}")
        except Exception as exc:
            raise RuntimeError(f"Could not select component reference {name}") from exc
        return component if selected is not False else None

    def _select_by_rule(self, component: Any, selector: ReferenceSpec) -> Any:
        try:
            selected = component.Select4(False, None, False)
            print(
                "[SolidWorks] Selected component for "
                f"{selector.entity_type}/{selector.selection_rule}: {selected}"
            )
        except Exception as exc:
            raise RuntimeError(
                f"Could not select {selector.entity_type} with rule {selector.selection_rule}"
            ) from exc
        return component if selected is not False else None
