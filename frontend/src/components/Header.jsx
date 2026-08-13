import { BrainCircuit } from 'lucide-react'

export default function Header() {
  return (
    <header className="site-header">
      <div className="brand-mark"><BrainCircuit aria-hidden="true" /></div>
      <div>
        <h1>DataMind</h1>
        <p>AI-Powered Data Analytics Platform</p>
      </div>
    </header>
  )
}
