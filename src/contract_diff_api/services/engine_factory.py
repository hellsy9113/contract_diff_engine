from functools import lru_cache

from contract_diff.core.services.contract_diff_engine import ContractDiffEngine


@lru_cache(maxsize=1)
def get_engine() -> ContractDiffEngine:
    return ContractDiffEngine()
