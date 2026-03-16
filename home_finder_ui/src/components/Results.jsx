import { useState } from 'react'
import {
  Home, MapPin, DollarSign, Star, TrendingUp, Shield, Train, Utensils,
  Plane, GraduationCap, CheckCircle, AlertCircle, ArrowRight, ChevronDown,
  ChevronUp, Building2, Calendar, RotateCcw, Award, Bed, Bath, Square
} from 'lucide-react'

// ─── Score Ring ───────────────────────────────────────────────────────────────
function ScoreRing({ score, size = 64 }) {
  const radius = (size - 8) / 2
  const circ = 2 * Math.PI * radius
  const fill = (score / 10) * circ
  const color = score >= 7.5 ? '#22c55e' : score >= 5 ? '#f59e0b' : '#ef4444'

  return (
    <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="#e5e7eb" strokeWidth={6} />
      <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke={color} strokeWidth={6}
        strokeDasharray={`${fill} ${circ}`} strokeLinecap="round" />
      <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle"
        style={{ transform: 'rotate(90deg)', transformOrigin: '50% 50%', fontSize: '13px', fontWeight: 700, fill: color }}>
        {score.toFixed(1)}
      </text>
    </svg>
  )
}

// ─── Metric Row ───────────────────────────────────────────────────────────────
function MetricRow({ icon: Icon, label, score, color }) {
  const pct = (score / 10) * 100
  const barColor = score >= 7 ? 'bg-green-500' : score >= 5 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div className="flex items-center gap-3">
      <Icon className={`w-4 h-4 flex-shrink-0 ${color}`} />
      <span className="text-sm text-gray-600 w-32 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className={`h-2 rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-bold text-gray-700 w-6">{score.toFixed(1)}</span>
    </div>
  )
}

