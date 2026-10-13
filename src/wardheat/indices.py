"""Ward heat risk = Hazard × Exposure × Vulnerability (IPCC AR6).

    H  hazard         how hot the ward gets: built-up surfaces by day + the night
    E  exposure       how many people live there (people per km²)
    V  vulnerability  how little tree shade there is

Recipe
------
1. Scale each ingredient to 0-1 between the city's 5th and 95th percentile, so
   the result ranks wards *within* Bengaluru. Floor at 0.05 so a single zero
   cannot wipe a ward out.
2. Combine with a geometric mean, ``(H·E·V)^(1/3)``: a ward has to score on
   all three to rank high. Extreme heat where nobody lives is not high risk.
3. Top 30 % of wards → High, next 30 % → Medium, the rest → Low.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

FLOOR = 0.05
CLASS_ORDER = ["Low", "Medium", "High"]


def scale01(x: pd.Series, floor: float = FLOOR) -> pd.Series:
    """0 = among the city's lowest 5 %, 1 = among the highest 5 %."""
    x = pd.Series(x, dtype="float64")
    lo, hi = np.nanpercentile(x, [5, 95])
    return ((x - lo) / (hi - lo)).clip(floor, 1)


def classify(score: pd.Series, cuts=(40, 70)) -> pd.Series:
    """Low / Medium / High by city percentiles of ``score``."""
    lo, hi = np.nanpercentile(score, cuts)
    return pd.Series(np.select([score >= hi, score >= lo], ["High", "Medium"], "Low"), index=score.index)


def ward_risk(f: pd.DataFrame) -> pd.DataFrame:
    """H, E, V (0-1), the risk score (0-100) and class for every ward of the feature table."""
    H = (scale01(f["lst_built"]) + scale01(f["lst_night"])) / 2
    E = scale01(np.log(f["pop_density"]))  # log: a 2x denser ward is not 2x the risk
    V = scale01(-f["canopy_frac"])
    score = (H * E * V) ** (1 / 3) * 100
    return pd.DataFrame({"H": H, "E": E, "V": V, "score": score, "risk": classify(score)}, index=f.index)
