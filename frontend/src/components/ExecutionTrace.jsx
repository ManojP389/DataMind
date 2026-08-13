import { ArrowRight, CheckCircle2 } from 'lucide-react'

const agentName = (agent) => agent.split('_').map((word) => word[0].toUpperCase() + word.slice(1)).join(' ')

export default function ExecutionTrace({ execution, eyebrow = 'Agent execution', title = 'Analysis workflow' }) {
  const agents = [...new Set((execution || []).map(({ agent }) => agent).filter(Boolean))]
  if (!agents.length) return null
  return <section><div className="section-heading"><span className="eyebrow">{eyebrow}</span><h2>{title}</h2></div><div className="trace">{agents.map((agent, index) => <div className="trace-item" key={agent}><div><CheckCircle2 size={17} />{agentName(agent)}</div>{index < agents.length - 1 && <ArrowRight className="trace-arrow" size={18} />}</div>)}</div></section>
}