// ─── City Card ────────────────────────────────────────────────────────────────
function CityCard({ city, rank, isTop }) {
  const [expanded, setExpanded] = useState(rank === 1)

  return (
    <div className={`card overflow-hidden ${isTop ? 'ring-2 ring-blue-500' : ''}`}>
      {isTop && (
        <div className="flex items-center gap-2 bg-blue-600 text-white px-4 py-2 -mx-6 -mt-6 mb-4 text-sm font-semibold">
          <Award className="w-4 h-4" />
          #1 Recommended City
        </div>
      )}
      <div className="flex items-start gap-4">
        <ScoreRing score={city.overall_score} />
        <div className="flex-1">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-bold text-gray-900">{city.city}, {city.state}</h3>
              <p className="text-sm text-gray-500 mt-0.5">{city.summary}</p>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">Median Price</div>
              <div className="font-bold text-gray-900">${(city.median_home_price/1000).toFixed(0)}k</div>
            </div>
          </div>
        </div>
      </div>

      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-blue-600 text-sm font-medium mt-3 hover:text-blue-800"
      >
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        {expanded ? 'Less detail' : 'Full breakdown'}
      </button>

      {expanded && (
        <div className="mt-4 space-y-4">
          <div className="space-y-2">
            <MetricRow icon={GraduationCap} label="Schools" score={city.school_score} color="text-blue-500" />
            <MetricRow icon={Shield} label="Safety" score={city.crime_score} color="text-green-500" />
            <MetricRow icon={Home} label="Walkability" score={city.walkability_score} color="text-purple-500" />
            <MetricRow icon={Train} label="Transport" score={city.transport_score} color="text-orange-500" />
            <MetricRow icon={Building2} label="Job Market" score={city.job_market_score} color="text-indigo-500" />
            <MetricRow icon={Utensils} label="Restaurants" score={city.restaurant_score} color="text-red-500" />
            <MetricRow icon={Plane} label="Airport" score={city.airport_score} color="text-sky-500" />
            <MetricRow icon={TrendingUp} label="Growth" score={city.growth_score} color="text-emerald-500" />
            <MetricRow icon={DollarSign} label="Affordability" score={city.affordability_score} color="text-yellow-500" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <h4 className="font-semibold text-green-700 text-sm mb-2 flex items-center gap-1">
                <CheckCircle className="w-3.5 h-3.5" /> Pros
              </h4>
              <ul className="space-y-1">
                {city.pros.map((p, i) => (
                  <li key={i} className="text-xs text-gray-600 flex gap-2">
                    <span className="text-green-400 mt-0.5 flex-shrink-0">•</span>{p}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="font-semibold text-red-600 text-sm mb-2 flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" /> Cons
              </h4>
              <ul className="space-y-1">
                {city.cons.map((c, i) => (
                  <li key={i} className="text-xs text-gray-600 flex gap-2">
                    <span className="text-red-400 mt-0.5 flex-shrink-0">•</span>{c}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {city.neighborhoods.length > 0 && (
            <div>
              <h4 className="font-semibold text-gray-700 text-sm mb-2">Top Neighborhoods</h4>
              <div className="flex flex-wrap gap-2">
                {city.neighborhoods.map(n => (
                  <span key={n} className="bg-gray-100 text-gray-600 px-2 py-1 rounded-lg text-xs">{n}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Home Listing Card ────────────────────────────────────────────────────────
function HomeCard({ home, isTop }) {
  return (
    <div className={`card relative ${isTop ? 'ring-2 ring-green-500' : ''}`}>
      {isTop && (
        <div className="absolute top-3 right-3 bg-green-500 text-white text-xs font-bold px-2 py-1 rounded-full flex items-center gap-1">
          <Star className="w-3 h-3" /> Best Match
        </div>
      )}
      <div className="flex justify-between items-start mb-3">
        <div>
          <h3 className="font-bold text-gray-900">{home.address}</h3>
          <p className="text-sm text-gray-500">{home.city}</p>
        </div>
        <div className="text-right">
          <div className="text-xl font-bold text-blue-600">${(home.price/1000).toFixed(0)}k</div>
          <div className="text-xs text-gray-400">{home.home_type?.replace(/_/g, ' ')}</div>
        </div>
      </div>
      <div className="flex gap-4 text-sm text-gray-600 mb-3">
        <span className="flex items-center gap-1"><Bed className="w-4 h-4" />{home.bedrooms} bd</span>
        <span className="flex items-center gap-1"><Bath className="w-4 h-4" />{home.bathrooms} ba</span>
        <span className="flex items-center gap-1"><Square className="w-4 h-4" />{home.sqft?.toLocaleString()} sqft</span>
        {home.year_built && <span className="text-gray-400">Built {home.year_built}</span>}
      </div>
      <p className="text-sm text-gray-600 line-clamp-3">{home.description}</p>
      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-1">
          <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
          <span className="text-sm font-medium text-gray-700">{home.match_score.toFixed(1)}/10 match</span>
        </div>
        {home.zillow_url && (
          <a href={home.zillow_url} target="_blank" rel="noopener noreferrer"
            className="text-sm text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1">
            View on Zillow <ArrowRight className="w-3 h-3" />
          </a>
        )}
      </div>
    </div>
  )
}

// ─── Financial Summary ────────────────────────────────────────────────────────
function FinancialSummary({ fin }) {
  const ratingColor = {
    comfortable: 'text-green-600 bg-green-50',
    stretched: 'text-amber-600 bg-amber-50',
    aggressive: 'text-red-600 bg-red-50',
  }[fin.affordability_rating] || 'text-gray-600 bg-gray-50'

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <DollarSign className="w-5 h-5 text-green-600" /> Financial Analysis
        <span className={`ml-2 text-sm font-semibold px-3 py-1 rounded-full capitalize ${ratingColor}`}>
          {fin.affordability_rating}
        </span>
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
        {[
          { label: 'Rec. Budget', value: `$${(fin.recommended_price_range_min/1000).toFixed(0)}k–$${(fin.recommended_price_range_max/1000).toFixed(0)}k` },
          { label: 'Max Affordable', value: `$${(fin.max_affordable_price/1000).toFixed(0)}k` },
          { label: 'Monthly Payment', value: `$${fin.estimated_monthly_payment.toLocaleString()}/mo` },
          { label: 'Down Payment', value: `$${(fin.estimated_down_payment/1000).toFixed(0)}k` },
        ].map(item => (
          <div key={item.label} className="bg-gray-50 rounded-xl p-3 text-center">
            <div className="text-xs text-gray-500 mb-1">{item.label}</div>
            <div className="font-bold text-gray-900">{item.value}</div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div className="text-sm text-gray-600">
          <span className="font-medium">Closing Costs:</span> ~${(fin.estimated_closing_costs/1000).toFixed(0)}k
        </div>
        <div className="text-sm text-gray-600">
          <span className="font-medium">DTI Ratio:</span> {(fin.dti_ratio * 100).toFixed(0)}%
        </div>
      </div>
      <ul className="mt-3 space-y-1">
        {fin.notes.map((note, i) => (
          <li key={i} className="text-sm text-gray-600 flex gap-2">
            <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0 mt-0.5" />
            {note}
          </li>
        ))}
      </ul>
    </div>
  )
}

// ─── Sale Timeline ────────────────────────────────────────────────────────────
function SaleTimeline({ timeline }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Building2 className="w-5 h-5 text-orange-600" /> Home Sale Plan
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-4">
        <div className="bg-orange-50 rounded-xl p-3 text-center">
          <div className="text-xs text-orange-600 mb-1">List By</div>
          <div className="font-bold text-gray-900">{timeline.recommended_list_date}</div>
        </div>
        <div className="bg-orange-50 rounded-xl p-3 text-center">
          <div className="text-xs text-orange-600 mb-1">Est. Close</div>
          <div className="font-bold text-gray-900">{timeline.estimated_sale_date}</div>
        </div>
        <div className="bg-green-50 rounded-xl p-3 text-center col-span-2 sm:col-span-1">
          <div className="text-xs text-green-600 mb-1">Net Proceeds</div>
          <div className="font-bold text-green-700">${(timeline.estimated_net_proceeds/1000).toFixed(0)}k</div>
        </div>
      </div>

      <p className="text-sm text-gray-600 mb-3">{timeline.pricing_strategy}</p>

      <button onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-orange-600 text-sm font-medium hover:text-orange-800">
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        {expanded ? 'Hide' : 'Show'} full timeline
      </button>

      {expanded && (
        <div className="mt-4 space-y-3">
          <h4 className="font-semibold text-gray-700">Timeline</h4>
          {timeline.timeline_steps.map((step, i) => (
            <div key={i} className="flex gap-3">
              <div className="flex flex-col items-center">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${step.action_required ? 'bg-orange-500' : 'bg-gray-300'}`}>
                  <span className="text-white text-xs font-bold">{i+1}</span>
                </div>
                {i < timeline.timeline_steps.length - 1 && <div className="w-0.5 bg-gray-200 flex-1 my-1" />}
              </div>
              <div className="pb-3">
                <div className="text-xs text-gray-400">{step.date}</div>
                <div className="font-semibold text-sm text-gray-900">{step.milestone}</div>
                <div className="text-sm text-gray-600">{step.description}</div>
                {step.action_required && (
                  <span className="text-xs bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full font-medium">Action Required</span>
                )}
              </div>
            </div>
          ))}

          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Preparation Checklist</h4>
            <ul className="space-y-1">
              {timeline.preparation_tasks.map((task, i) => (
                <li key={i} className="text-sm text-gray-600 flex gap-2">
                  <Calendar className="w-4 h-4 text-orange-400 flex-shrink-0 mt-0.5" />
                  {task}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-red-600 mb-2">Key Risks</h4>
            <ul className="space-y-1">
              {timeline.key_risks.map((risk, i) => (
                <li key={i} className="text-sm text-gray-600 flex gap-2">
                  <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                  {risk}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Main Results ─────────────────────────────────────────────────────────────
export default function Results({ result, onReset }) {
  const [activeTab, setActiveTab] = useState('overview')

  const tabs = [
    { id: 'overview', label: '📋 Overview' },
    { id: 'cities', label: `🗺️ Cities (${result.city_analyses.length})` },
    { id: 'homes', label: `🏠 Homes (${result.home_listings.length})` },
    ...(result.sale_timeline ? [{ id: 'sell', label: '🏷️ Sale Plan' }] : []),
  ]

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Your Home Finder Report</h1>
          <p className="text-gray-500 mt-1">
            Top pick: <span className="font-semibold text-blue-600">{result.recommended_city}</span>
          </p>
        </div>
        <button onClick={onReset} className="btn-secondary flex items-center gap-2 text-sm">
          <RotateCcw className="w-4 h-4" /> New Search
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {tabs.map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-xl text-sm font-medium whitespace-nowrap transition-colors ${
              activeTab === tab.id ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Overview Tab */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Executive Summary */}
          <div className="card bg-gradient-to-br from-blue-600 to-indigo-700 text-white">
            <h2 className="text-xl font-bold mb-3">Executive Summary</h2>
            <div className="text-blue-100 text-sm leading-relaxed whitespace-pre-line">
              {result.executive_summary}
            </div>
          </div>

          <FinancialSummary fin={result.financial_analysis} />

          {/* Top city preview */}
          {result.city_analyses[0] && (
            <CityCard city={result.city_analyses[0]} rank={1} isTop={true} />
          )}

          {/* Next Steps */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
              <ArrowRight className="w-5 h-5 text-blue-600" /> Your Next Steps
            </h2>
            <ol className="space-y-3">
              {result.next_steps.map((step, i) => (
                <li key={i} className="flex gap-3">
                  <span className="w-7 h-7 bg-blue-100 text-blue-700 rounded-full flex items-center justify-center flex-shrink-0 font-bold text-sm">
                    {i+1}
                  </span>
                  <span className="text-gray-700 text-sm pt-1">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {/* Cities Tab */}
      {activeTab === 'cities' && (
        <div className="space-y-4">
          {result.city_analyses.map((city, i) => (
            <CityCard key={city.city} city={city} rank={i+1} isTop={i===0} />
          ))}
        </div>
      )}

      {/* Homes Tab */}
      {activeTab === 'homes' && (
        <div className="space-y-4">
          <FinancialSummary fin={result.financial_analysis} />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {result.home_listings.map((home, i) => (
              <HomeCard key={i} home={home} isTop={i===0} />
            ))}
          </div>
        </div>
      )}

      {/* Sell Tab */}
      {activeTab === 'sell' && result.sale_timeline && (
        <div className="space-y-4">
          <SaleTimeline timeline={result.sale_timeline} />
        </div>
      )}
    </div>
  )
}
