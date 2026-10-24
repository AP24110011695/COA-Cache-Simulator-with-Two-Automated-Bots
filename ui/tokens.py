"""Design tokens (docs/design.md §4) — the single Python source for colors
and layout constants. ui/styles.css mirrors them as CSS variables and the
charts import the same values so CSS and matplotlib never drift
(docs/design.md §11)."""

ACCENT = "#1F5FA8"
ACCENT_SOFT = "#E8F0F8"
BG = "#FFFFFF"
BG_SUBTLE = "#F5F7FA"
BORDER = "#D9DEE4"
TEXT = "#1F2933"
TEXT_SECONDARY = "#52606D"
SUCCESS = "#2E7D32"
SUCCESS_SOFT = "#E6F2E8"
DANGER = "#C62828"
DANGER_SOFT = "#FBEAEA"
WARNING = "#B26A00"
WARNING_SOFT = "#FBF1E2"
BOT2 = "#0B7285"

CHART_HITS = SUCCESS
CHART_MISSES = DANGER
CHART_EVICTIONS = WARNING

MAX_CONTENT_WIDTH = 1100
EVENT_TABLE_ROWS = 500

# Widget choices — powers of two per prd.md 5 (the engine re-validates
# authoritatively; the selects make invalid input untypable).
BLOCK_SIZES = [1, 2, 4, 8, 16, 32, 64, 128]
CAPACITIES = [2 ** exponent for exponent in range(0, 21)]  # 1 .. 2^20 B
ADDRESS_WIDTH_MIN = 4
ADDRESS_WIDTH_MAX = 64
