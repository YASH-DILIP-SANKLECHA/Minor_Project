import React from 'react';
import { Bot, Zap, Sparkles, Send, Activity, CheckCircle2, Clock, ShieldCheck } from 'lucide-react';

export default function ModelComparisonSection({
  prompt,
  setPrompt,
  rawAnswer,
  optimizedAnswer,
  comparison,
  onRunComparison,
  loading,
  isDisabled,
  suggestedPrompts = []
}) {
  const handleSubmit = (e) => {
    e.preventDefault();
    if (prompt && prompt.trim()) {
      onRunComparison(prompt);
    }
  };

  return (
    <section id="compare-models" className="py-16 bg-white border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-10">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-2">
          <span className="text-xs font-mono font-bold tracking-widest text-purple-700 uppercase bg-purple-50 px-3 py-1 rounded-full border border-purple-100">
            ANSWER COMPARISON
          </span>
          <h2 className="text-3xl sm:text-4xl font-black font-heading text-slate-950 tracking-tight">
            COMPARE YOUR ANSWERS
          </h2>
          <p className="text-sm font-medium text-slate-600">
            Ask the same question using your original dataset and your refined dataset.
          </p>
        </div>

        {/* Key Message Callout Banner (Specification 15) */}
        <div className="bg-gradient-to-r from-purple-900 via-indigo-900 to-slate-900 text-white rounded-2xl p-5 shadow-xl text-center border border-purple-700/50 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3 text-left">
            <div className="p-2.5 bg-yellow-400 text-slate-950 rounded-xl font-bold">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <span className="text-xs font-mono text-yellow-300 font-bold uppercase">DATASET ANSWERS</span>
              <h3 className="font-heading font-black text-lg text-white">
                Compare answers from both versions of your dataset.
              </h3>
            </div>
          </div>

          <div className="text-xs font-mono text-slate-300 bg-white/10 px-3.5 py-1.5 rounded-lg border border-white/10">
            Compare answers based on the information available in each dataset
          </div>
        </div>

        {/* Premium Query Console Input (Specification 16) */}
        <div className="saas-card p-6 bg-slate-50 space-y-4">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-mono font-bold text-slate-700 uppercase flex items-center gap-2">
                <Bot className="w-4 h-4 text-purple-600" />
                <span>YOUR QUESTION</span>
              </label>
              <span className="text-xs font-mono text-slate-400">
                The same question is asked using both datasets
              </span>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Ask a question about your dataset"
                disabled={isDisabled || loading}
                className="flex-1 px-4 py-3.5 rounded-xl border border-slate-300 font-sans text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-purple-500 shadow-sm"
              />

              {/* Action Button (Preserved Neo-Brutalist Style) */}
              <button
                type="submit"
                disabled={isDisabled || loading || !prompt.trim()}
                className="neo-btn neo-btn-purple neo-btn-md text-sm font-black px-6 py-3.5 shrink-0 shadow-[4px_4px_0_#111111]"
              >
                <Send className="w-4 h-4 text-[#111111]" />
                <span>{loading ? 'PREPARING ANSWERS...' : 'COMPARE ANSWERS'}</span>
              </button>
            </div>

            {/* Suggested Prompts */}
            {suggestedPrompts && suggestedPrompts.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
                <span className="font-mono text-slate-500 font-bold">Suggested:</span>
                {suggestedPrompts.map((p, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => {
                      setPrompt(p);
                      onRunComparison(p);
                    }}
                    className="bg-white border border-slate-200 text-slate-700 hover:text-purple-700 hover:border-purple-300 px-2.5 py-1 rounded-lg transition-colors font-medium text-[11px]"
                  >
                    "{p}"
                  </button>
                ))}
              </div>
            )}
          </form>

          {/* Processing Query Dispatch State */}
          {loading && (
            <div className="p-4 bg-purple-950 text-white rounded-xl border border-purple-800 space-y-2 text-xs font-mono animate-fadeIn">
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-3.5 rounded-full border-2 border-yellow-400 border-t-transparent animate-spin" />
                <span className="font-bold text-yellow-300">PREPARING YOUR ANSWERS...</span>
              </div>
              <div className="text-slate-300">
                Checking the original dataset and the refined dataset...
              </div>
            </div>
          )}
        </div>

        {/* Side-by-Side Model Responses Display */}
        {(rawAnswer || optimizedAnswer) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fadeIn">
            
            {/* MODEL 1: RAW DATASET INTELLIGENCE */}
            <div className="saas-card p-6 bg-white space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Bot className="w-5 h-5 text-slate-700" />
                  <h3 className="font-heading font-extrabold text-base text-slate-900">
                    ORIGINAL DATASET ANSWER
                  </h3>
                </div>
                <span className="text-[11px] font-mono font-bold text-slate-600 bg-slate-100 px-2 py-0.5 rounded">
                  Original data
                </span>
              </div>

              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-800 leading-relaxed min-h-[160px] whitespace-pre-wrap">
                {rawAnswer}
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-600 pt-2 border-t border-slate-100">
                <div>Relevant lines: <b>{comparison?.rawContextLines ?? '—'}</b></div>
                <div>Dataset: <b>Original</b></div>
              </div>
            </div>

            {/* MODEL 2: OPTIMIZED DATASET INTELLIGENCE */}
            <div className="saas-card p-6 bg-white space-y-4 border-emerald-200/80">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-emerald-600" />
                  <h3 className="font-heading font-extrabold text-base text-slate-900">
                    REFINED DATASET ANSWER
                  </h3>
                </div>
                <span className="text-[11px] font-mono font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  Refined data
                </span>
              </div>

              <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-200 text-xs font-mono text-slate-900 leading-relaxed min-h-[160px] whitespace-pre-wrap">
                {optimizedAnswer}
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-600 pt-2 border-t border-slate-100">
                <div>Relevant lines: <b className="text-emerald-600">{comparison?.optimizedContextLines ?? '—'}</b></div>
                <div>Dataset: <b className="text-emerald-600">Refined</b></div>
              </div>
            </div>

          </div>
        )}

      </div>
    </section>
  );
}
