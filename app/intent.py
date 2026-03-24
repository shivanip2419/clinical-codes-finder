import re
from typing import List

from app.models import SystemName
from app.normalization import normalize_query_text


def infer_systems(query: str) -> List[SystemName]:
    q = normalize_query_text(query)
    systems: List[SystemName] = []

    if re.search(r"\bmg\/dl\b|\bmmol\/l\b|\bunit\b|\bmcg\b|\bmg\b", q):
        systems.append("UCUM")
    if re.search(r"\btest\b|\bpanel\b|\blab\b|\bglucose\b|\ba1c\b", q):
        systems.append("LOINC")
    if re.search(r"\bmg\b|\btablet\b|\bcapsule\b|\bmetformin\b|\binsulin\b", q):
        systems.append("RXTERMS")
    if re.search(r"\bwheelchair\b|\bprosthetic\b|\bsupply\b|\bdevice\b", q):
        systems.append("HCPCS")
    if re.search(r"\bataxia\b|\bphenotype\b|\bsymptom\b", q):
        systems.append("HPO")
    if re.search(r"\bdiabetes\b|\btuberculosis\b|\bdisease\b|\bdiagnosis\b|\bcancer\b", q):
        systems.append("ICD10CM")

    if not systems:
        systems = ["ICD10CM", "LOINC", "RXTERMS"]

    # Keep order, remove duplicates.
    return list(dict.fromkeys(systems))
