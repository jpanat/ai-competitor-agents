import { useEffect, useState } from 'react'
import { CheckCircle, XCircle, Loader, DollarSign, MapPin, Home, Building2, FileText, Cpu } from 'lucide-react'

const AGENTS = [
  { id: 'financial', label: 'Financial Advisor', icon: DollarSign, color: 'green', desc: 'Calculating your budget and affordability' },
  { id: 'location', label: 'Location Researcher', icon: MapPin, color: 'blue', desc: 'Analyzing cities across 8 factors' },
  { id: 'homes', label: 'Home Search Agent', icon: Home, color: 'purple', desc: 'Finding matching homes in top city' },
  { id: 'sell', label: 'Sale Strategist', icon: Building2, color: 'orange', desc: 'Creating your home sale plan' },
  { id: 'summary', label: 'Report Generator', icon: FileText, color: 'indigo', desc: 'Synthesizing your personalized report' },
]

const COLOR_MAP = {
  green: { bg: 'bg-green-50', icon: 'text-green-600', ring: 'ring-green-200', badge: 'bg-green-100 text-green-700' },
  blue: { bg: 'bg-blue-50', icon: 'text-blue-600', ring: 'ring-blue-200', badge: 'bg-blue-100 text-blue-700' },
  purple: { bg: 'bg-purple-50', icon: 'text-purple-600', ring: 'ring-purple-200', badge: 'bg-purple-100 text-purple-700' },
  orange: { bg: 'bg-orange-50', icon: 'text-orange-600', ring: 'ring-orange-200', badge: 'bg-orange-100 text-orange-700' },
  indigo: { bg: 'bg-indigo-50', icon: 'text-indigo-600', ring: 'ring-indigo-200', badge: 'bg-indigo-100 text-indigo-700' },
}

function AgentCard({ agent, update }) {
  const colors = COLOR_MAP[agent.color]
  const Icon = agent.icon
  const status = update?.status

  return (
    <div className={`card transition-all duration-300 ${status === 'starting' || status === 'working' ? 'ring-2 ' + colors.ring : ''} ${!status ? 'opacity-60' : ''}`}>
      <div className="flex items-start gap-4">
        <div className={`w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 ${colors.bg}`}>
          <Icon className={`w-6 h-6 ${colors.icon}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h3 className="font-semibold text-gray-900">{agent.label}</h3>
            <StatusBadge status={status} colors={colors} />
          </div>
          {update?.message ? (
            <p className={`text-sm ${status === 'error' ? 'text-red-600' : 'text-gray-600'} ${status === 'working' || status === 'starting' ? 'thinking' : ''}`}>
              {update.message}
            </p>
          ) : (
            <p className="text-sm text-gray-400">{agent.desc}</p>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status, colors }) {
  if (!status) return <span className="text-xs text-gray-400 font-medium">Waiting</span>
  if (status === 'starting' || status === 'working') {
    return (
      <span className={`flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full ${colors.badge}`}>
        <Loader className="w-3 h-3 animate-spin" />
        Working
      </span>
    )
  }
  if (status === 'complete') {
    return (
      <span className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full bg-green-100 text-green-700">
        <CheckCircle className="w-3 h-3" />
        Done
      </span>
    )
  }
  if (status === 'error') {
    return (
      <span className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full bg-red-100 text-red-700">
        <XCircle className="w-3 h-3" />
        Error
      </span>
    )
  }
  return null
}

export default function AgentProgress({ updates, error, profile }) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const t = setInterval(() => setElapsed(e => e + 1), 1000)
    return () => clearInterval(t)
  }, [])

  const getUpdate = (agentId) => updates.find(u => u.agent === agentId)
  const completedCount = AGENTS.filter(a => getUpdate(a.id)?.status === 'complete').length

  const needsSell = profile?.has_current_home
  const visibleAgents = needsSell ? AGENTS : AGENTS.filter(a => a.id !== 'sell')

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <Cpu className="w-8 h-8 text-white animate-pulse" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">AI Agents at Work</h1>
        <p className="text-gray-500 mt-1">
          {completedCount}/{visibleAgents.length} agents complete
          <span className="text-gray-400 ml-2">· {Math.floor(elapsed/60)}:{String(elapsed%60).padStart(2,'0')}</span>
        </p>
      </div>

      {/* Progress bar */}
      <div className="mb-8">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>Analyzing your profile</span>
          <span>{Math.round(completedCount / visibleAgents.length * 100)}%</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-1000"
            style={{ width: `${Math.round(completedCount / visibleAgents.length * 100)}%` }}
          />
        </div>
      </div>

      {/* Agent cards */}
      <div className="space-y-3">
        {visibleAgents.map(agent => (
          <AgentCard key={agent.id} agent={agent} update={getUpdate(agent.id)} />
        ))}
      </div>

      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          <strong>Error:</strong> {error}
          <br />
          <span className="text-xs text-red-500">Make sure your ANTHROPIC_API_KEY is set and the backend is running.</span>
        </div>
      )}

      <div className="mt-6 text-center text-sm text-gray-400">
        Powered by Claude Opus with adaptive thinking · This may take 2-4 minutes
      </div>
    </div>
  )
}
