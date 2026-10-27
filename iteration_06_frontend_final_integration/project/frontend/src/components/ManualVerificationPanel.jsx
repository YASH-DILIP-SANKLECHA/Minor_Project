import React from 'react';
import { CheckCircle2, ClipboardCheck, X } from 'lucide-react';

export default function ManualVerificationPanel({ pairs, loading, resolvingCase, onResolve, onClose }) {
  if (!pairs) return null;
  const pair = pairs[0];
  return <section className="py-8 bg-slate-50 border-y border-slate-200">
    <div className="max-w-7xl mx-auto px-4 sm:px-6">
      <div className="saas-card p-6 sm:p-8">
        <div className="flex items-start justify-between gap-4 border-b border-slate-100 pb-5">
          <div><span className="text-xs font-mono font-bold tracking-widest text-amber-700 uppercase bg-amber-50 px-3 py-1 rounded-full border border-amber-200">Manual verification</span><h2 className="text-2xl font-black font-heading text-slate-950 mt-3">Choose the statement to retain</h2><p className="text-sm text-slate-600 mt-1">One contradiction pair is shown at a time. Selections are saved together; the final dataset is rebuilt once after the last pair is reviewed.</p></div>
          <button onClick={onClose} className="p-2 text-slate-500 hover:text-slate-900" aria-label="Close manual verification"><X className="w-5 h-5" /></button>
        </div>
        {loading ? <p className="py-8 text-sm text-slate-500">Loading statements for review…</p> : pairs.length === 0 ? <div className="py-8 text-center text-slate-600"><CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto mb-2" /><p>All manual verification pairs have been resolved.</p><p className="text-sm text-slate-500 mt-1">The final refined dataset now includes your selections.</p><div className="flex flex-wrap justify-center gap-3 mt-5"><a href="/api/datasets/refined" target="_blank" rel="noreferrer" className="neo-btn neo-btn-white neo-btn-sm text-xs font-bold">VIEW FINAL DATASET</a><a href="/api/datasets/refined/download" className="neo-btn neo-btn-primary neo-btn-sm text-xs font-bold">DOWNLOAD FINAL DATASET</a></div></div> : <div className="mt-6"><article key={pair.case_number} className="border border-slate-200 rounded-2xl overflow-hidden"><div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-3"><span className="flex items-center gap-2 text-xs font-mono font-bold text-slate-700 uppercase"><ClipboardCheck className="w-4 h-4 text-amber-600" />Review pair {pair.case_number}</span><span className="text-xs font-mono text-slate-500">{pairs.length} pairs pending</span></div><div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-slate-200"><Statement label="Statement 1" text={pair.text_a} action="KEEP_FIRST" pair={pair} resolvingCase={resolvingCase} onResolve={onResolve} /><Statement label="Statement 2" text={pair.text_b} action="KEEP_SECOND" pair={pair} resolvingCase={resolvingCase} onResolve={onResolve} /></div></article></div>}
      </div>
    </div>
  </section>;
}

function Statement({ label, text, action, pair, resolvingCase, onResolve }) {
  const saving = resolvingCase === pair.case_number;
  return <div className="bg-white p-5"><span className="text-xs font-mono font-bold uppercase tracking-wider text-slate-500">{label}</span><p className="mt-3 min-h-16 text-sm leading-6 text-slate-800">{text}</p><button disabled={resolvingCase !== null} onClick={() => onResolve(pair, action)} className="neo-btn neo-btn-primary neo-btn-sm text-xs font-bold mt-4 w-full justify-center">{saving ? 'SAVING…' : `SELECT ${label.toUpperCase()}`}</button></div>;
}
