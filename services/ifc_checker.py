import xml.etree.ElementTree as ET
import multiprocessing
try:
    # pyrefly: ignore [missing-import]
    import ifcopenshell
    import ifcopenshell.util.element
    import ifcopenshell.geom
    IFCOPENSHELL_AVAILABLE = True
except ImportError:
    IFCOPENSHELL_AVAILABLE = False


# ---------------------------------------------------------------------------
# Required properties per IFC type (Нормативы)
# ---------------------------------------------------------------------------
REQUIRED_PROPS = {
    "IfcWall":    ["FireRating", "IsExternal", "ThermalTransmittance"],
    "IfcColumn":  ["LoadBearing", "FireRating"],
    "IfcSlab":    ["LoadBearing", "FireRating", "ThermalTransmittance"],
    "IfcBeam":    ["LoadBearing", "FireRating"],
    "IfcDoor":    ["FireRating", "AcousticRating"],
    "IfcWindow":  ["ThermalTransmittance", "AcousticRating"],
}

# Generic placeholder names that should be flagged
GENERIC_NAMES = {"Basic Wall", "Basic Floor", "Generic", "Unnamed", ""}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_all_props(element) -> dict:
    """Flatten all property sets of an element into a single dict."""
    try:
        psets = ifcopenshell.util.element.get_psets(element)
        flat = {}
        for pset_values in psets.values():
            if isinstance(pset_values, dict):
                flat.update(pset_values)
        return flat
    except Exception:
        return {}


def _get_storey(element) -> str:
    """Return the name of the IfcBuildingStorey that contains *element*."""
    try:
        container = ifcopenshell.util.element.get_container(element)
        while container and not container.is_a("IfcBuildingStorey"):
            container = ifcopenshell.util.element.get_container(container)
        if container and container.Name:
            return container.Name
    except Exception:
        pass
    # Fallback: use element's own Name or its IFC type
    try:
        el_name = getattr(element, "Name", None)
        if el_name and el_name.strip():
            return el_name.strip()
    except Exception:
        pass
    return "Без привязки к этажу"


def _guid(element) -> str:
    try:
        return element.GlobalId or "N/A"
    except Exception:
        return "N/A"


def _name(element) -> str:
    try:
        return getattr(element, "Name", None) or "Без имени"
    except Exception:
        return "Без имени"


# ---------------------------------------------------------------------------
# Check 1 — Schema & Structure
# ---------------------------------------------------------------------------

def _check_schema(model: "ifcopenshell.file", issues: list, issue_id_counter: list):
    # IfcProject must exist
    if not model.by_type("IfcProject"):
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Схема",
            "severity": "ERROR",
            "description": "IfcProject отсутствует в модели",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1

    # Mandatory spatial hierarchy
    for ifc_type in ["IfcSite", "IfcBuilding", "IfcBuildingStorey"]:
        if not model.by_type(ifc_type):
            issues.append({
                "id": issue_id_counter[0],
                "guid": "N/A",
                "type": "Схема",
                "severity": "WARNING",
                "description": f"Пространственный элемент '{ifc_type}' отсутствует в модели",
                "location": "Вся модель",
            })
            issue_id_counter[0] += 1

    # GlobalId check
    missing_guid_count = 0
    for element in model.by_type("IfcProduct"):
        if not element.GlobalId:
            missing_guid_count += 1

    if missing_guid_count:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Схема",
            "severity": "ERROR",
            "description": f"Обнаружено {missing_guid_count} элементов без GlobalId",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1
    else:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Схема",
            "severity": "OK",
            "description": "Все элементы имеют GlobalId",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1


# ---------------------------------------------------------------------------
# Check 2 — Property Sets (Нормативы)
# ---------------------------------------------------------------------------

def _check_norms(model: "ifcopenshell.file", issues: list, issue_id_counter: list):
    for ifc_type, required in REQUIRED_PROPS.items():
        elements = model.by_type(ifc_type)
        if not elements:
            continue

        missing_map: dict[str, list] = {prop: [] for prop in required}

        for element in elements:
            all_props = _get_all_props(element)
            for prop in required:
                if prop not in all_props:
                    missing_map[prop].append(element)

        for prop, bad_elements in missing_map.items():
            if not bad_elements:
                continue
            # Group report: one issue per (type, missing_prop)
            count = len(bad_elements)
            sample_guid = _guid(bad_elements[0])
            sample_storey = _get_storey(bad_elements[0])
            location = sample_storey if count == 1 else f"{sample_storey} и др. ({count} элементов)"
            issues.append({
                "id": issue_id_counter[0],
                "guid": sample_guid,
                "type": "Нормативы",
                "severity": "ERROR",
                "description": f"Отсутствует обязательное свойство '{prop}' на элементах {ifc_type}",
                "location": location,
            })
            issue_id_counter[0] += 1

    # Room height check — СП 54.13330.2022 п.4.4 (min 2.7 m residential)
    for space in model.by_type("IfcSpace"):
        all_props = _get_all_props(space)
        raw_height = (
            all_props.get("Height")
            or all_props.get("NetHeight")
            or all_props.get("FinishCeilingHeight")
        )
        if raw_height is None:
            continue
        try:
            height = float(raw_height)
        except (TypeError, ValueError):
            continue

        storey = _get_storey(space)
        space_name = _name(space)

        if height < 2.7:
            issues.append({
                "id": issue_id_counter[0],
                "guid": _guid(space),
                "type": "Нормативы",
                "severity": "ERROR",
                "description": (
                    f"Высота помещения '{space_name}' ниже нормативной: "
                    f"{height:.2f}м < 2.7м (СП 54.13330.2022 п.4.4)"
                ),
                "location": storey,
            })
            issue_id_counter[0] += 1


