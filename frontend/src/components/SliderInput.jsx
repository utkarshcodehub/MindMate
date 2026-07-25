/**
 * SliderInput.jsx
 *
 * The signature component of this UI: large JetBrains Mono value
 * in amber beside the label, making the number feel like a reading
 * on a precise instrument rather than a form input.
 */

export default function SliderInput({
  label,
  id,
  min,
  max,
  step = 1,
  value,
  onChange,
  minLabel,
  maxLabel,
  formatValue,
}) {
  const display = formatValue ? formatValue(value) : String(value)

  return (
    <div className="slider-wrap">
      <div className="slider-header">
        <label className="slider-label" htmlFor={id}>{label}</label>
        <span className="slider-value">{display}</span>
      </div>

      <input
        type="range"
        id={id}
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
      />

      <div className="slider-anchors">
        <span className="slider-anchor">{minLabel}</span>
        <span className="slider-anchor">{maxLabel}</span>
      </div>
    </div>
  )
}