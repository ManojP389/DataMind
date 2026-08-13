import { Lightbulb } from 'lucide-react'

const label = (key) => key.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())

export default function Insights({ insights }) {
  const patterns = insights?.potentially_important_patterns || []
  const highlights = Object.entries(insights || {}).filter(([key, value]) => key !== 'potentially_important_patterns' && value)
  return <section className="insights-card"><div className="section-heading"><span className="eyebrow">EDA insights</span><h2>What DataMind found</h2></div><div className="insight-list">{patterns.map((pattern) => <p key={pattern}><Lightbulb size={17} />{pattern}</p>)}{highlights.map(([key, value]) => <p key={key}><strong>{label(key)}:</strong> {typeof value === 'object' ? JSON.stringify(value) : String(value)}</p>)}</div></section>
}
