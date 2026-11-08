import { useState } from "react";

const CRITERIA = [
  { key: "mat_do", label: "Mật độ lây lan" },
  { key: "chi_phi", label: "Chi phí" },
  { key: "thoi_gian", label: "Thời gian tác dụng" },
  { key: "an_toan", label: "An toàn sinh thái" },
];

const PAIRS = [
  [0, 1],
  [0, 2],
  [0, 3],
  [1, 2],
  [1, 3],
  [2, 3],
];

const INITIAL_COMPARISONS = PAIRS.map(() => 0);

export function bipolarToSaaty(sliderValue) {
  const value = Number(sliderValue);
  if (!Number.isInteger(value) || value < -8 || value > 8) {
    return 1;
  }
  if (value === 0) {
    return 1;
  }

  const saatyScale = Math.abs(value) + 1;
  return value < 0 ? saatyScale : 1 / saatyScale;
}

function pairLabel(leftIndex, rightIndex) {
  return `${CRITERIA[leftIndex].label} và ${CRITERIA[rightIndex].label}`;
}

function comparisonDescription(value, leftLabel, rightLabel) {
  if (value === 0) {
    return "Hai tiêu chí ngang nhau";
  }
  const preferredLabel = value < 0 ? leftLabel : rightLabel;
  return `${preferredLabel} được ưu tiên ${Math.abs(value) + 1}/9`;
}

export default function AHPForm({ apiUrl = "/api/ahp" }) {
  const [comparisons, setComparisons] = useState(INITIAL_COMPARISONS);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function updateComparison(index, value) {
    setComparisons((current) => ({
      ...current,
      [index]: Number(value),
    }));
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);

    const values = comparisons.map(bipolarToSaaty);

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comparisons: values }),
      });
      const payload = await response.json().catch(() => ({}));

      if (!response.ok) {
        if (response.status === 400) {
          setError(
            payload.detail ||
              "Đánh giá mâu thuẫn. Vui lòng kéo lại các thanh trượt.",
          );
        } else {
          setError(payload.detail || "Không thể phân tích AHP.");
        }
        return;
      }

      setResult(payload.data || payload);
    } catch {
      setError("Không thể kết nối Backend. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="mx-auto w-full max-w-3xl rounded-2xl bg-white p-4 shadow-lg sm:p-6">
      <header className="mb-6">
        <p className="text-sm font-semibold uppercase tracking-wide text-emerald-700">
          Hỗ trợ ra quyết định
        </p>
        <h1 className="mt-1 text-2xl font-bold text-slate-900">
          So sánh tiêu chí AHP
        </h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          Kéo về bên trái để ưu tiên tiêu chí bên trái, về bên phải để ưu tiên
          tiêu chí bên phải. Ở chính giữa, hai tiêu chí được xem là ngang nhau.
        </p>
      </header>

      <form className="space-y-5" onSubmit={submit}>
        {PAIRS.map(([leftIndex, rightIndex], index) => {
          const value = comparisons[index];
          return (
            <fieldset
              key={`${leftIndex}-${rightIndex}`}
              className="rounded-xl border border-slate-200 p-4"
            >
              <legend className="px-1 text-sm font-semibold text-slate-800">
                So sánh {pairLabel(leftIndex, rightIndex)}
              </legend>
              <div className="mt-3 flex items-center justify-between gap-3 text-xs font-semibold text-slate-600">
                <span className="max-w-[38%] text-left">
                  {CRITERIA[leftIndex].label}
                </span>
                <output
                  className="rounded-full bg-emerald-50 px-3 py-1 text-center text-emerald-700"
                  aria-live="polite"
                >
                  {comparisonDescription(
                    value,
                    CRITERIA[leftIndex].label,
                    CRITERIA[rightIndex].label,
                  )}
                </output>
                <span className="max-w-[38%] text-right">
                  {CRITERIA[rightIndex].label}
                </span>
              </div>
              <input
                aria-label={`So sánh ${pairLabel(leftIndex, rightIndex)}`}
                className="mt-3 w-full accent-emerald-700"
                max="8"
                min="-8"
                onChange={(event) => updateComparison(index, event.target.value)}
                step="1"
                type="range"
                value={value}
              />
              <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                <span>-8: ưu tiên {CRITERIA[leftIndex].label}</span>
                <span>0: ngang bằng</span>
                <span>+8: ưu tiên {CRITERIA[rightIndex].label}</span>
              </div>
            </fieldset>
          );
        })}

        {error && (
          <div
            aria-live="polite"
            className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700"
            role="alert"
          >
            {error}
          </div>
        )}

        <button
          className="w-full rounded-xl bg-emerald-700 px-5 py-3.5 font-bold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:opacity-60"
          disabled={loading}
          type="submit"
        >
          {loading ? "Đang phân tích..." : "Phân tích AHP"}
        </button>
      </form>

      {result && (
        <section className="mt-8" aria-live="polite">
          <div className="grid gap-3 sm:grid-cols-3">
            <Metric label="CR" value={result.cr} />
            <Metric label="CI" value={result.ci} />
            <Metric label="Lambda max" value={result.lambda_max} />
          </div>

          <h2 className="mt-6 text-lg font-bold text-slate-900">
            Trọng số tiêu chí
          </h2>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {CRITERIA.map(({ key, label }) => (
              <div
                className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2 text-sm"
                key={key}
              >
                <span>{label}</span>
                <strong className="text-emerald-700">
                  {formatNumber(result.weights?.[key])}
                </strong>
              </div>
            ))}
          </div>

          <h2 className="mt-6 text-lg font-bold text-slate-900">
            Xếp hạng giải pháp sinh học
          </h2>
          <div className="mt-3 space-y-2">
            {(result.ranking || []).map((solution) => (
              <div
                className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-slate-200 px-4 py-3"
                key={solution.id}
              >
                <span className="font-semibold text-slate-800">
                  #{solution.rank} {solution.name}
                </span>
                <strong className="text-emerald-700">
                  {formatNumber(solution.weighted_score)}
                </strong>
              </div>
            ))}
          </div>
        </section>
      )}
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="rounded-xl bg-emerald-50 p-3">
      <span className="block text-xs text-slate-500">{label}</span>
      <strong className="mt-1 block text-emerald-800">
        {formatNumber(value)}
      </strong>
    </div>
  );
}

function formatNumber(value) {
  return Number.isFinite(Number(value)) ? Number(value).toFixed(6) : "-";
}
