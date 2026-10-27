import React from 'react';
import DatasetReductionChart from '../charts/DatasetReductionChart';
import DatasetSizeChart from '../charts/TokenEfficiencyChart';
import ChangeBreakdownChart from '../charts/DuplicateAnalysisChart';
import { BarChart2, HardDrive, PieChart as PieIcon, CheckCircle2 } from 'lucide-react';

export default function AnalyticsDashboardSection({ stats }) {
  if (!stats) return <section id="analytics" className="py-16 bg-white border-y border-slate-200/80"><div className="max-w-7xl mx-auto px-4 sm:px-6 text-center"><span className="text-xs font-mono font-bold tracking-widest text-slate-500 uppercase">Results will appear after refinement</span><h2 className="text-3xl font-black font-heading text-slate-950 mt-3">YOUR DATASET RESULTS</h2></div></section>;

  const retained = stats.refinedInformationUnits;
  const removed = stats.removalsMade;
  const similar = stats.semanticDuplicatesRemoved;
  const conflicts = stats.contradictionsResolved;
  const unclassifiedRemovals = Math.max(0, removed - similar - conflicts);
  return <section id="analytics" className="py-16 bg-white border-y border-slate-200/80"><div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-10">
    <div className="text-center max-w-3xl mx-auto space-y-2"><span className="text-xs font-mono font-bold tracking-widest text-emerald-700 uppercase bg-emerald-50 px-3 py-1 rounded-full border border-emerald-100">RESULTS</span><h2 className="text-3xl sm:text-4xl font-black font-heading text-slate-950 tracking-tight">DATASET RESULTS</h2></div>
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <Metric label="Original lines" value={stats.originalRecords} />
      <Metric label="Refined lines" value={stats.optimizedRecords} accent="text-emerald-600" />
      <Metric label="Lines reduced" value={stats.originalRecords - stats.optimizedRecords} accent="text-purple-600" />
      <Metric label="Conflicts resolved" value={conflicts} accent="text-amber-600" />
    </div>
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <ChartCard icon={<BarChart2 className="w-5 h-5 text-blue-600" />} title="Line count"><DatasetReductionChart rawCount={stats.originalRecords} optimizedCount={stats.optimizedRecords} /></ChartCard>
      <ChartCard icon={<HardDrive className="w-5 h-5 text-amber-600" />} title="File size"><DatasetSizeChart originalBytes={stats.originalSizeBytes} refinedBytes={stats.optimizedSizeBytes} /></ChartCard>
      <ChartCard icon={<PieIcon className="w-5 h-5 text-purple-600" />} title="Statement changes"><ChangeBreakdownChart similarRemoved={similar} conflictsResolved={conflicts} otherRemoved={unclassifiedRemovals} retained={retained} /></ChartCard>
      <div className="saas-card p-6"><div className="flex items-center gap-2 pb-3 border-b border-slate-100 mb-4"><CheckCircle2 className="w-5 h-5 text-emerald-600" /><h3 className="font-heading font-extrabold text-base text-slate-900">Refinement summary</h3></div><dl className="space-y-4 text-sm"><Row label="Similar statements removed" value={similar} /><Row label="Conflicts resolved automatically" value={stats.contradictionsResolvedAutomatically} /><Row label="Manual choices applied" value={stats.contradictionsResolvedManually} /><Row label="Items retained" value={retained} /><Row label="Pairs needing review" value={stats.manualReview} /></dl></div>
    </div>
  </div></section>;
}
function Metric({ label, value, accent = 'text-slate-900' }) { return <div className="saas-card p-5 bg-slate-50 border-slate-200"><span className="text-xs font-mono text-slate-500 font-bold uppercase">{label}</span><div className={`text-3xl font-black font-heading mt-1 ${accent}`}>{value.toLocaleString()}</div></div>; }
function ChartCard({ icon, title, children }) { return <div className="saas-card p-6"><div className="flex items-center gap-2 pb-3 border-b border-slate-100 mb-4">{icon}<h3 className="font-heading font-extrabold text-base text-slate-900">{title}</h3></div>{children}</div>; }
function Row({ label, value }) { return <div className="flex items-center justify-between border-b border-slate-100 pb-3"><dt className="text-slate-600">{label}</dt><dd className="font-mono font-bold text-slate-900">{value.toLocaleString()}</dd></div>; }
