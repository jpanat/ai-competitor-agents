import { useState } from 'react'
import {
  DollarSign, MapPin, Home, Users, Star, Calendar,
  Building2, ChevronLeft, ChevronRight, Plus, X, Check
} from 'lucide-react'

const STEPS = [
  { id: 'finances', label: 'Finances', icon: DollarSign },
  { id: 'current_home', label: 'Current Home', icon: Building2 },
  { id: 'destination', label: 'Destination', icon: MapPin },
  { id: 'priorities', label: 'Priorities', icon: Star },
  { id: 'family', label: 'Family & Home', icon: Users },
]

const DEFAULT_FORM = {
  // Finances
  annual_income: '',
  savings: '',
  credit_score: '',
  monthly_debts: '0',

  // Current home
  has_current_home: false,
  current_home_value: '',
  current_home_equity: '',
  current_home_location: '',

  // Destination
  target_move_date: '',
  destination_cities: [],
  _city_input: '',
  home_type_preference: 'either',

  // Priorities (1-5)
  school_priority: 3,
  commute_priority: 3,
  safety_priority: 3,
  walkability_priority: 3,
  restaurants_priority: 3,
  job_market_priority: 3,
  airport_priority: 3,
  growth_priority: 3,

  // Family
  num_adults: 2,
  num_children: 0,
  industry: '',
  min_bedrooms: 3,
  max_budget: '',
}