# ---------------------------------------------------------------------------
# Check 3 — Naming Convention
# ---------------------------------------------------------------------------

def _check_naming(model: "ifcopenshell.file", issues: list, issue_id_counter: list):
    no_name_count = 0
    generic_count = 0

    for element in model.by_type("IfcProduct"):
        name = getattr(element, "Name", None)

        if not name or name.strip() == "":
            no_name_count += 1
        elif name.strip() in GENERIC_NAMES:
            generic_count += 1

    if no_name_count:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Именование",
            "severity": "WARNING",
            "description": f"{no_name_count} элементов не имеют имени (Name = пусто)",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1

    if generic_count:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Именование",
            "severity": "WARNING",
            "description": f"{generic_count} элементов имеют шаблонное имя (Basic Wall, Generic и т.д.)",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1


# ---------------------------------------------------------------------------
# Check 4 — Clash Detection (Bounding Box)
# ---------------------------------------------------------------------------

def _check_clashes(model: "ifcopenshell.file", issues: list, issue_id_counter: list):
    settings = ifcopenshell.geom.settings()
    elements_with_bbox = []

    # Use the iterator — processes geometry in batches, far faster than create_shape per element
    try:
        iterator = ifcopenshell.geom.iterator(
            settings, model, multiprocessing.cpu_count()
        )
        has_item = iterator.initialize()
    except Exception:
        has_item = False

    if has_item:
        while True:
            try:
                shape = iterator.get()
                element = model.by_id(shape.id)
                if element is None:
                    continue
                verts = shape.geometry.verts
                if not verts:
                    continue
                xs = verts[0::3]
                ys = verts[1::3]
                zs = verts[2::3]
                elements_with_bbox.append({
                    "element": element,
                    "min": (min(xs), min(ys), min(zs)),
                    "max": (max(xs), max(ys), max(zs)),
                })
                # Cap geometry loading at 500 elements to stay fast
                if len(elements_with_bbox) >= 500:
                    break
            except Exception:
                pass
            if not iterator.next():
                break

    def bbox_intersects(a, b) -> bool:
        return (
            a["min"][0] < b["max"][0] and a["max"][0] > b["min"][0]
            and a["min"][1] < b["max"][1] and a["max"][1] > b["min"][1]
            and a["min"][2] < b["max"][2] and a["max"][2] > b["min"][2]
        )

    clash_count = 0
    CAP = 20

    for i in range(len(elements_with_bbox)):
        if clash_count >= CAP:
            break
        for j in range(i + 1, len(elements_with_bbox)):
            if clash_count >= CAP:
                break
            a = elements_with_bbox[i]
            b = elements_with_bbox[j]
            if a["element"].is_a() == b["element"].is_a():
                continue
            if bbox_intersects(a, b):
                el_a = a["element"]
                el_b = b["element"]
                issues.append({
                    "id": issue_id_counter[0],
                    "guid": _guid(el_a),
                    "type": "Коллизия",
                    "severity": "ERROR",
                    "description": (
                        f"Пересечение: {el_a.is_a()} '{_name(el_a)}' "
                        f"и {el_b.is_a()} '{_name(el_b)}'"
                    ),
                    "location": _get_storey(el_a),
                })
                issue_id_counter[0] += 1
                clash_count += 1

    if clash_count == 0:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Коллизия",
            "severity": "OK",
            "description": "Коллизии не обнаружены (проверка ограничивающих объёмов)",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1


# ---------------------------------------------------------------------------
# Check 5 — IDS Validation
# ---------------------------------------------------------------------------

