from api.app.schemas import CitationOut, RulesOut
from rules.loader import load_rules


def current_rules() -> RulesOut:
    rules = load_rules()
    return RulesOut(
        version=rules.version,
        effective_from=rules.effective_from,
        checked_on=rules.checked_on,
        subsidy=rules.subsidy,
        sizing=rules.sizing,
        payback=rules.payback,
        scoring=rules.scoring,
        citations=[
            CitationOut(key=key, **citation.model_dump())
            for key, citation in rules.citations.items()
        ],
    )