function PrioritySelector({ label, value, onChange }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-gray-700 flex-1">{label}</span>
      <div className="flex gap-1">
        {[1,2,3,4,5].map(n => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={`priority-btn ${
              n <= value
                ? 'bg-blue-600 border-blue-600 text-white'
                : 'border-gray-200 text-gray-400 hover:border-blue-300'
            }`}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  )
}

function FormInput({ label, type = 'text', value, onChange, placeholder, prefix, required }) {
  return (
    <div>
      <label className="label">{label}{required && <span className="text-red-500 ml-1">*</span>}</label>
      <div className="relative">
        {prefix && (
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 font-medium">{prefix}</span>
        )}
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          className={`input-field ${prefix ? 'pl-8' : ''}`}
          required={required}
        />
      </div>
    </div>
  )
}

export default function WizardForm({ onSubmit }) {
  const [currentStep, setCurrentStep] = useState(0)
  const [form, setForm] = useState(DEFAULT_FORM)
  const [submitting, setSubmitting] = useState(false)

  const set = (key, val) => setForm(f => ({ ...f, [key]: val }))

  function addCity() {
    const city = form._city_input.trim()
    if (city && !form.destination_cities.includes(city)) {
      set('destination_cities', [...form.destination_cities, city])
      set('_city_input', '')
    }
  }

  function removeCity(city) {
    set('destination_cities', form.destination_cities.filter(c => c !== city))
  }

  function canProceed() {
    switch (currentStep) {
      case 0: return form.annual_income && form.savings
      case 1: return true
      case 2: return form.target_move_date && form.destination_cities.length > 0
      case 3: return true
      case 4: return true
      default: return true
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSubmitting(true)

    const payload = {
      annual_income: parseFloat(form.annual_income),
      savings: parseFloat(form.savings),
      credit_score: form.credit_score ? parseInt(form.credit_score) : null,
      monthly_debts: parseFloat(form.monthly_debts || 0),
      has_current_home: form.has_current_home,
      current_home_value: form.has_current_home && form.current_home_value ? parseFloat(form.current_home_value) : null,
      current_home_equity: form.has_current_home && form.current_home_equity ? parseFloat(form.current_home_equity) : null,
      current_home_location: form.has_current_home ? form.current_home_location : null,
      target_move_date: form.target_move_date,
      destination_cities: form.destination_cities,
      home_type_preference: form.home_type_preference,
      school_priority: form.school_priority,
      commute_priority: form.commute_priority,
      safety_priority: form.safety_priority,
      walkability_priority: form.walkability_priority,
      restaurants_priority: form.restaurants_priority,
      job_market_priority: form.job_market_priority,
      airport_priority: form.airport_priority,
      growth_priority: form.growth_priority,
      num_adults: parseInt(form.num_adults),
      num_children: parseInt(form.num_children),
      industry: form.industry || null,
      min_bedrooms: parseInt(form.min_bedrooms),
      max_budget: form.max_budget ? parseFloat(form.max_budget) : null,
    }

    await onSubmit(payload)
    setSubmitting(false)
  }

  const stepContent = [
    // Step 0: Finances
    <div key="finances" className="space-y-4">
      <p className="text-gray-500 text-sm">Help us understand your budget so we can find the right homes.</p>
      <div className="grid grid-cols-2 gap-4">
        <FormInput label="Annual Household Income" type="number" prefix="$" value={form.annual_income}
          onChange={v => set('annual_income', v)} placeholder="120,000" required />
        <FormInput label="Available Savings" type="number" prefix="$" value={form.savings}
          onChange={v => set('savings', v)} placeholder="80,000" required />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <FormInput label="Credit Score (optional)" type="number" value={form.credit_score}
          onChange={v => set('credit_score', v)} placeholder="720" />
        <FormInput label="Monthly Debt Payments" type="number" prefix="$" value={form.monthly_debts}
          onChange={v => set('monthly_debts', v)} placeholder="500" />
      </div>
      <p className="text-xs text-gray-400">Monthly debts = car payments + student loans + other loans (not rent/mortgage)</p>
    </div>,

    // Step 1: Current Home
    <div key="current_home" className="space-y-4">
      <p className="text-gray-500 text-sm">Tell us about your current home so we can plan the sale timeline.</p>
      <div className="flex items-center gap-3 p-4 bg-blue-50 rounded-xl">
        <button
          type="button"
          onClick={() => set('has_current_home', !form.has_current_home)}
          className={`w-12 h-6 rounded-full transition-colors relative ${form.has_current_home ? 'bg-blue-600' : 'bg-gray-300'}`}
        >
          <span className={`absolute top-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${form.has_current_home ? 'translate-x-6' : 'translate-x-0.5'}`} />
        </button>
        <label className="font-medium text-gray-900">I own a home I need to sell</label>
      </div>

      {form.has_current_home && (
        <div className="space-y-4 p-4 bg-gray-50 rounded-xl">
          <div className="grid grid-cols-2 gap-4">
            <FormInput label="Current Home Value" type="number" prefix="$" value={form.current_home_value}
              onChange={v => set('current_home_value', v)} placeholder="450,000" />
            <FormInput label="Equity in Home" type="number" prefix="$" value={form.current_home_equity}
              onChange={v => set('current_home_equity', v)} placeholder="200,000" />
          </div>
          <FormInput label="Current City & State" value={form.current_home_location}
            onChange={v => set('current_home_location', v)} placeholder="e.g. Chicago, IL" />
        </div>
      )}

      {!form.has_current_home && (
        <div className="p-4 bg-green-50 rounded-xl text-sm text-green-700">
          <Check className="w-4 h-4 inline mr-1" />
          No home to sell - you can move quickly when you find the right place!
        </div>
      )}
    </div>,

    // Step 2: Destination
    <div key="destination" className="space-y-4">
      <p className="text-gray-500 text-sm">Where are you considering moving? Add multiple cities to compare.</p>

      <FormInput label="Target Move Date" type="text" value={form.target_move_date}
        onChange={v => set('target_move_date', v)} placeholder="e.g. June 2025" required />

      <div>
        <label className="label">Cities to Consider <span className="text-red-500">*</span></label>
        <div className="flex gap-2">
          <input
            type="text"
            value={form._city_input}
            onChange={e => set('_city_input', e.target.value)}
            onKeyDown={e => e.key === 'Enter' && (e.preventDefault(), addCity())}
            placeholder="e.g. Austin, TX"
            className="input-field flex-1"
          />
          <button type="button" onClick={addCity} className="btn-primary px-4 py-3">
            <Plus className="w-4 h-4" />
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">
          {form.destination_cities.map(city => (
            <span key={city} className="flex items-center gap-1 bg-blue-100 text-blue-700 px-3 py-1.5 rounded-full text-sm font-medium">
              <MapPin className="w-3 h-3" />
              {city}
              <button type="button" onClick={() => removeCity(city)} className="hover:text-blue-900 ml-1">
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
        {form.destination_cities.length === 0 && (
          <p className="text-xs text-gray-400 mt-1">Add at least one city. Add multiple to compare them.</p>
        )}
      </div>

      <div>
        <label className="label">Home Type Preference</label>
        <div className="grid grid-cols-3 gap-3">
          {[
            { val: 'new_build', label: '🏗️ New Build', desc: 'Brand new construction' },
            { val: 'existing', label: '🏘️ Existing', desc: 'Resale homes' },
            { val: 'either', label: '🏠 Either', desc: 'Show me both' },
          ].map(opt => (
            <button key={opt.val} type="button"
              onClick={() => set('home_type_preference', opt.val)}
              className={`p-3 rounded-xl border-2 text-left transition-all ${
                form.home_type_preference === opt.val
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
            >
              <div className="font-medium text-sm">{opt.label}</div>
              <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>,

    // Step 3: Priorities
    <div key="priorities" className="space-y-2">
      <p className="text-gray-500 text-sm">Rate how important each factor is for your decision (1 = low, 5 = critical).</p>
      <div className="divide-y divide-gray-100">
        <PrioritySelector label="🏫 School Quality" value={form.school_priority} onChange={v => set('school_priority', v)} />
        <PrioritySelector label="🚌 Commute & Transport" value={form.commute_priority} onChange={v => set('commute_priority', v)} />
        <PrioritySelector label="🔒 Safety / Low Crime" value={form.safety_priority} onChange={v => set('safety_priority', v)} />
        <PrioritySelector label="🚶 Walkability" value={form.walkability_priority} onChange={v => set('walkability_priority', v)} />
        <PrioritySelector label="🍽️ Restaurants & Food Scene" value={form.restaurants_priority} onChange={v => set('restaurants_priority', v)} />
        <PrioritySelector label="💼 Job Market" value={form.job_market_priority} onChange={v => set('job_market_priority', v)} />
        <PrioritySelector label="✈️ Airport Access" value={form.airport_priority} onChange={v => set('airport_priority', v)} />
        <PrioritySelector label="📈 City Growth & Appreciation" value={form.growth_priority} onChange={v => set('growth_priority', v)} />
      </div>
    </div>,

    // Step 4: Family & Home
    <div key="family" className="space-y-4">
      <p className="text-gray-500 text-sm">A few final details to personalize your home search.</p>
      <div className="grid grid-cols-3 gap-4">
        <div>
          <label className="label">Adults in Household</label>
          <select value={form.num_adults} onChange={e => set('num_adults', parseInt(e.target.value))} className="input-field">
            {[1,2,3,4].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Children</label>
          <select value={form.num_children} onChange={e => set('num_children', parseInt(e.target.value))} className="input-field">
            {[0,1,2,3,4,5].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Min Bedrooms</label>
          <select value={form.min_bedrooms} onChange={e => set('min_bedrooms', parseInt(e.target.value))} className="input-field">
            {[1,2,3,4,5,6].map(n => <option key={n} value={n}>{n}+ BR</option>)}
          </select>
        </div>
      </div>
      <FormInput label="Your Industry / Career Field" value={form.industry}
        onChange={v => set('industry', v)} placeholder="e.g. Software Engineering, Healthcare, Finance" />
      <FormInput label="Max Budget (optional - we'll calculate if blank)" type="number" prefix="$"
        value={form.max_budget} onChange={v => set('max_budget', v)} placeholder="650,000" />

      {/* Summary Card */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 rounded-2xl p-5 text-white">
        <h3 className="font-bold text-lg mb-3">Ready to find your home! 🏠</h3>
        <div className="grid grid-cols-2 gap-2 text-sm text-blue-100">
          <div>💰 Income: <span className="text-white font-medium">${parseInt(form.annual_income || 0).toLocaleString()}/yr</span></div>
          <div>💵 Savings: <span className="text-white font-medium">${parseInt(form.savings || 0).toLocaleString()}</span></div>
          <div>📍 Cities: <span className="text-white font-medium">{form.destination_cities.length} cities</span></div>
          <div>🗓️ Move: <span className="text-white font-medium">{form.target_move_date || 'TBD'}</span></div>
          <div>🏡 Type: <span className="text-white font-medium capitalize">{form.home_type_preference.replace('_', ' ')}</span></div>
          <div>🛏️ Min: <span className="text-white font-medium">{form.min_bedrooms}+ bedrooms</span></div>
        </div>
      </div>
    </div>,
  ]

  return (
    <div className="max-w-2xl mx-auto">
      {/* Hero */}
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-3">Find Your Perfect Home</h1>
        <p className="text-lg text-gray-500">
          Our AI agents research cities, analyze homes, and create a personalized plan — just for you.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center justify-center mb-8 gap-0">
        {STEPS.map((s, i) => {
          const Icon = s.icon
          const active = i === currentStep
          const done = i < currentStep
          return (
            <div key={s.id} className="flex items-center">
              <div className={`flex flex-col items-center gap-1`}>
                <div className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                  done ? 'bg-blue-600 text-white' :
                  active ? 'bg-blue-600 text-white ring-4 ring-blue-100' :
                  'bg-gray-100 text-gray-400'
                }`}>
                  {done ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
                </div>
                <span className={`text-xs font-medium hidden sm:block ${active ? 'text-blue-600' : 'text-gray-400'}`}>
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`w-8 sm:w-16 h-0.5 mx-1 mb-4 transition-colors ${i < currentStep ? 'bg-blue-600' : 'bg-gray-200'}`} />
              )}
            </div>
          )
        })}
      </div>

      {/* Form card */}
      <form onSubmit={handleSubmit}>
        <div className="card mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-1">{STEPS[currentStep].label}</h2>
          <div className="mt-4">
            {stepContent[currentStep]}
          </div>
        </div>

        {/* Navigation */}
        <div className="flex justify-between">
          <button
            type="button"
            onClick={() => setCurrentStep(s => s - 1)}
            className={`btn-secondary flex items-center gap-2 ${currentStep === 0 ? 'invisible' : ''}`}
          >
            <ChevronLeft className="w-4 h-4" /> Back
          </button>

          {currentStep < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={() => setCurrentStep(s => s + 1)}
              disabled={!canProceed()}
              className="btn-primary flex items-center gap-2"
            >
              Continue <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={submitting || !form.annual_income || !form.savings || form.destination_cities.length === 0}
              className="btn-primary flex items-center gap-2"
            >
              {submitting ? 'Starting Analysis...' : 'Find My Home'} ✨
            </button>
          )}
        </div>
      </form>
    </div>
  )
}
