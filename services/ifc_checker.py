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
                issues.append({
                    "id": issue_id_counter[0],
                    "guid": "N/A",
                    "type": "Нормативы",
                    "severity": "OK",
                    "description": f"Обязательное свойство '{prop}' присутствует у всех элементов {ifc_type}",
                    "location": "Вся модель",
                })
                issue_id_counter[0] += 1
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
    height_issues_found = False
    spaces = model.by_type("IfcSpace")
    for space in spaces:
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
            height_issues_found = True
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

    if not height_issues_found and spaces:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Нормативы",
            "severity": "OK",
            "description": f"Высота всех {len(spaces)} помещений соответствует нормам (≥ 2.7м)",
            "location": "Вся модель",
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

    if no_name_count == 0 and generic_count == 0:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Именование",
            "severity": "OK",
            "description": "Все элементы имеют корректные уникальные имена",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1


# ---------------------------------------------------------------------------
# Check 4 — Clash Detection (Bounding Box)
# ---------------------------------------------------------------------------

def _load_geometry(model, settings, result_list, max_elements=400):
    """Load bounding boxes in a background thread (single-threaded, no multiprocessing)."""
    try:
        # num_threads=1 avoids the Windows multiprocessing deadlock
        iterator = ifcopenshell.geom.iterator(settings, model, 1)
        if not iterator.initialize():
            return
        while True:
            try:
                shape = iterator.get()
                element = model.by_id(shape.id)
                if element is not None:
                    verts = shape.geometry.verts
                    if verts:
                        xs = verts[0::3]
                        ys = verts[1::3]
                        zs = verts[2::3]
                        result_list.append({
                            "element": element,
                            "is_a": element.is_a(),
                            "name": _name(element),
                            "storey": _get_storey(element),
                            "min": (min(xs), min(ys), min(zs)),
                            "max": (max(xs), max(ys), max(zs)),
                        })
                        if len(result_list) >= max_elements:
                            break
            except Exception:
                pass
            if not iterator.next():
                break
    except Exception:
        pass


def _check_clashes(model: "ifcopenshell.file", issues: list, issue_id_counter: list):
    import threading
    settings = ifcopenshell.geom.settings()
    elements_with_bbox = []

    # Run geometry loading in a daemon thread with a hard 30-second timeout.
    # This prevents the Windows multiprocessing deadlock from hanging the server.
    loader = threading.Thread(
        target=_load_geometry,
        args=(model, settings, elements_with_bbox),
        daemon=True,
    )
    loader.start()
    loader.join(timeout=30)  # give geometry loading at most 30 seconds

    if loader.is_alive():
        # Geometry loading timed out — report a warning and skip clash math
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Коллизия",
            "severity": "WARNING",
            "description": "Проверка коллизий пропущена: загрузка геометрии заняла более 30 сек.",
            "location": "Вся модель",
        })
        issue_id_counter[0] += 1
        return

    clash_count = 0
    REPORT_CAP = 50  # show at most 50 clash rows; bbox clashes produce many false positives

    # O(N log N) Sweep and Prune algorithm for ultra-fast collision checking
    elements_with_bbox.sort(key=lambda x: x["min"][0])

    for i in range(len(elements_with_bbox)):
        a = elements_with_bbox[i]
        for j in range(i + 1, len(elements_with_bbox)):
            b = elements_with_bbox[j]

            # Since array is sorted by min X, if b's min X > a's max X no further j can match
            if b["min"][0] > a["max"][0]:
                break

            if a["is_a"] == b["is_a"]:
                continue

            # Check Y and Z axis intersections
            if (a["min"][1] < b["max"][1] and a["max"][1] > b["min"][1] and
                    a["min"][2] < b["max"][2] and a["max"][2] > b["min"][2]):

                clash_count += 1
                if clash_count <= REPORT_CAP:
                    el_a = a["element"]
                    issues.append({
                        "id": issue_id_counter[0],
                        "guid": _guid(el_a),
                        "type": "Коллизия",
                        "severity": "ERROR",
                        "description": (
                            f"Пересечение: {a['is_a']} '{a['name']}' "
                            f"и {b['is_a']} '{b['name']}'"
                        ),
                        "location": a["storey"],
                    })
                    issue_id_counter[0] += 1

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
    elif clash_count > REPORT_CAP:
        issues.append({
            "id": issue_id_counter[0],
            "guid": "N/A",
            "type": "Коллизия",
            "severity": "WARNING",
            "description": (
                f"Всего обнаружено {clash_count} пересечений ограничивающих объёмов. "
                f"Показаны первые {REPORT_CAP}. Часть может быть ложными срабатываниями — "
                f"рекомендуется детальная проверка в Revit/Navisworks."
            ),
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
