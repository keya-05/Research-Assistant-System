import { useState, useRef } from 'react'
import './App.css'

const EXAMPLES = [
  'Impact of AI on healthcare',
  'Future of quantum computing',
  'Climate change and food security',
  'How does blockchain work?',
]

function ConfidenceBadge({ level }) {
  const map = { high: 'High Confidence', medium: 'Medium Confidence', low: 'Low Confidence' }
  return <span className={`badge badge-${level}`}>{map[level] ?? 'Medium Confidence'}</span>
}

function ResultCard({ result }) {
  return (
    <div className="result-card">
      <div className="result-header">
        <ConfidenceBadge level={result.confidence} />
        {result.cached && <span className="cached-tag">● cached</span>}
      </div>
      <div className="answer-body">
        {result.answer.split('\n').map((p, i) => p.trim() ? <p key={i}>{p}</p> : <br key={i} />)}
      </div>
      {result.sources?.length > 0 && (
        <div className="sources-block">
          <p className="sources-title">References</p>
          <ol className="sources-list">
            {result.sources.map((src, i) => (
              <li key={i}>
                <span className="src-num">[{i+1}]</span>
                <a href={src} target="_blank" rel="noopener noreferrer">{src}</a>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

function Loading() {
  return (
    <div className="loading-wrap">
      <div className="loader-bar"><div className="loader-bar-inner" /></div>
      <div className="loading-steps">
        <div className="step step-1">⬡ Gathering research…</div>
        <div className="step step-2">⬡ Building answer…</div>
        <div className="step step-3">⬡ Evaluating confidence…</div>
      </div>
    </div>
  )
}

export default function App() {
  const [question, setQuestion] = useState('')
  const [loading, setLoading]   = useState(false)
  const [result, setResult]     = useState(null)
  const [error, setError]       = useState(null)
  const ref = useRef(null)

  const submit = async (q) => {
    const query = (q ?? question).trim()
    if (!query || loading) return
    setLoading(true); setResult(null); setError(null)

    try {
      const res = await fetch('/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: query }),
      })
      if (!res.ok) {
        const e = await res.json().catch(() => ({}))
        throw new Error(e.detail || `Error ${res.status}`)
      }
      setResult(await res.json())
    } catch (e) {
      setError(e.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="logo">
          <div className="logo-mark">◈</div>
          <div className="logo-text">Research<span>Assistant</span></div>
        </div>
        <p className="tagline">// multi-agent AI research system</p>
        <div className="pipeline">
          <span className="dot" /> Query
          <span className="sep">→</span> Research
          <span className="sep">→</span> Answer
          <span className="sep">→</span> Confidence
          <span className="dot" />
        </div>
      </header>

      <main style={{display:'flex',flexDirection:'column',gap:'2rem'}}>
        <section className="query-section">
          <label className="query-label" htmlFor="q">Ask a research question</label>
          <div className="textarea-wrap">
            <textarea
              id="q" ref={ref} rows={4} className="query-input"
              placeholder="e.g. What is the impact of AI on healthcare?"
              value={question} disabled={loading}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit() }}
            />
          </div>
          <div className="actions-row">
            <button className="btn-submit" onClick={() => submit()} disabled={loading || !question.trim()}>
              {loading ? 'Researching…' : 'Run Research'}
            </button>
            <span className="hint">Ctrl + Enter</span>
          </div>
        </section>

        {!result && !loading && (
          <section className="examples-section">
            <p className="examples-label">Try an example</p>
            <div className="examples-grid">
              {EXAMPLES.map(ex => (
                <button key={ex} className="example-chip"
                  onClick={() => { setQuestion(ex); ref.current?.focus() }}>
                  {ex}
                </button>
              ))}
            </div>
          </section>
        )}

        {loading && <Loading />}

        {error && (
          <div className="error-card" role="alert">
            <span className="error-icon">⚠</span>
            <div><strong>Error</strong><p>{error}</p></div>
            <button className="error-dismiss" onClick={() => setError(null)}>✕</button>
          </div>
        )}

        {result && <ResultCard result={result} />}
      </main>

      <footer className="footer">research-assistant · fastapi + react + postgresql</footer>
    </div>
  )
}