def _check_ids(
    model: "ifcopenshell.file",
    ids_path: str,
    issues: list,
    issue_id_counter: list,
):
    try:
        tree = ET.parse(ids_path)
    except Exception as exc:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "IDS",
            "severity": "ERROR",
            "description": f"Не удалось прочитать IDS файл: {exc}",
            "location": "N/A",
        })
        issue_id_counter[0] += 1
        return

    root = tree.getroot()
    ns = {"ids": "http://standards.buildingsmart.org/IDS"}

    for spec in root.findall(".//ids:specification", ns):
        spec_name = spec.get("name", "Unnamed requirement")
        applicability = spec.find(".//ids:applicability", ns)
        requirements = spec.find(".//ids:requirements", ns)

        entity_el = (
            applicability.find(".//ids:name/ids:simpleValue", ns)
            if applicability is not None
            else None
        )
        entity_name = entity_el.text if entity_el is not None else None

        if not entity_name:
            continue

        try:
            elements = model.by_type(entity_name)
        except Exception:
            continue

        if not elements:
            continue

        prop_reqs = requirements.findall(".//ids:property", ns) if requirements is not None else []

        for prop_req in prop_reqs:
            pset_el = prop_req.find(".//ids:propertySetName/ids:simpleValue", ns)
            name_el = prop_req.find(".//ids:baseName/ids:simpleValue", ns)
            if pset_el is None or name_el is None:
                continue

            required_pset = pset_el.text
            required_prop = name_el.text
            failing = []

            for element in elements:
                try:
                    psets = ifcopenshell.util.element.get_psets(element)
                    found = required_pset in psets and required_prop in psets.get(required_pset, {})
                except Exception:
                    found = False
                if not found:
                    failing.append(element)

            if failing:
                count = len(failing)
                sample = failing[0]
                storey = _get_storey(sample)
                location = storey if count == 1 else f"{storey} и др. ({count} элементов)"
                issues.append({
                    "id": issue_id_counter[0],
                    "guid": _guid(sample),
                    "type": "IDS",
                    "severity": "ERROR",
                    "description": (
                        f"IDS '{spec_name}': свойство '{required_pset}.{required_prop}' "
                        f"отсутствует у {entity_name}"
                    ),
                    "location": location,
                })
                issue_id_counter[0] += 1
            else:
                issues.append({
                    "id": issue_id_counter[0],
                    "guid": "N/A",
                    "type": "IDS",
                    "severity": "OK",
                    "description": (
                        f"IDS '{spec_name}': '{required_pset}.{required_prop}' "
                        f"присутствует у всех {entity_name} ({len(elements)} эл.)"
                    ),
                    "location": "Вся модель",
                })
                issue_id_counter[0] += 1


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_checks(
    ifc_path: str,
    selected_checks: list,
    ids_path: str = None,
) -> dict:
    """
    Parse *ifc_path* and run the requested checks.

    Parameters
    ----------
    ifc_path       : absolute path to the uploaded .ifc file
    selected_checks: list of strings — "schema", "norms", "naming",
                     "clashes", "ids"  (keys used by the frontend)
    ids_path       : optional path to an IDS XML file
    """
    if not IFCOPENSHELL_AVAILABLE:
        return {
            "summary": {"total": 0, "errors": 1, "warnings": 0, "passed": 0},
            "issues": [{
                "id": 1,
                "guid": "N/A",
                "type": "Схема",
                "severity": "ERROR",
                "description": "Библиотека ifcopenshell не установлена на сервере",
                "location": "N/A",
            }],
        }

    # Open the model ---------------------------------------------------------
    try:
        model = ifcopenshell.open(ifc_path)
    except Exception as exc:
        return {
            "summary": {"total": 0, "errors": 1, "warnings": 0, "passed": 0},
            "issues": [{
                "id": 1,
                "guid": "N/A",
                "type": "Схема",
                "severity": "ERROR",
                "description": f"Не удалось открыть IFC файл: {exc}",
                "location": "N/A",
            }],
        }

    total_elements = len(model.by_type("IfcProduct"))
    issues: list = []
    issue_id_counter = [1]  # mutable counter shared across helpers

    # Run requested checks ---------------------------------------------------
    # "schema" / "clashes" / "norms" / "naming" / "ids"
    # The frontend may send different key names — normalise to lower-case
    selected = [s.lower() for s in selected_checks]

    if not selected or "schema" in selected:
        _check_schema(model, issues, issue_id_counter)

    if "norms" in selected:
        _check_norms(model, issues, issue_id_counter)

    if "naming" in selected:
        _check_naming(model, issues, issue_id_counter)

    if "clashes" in selected:
        _check_clashes(model, issues, issue_id_counter)

    if "ids" in selected and ids_path:
        _check_ids(model, ids_path, issues, issue_id_counter)
    elif "ids" in selected and not ids_path:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "IDS",
            "severity": "WARNING",
            "description": "IDS проверка запрошена, но файл IDS не загружен",
            "location": "N/A",
        })
        issue_id_counter[0] += 1

    # Build summary ----------------------------------------------------------
    errors   = sum(1 for i in issues if i["severity"] == "ERROR")
    warnings = sum(1 for i in issues if i["severity"] == "WARNING")
    passed   = sum(1 for i in issues if i["severity"] == "OK")
    total_checks = len(issues)

    return {
        "summary": {
            "total":    total_elements,   # real IFC element count
            "errors":   errors,           # number of error findings
            "warnings": warnings,         # number of warning findings
            "passed":   passed,           # number of checks that passed (OK)
        },
        "issues": issues,
    }
