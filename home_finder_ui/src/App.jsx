import { useState } from 'react'
import { Home, ArrowRight, Sparkles } from 'lucide-react'
import WizardForm from './components/WizardForm.jsx'
import AgentProgress from './components/AgentProgress.jsx'
import Results from './components/Results.jsx'

const STEPS = { FORM: 'form', ANALYZING: 'analyzing', RESULTS: 'results' }

export default function App() {
  const [step, setStep] = useState(STEPS.FORM)
  const [profile, setProfile] = useState(null)
  const [agentUpdates, setAgentUpdates] = useState([])
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleSubmit(profileData) {
    setProfile(profileData)
    setStep(STEPS.ANALYZING)
    setAgentUpdates([])
    setError(null)

    try {
      const response = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData),
      })

      if (!response.ok) {
        const err = await response.json()
        throw new Error(err.detail || 'Analysis failed')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // keep incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          const payload = line.slice(6).trim()
          if (payload === '[DONE]') continue

          try {
            const update = JSON.parse(payload)
            setAgentUpdates(prev => {
              // Replace existing update for same agent+status or append
              const idx = prev.findIndex(u => u.agent === update.agent && u.status !== 'complete')
              if (idx !== -1) {
                const next = [...prev]
                next[idx] = update
                return next
              }
              return [...prev, update]
            })

            // Final result
            if (update.agent === 'orchestrator' && update.status === 'complete') {
              setResult(update.data.result)
              setTimeout(() => setStep(STEPS.RESULTS), 800)
            }

            if (update.status === 'error') {
              setError(update.message)
            }
          } catch (e) {
            // ignore parse errors
          }
        }
      }
    } catch (err) {
      setError(err.message)
    }
  }

  function handleReset() {
    setStep(STEPS.FORM)
    setProfile(null)
    setAgentUpdates([])
    setResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50">
      {/* Header */}
      <header className="sticky top-0 z-10 bg-white/80 backdrop-blur border-b border-gray-100">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center justify-between">
          <button onClick={handleReset} className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
              <Home className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-gray-900 text-lg">AI Home Finder</span>
          </button>
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Sparkles className="w-4 h-4 text-blue-500" />
            <span>Powered by Claude Opus</span>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {step === STEPS.FORM && (
          <WizardForm onSubmit={handleSubmit} />
        )}
        {step === STEPS.ANALYZING && (
          <AgentProgress updates={agentUpdates} error={error} profile={profile} />
        )}
        {step === STEPS.RESULTS && result && (
          <Results result={result} onReset={handleReset} />
        )}
      </main>
    </div>
  )
}
