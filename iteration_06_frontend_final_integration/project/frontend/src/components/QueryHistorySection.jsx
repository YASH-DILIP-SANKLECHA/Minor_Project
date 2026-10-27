import React, { useState } from 'react';
import { History, Play, Trash2, Search, CheckCircle2, Clock } from 'lucide-react';

export default function QueryHistorySection({
  historyItems = [],
  onSelectHistoryItem,
  onClearHistory,
  activeHistoryId
}) {
  const [searchFilter, setSearchFilter] = useState('');

  const filteredItems = historyItems.filter((item) =>
    item.prompt.toLowerCase().includes(searchFilter.toLowerCase())
  );

  return (
    <section id="history" className="py-14 bg-slate-50 border-b border-slate-200/80">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-8">
        
        {/* Section Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <span className="text-xs font-mono font-bold tracking-widest text-slate-600 uppercase bg-slate-200 px-3 py-1 rounded-full">
              YOUR QUESTIONS
            </span>
            <h2 className="text-3xl font-black font-heading text-slate-950 mt-2 tracking-tight">
              QUESTION HISTORY
            </h2>
            <p className="text-xs font-medium text-slate-600 mt-1">
              Revisit earlier questions and their answers.
            </p>
          </div>

          {/* Action Bar */}
          <div className="flex items-center gap-3">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                placeholder="Filter queries..."
                className="pl-8 pr-3 py-1.5 rounded-lg border border-slate-300 text-xs font-sans text-slate-800 bg-white focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>

            {historyItems.length > 0 && (
              <button
                onClick={onClearHistory}
                className="neo-btn neo-btn-white neo-btn-sm text-xs font-bold"
              >
                <Trash2 className="w-3.5 h-3.5 text-rose-600" />
                <span>CLEAR</span>
              </button>
            )}
          </div>
        </div>

        {/* Query History Table / Timeline List (Specification 17) */}
        {filteredItems.length === 0 ? (
          <div className="saas-card p-8 text-center text-xs font-mono text-slate-500">
            No questions yet. Compare answers to see them here.
          </div>
        ) : (
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-150 border-b border-slate-200 text-[11px] font-mono font-bold text-slate-600 uppercase">
                    <th className="py-3 px-4">Question</th>
                    <th className="py-3 px-4">Timestamp</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs font-mono">
                  {filteredItems.map((item) => {
                    const isActive = activeHistoryId === item.id;
                    
                    return (
                      <tr
                        key={item.id}
                        className={`hover:bg-slate-50 transition-colors ${
                          isActive ? 'bg-purple-50/60' : ''
                        }`}
                      >
                        <td className="py-3.5 px-4 font-sans font-bold text-slate-900 max-w-md truncate">
                          "{item.prompt}"
                        </td>
                        <td className="py-3.5 px-4 text-slate-500 text-[11px]">
                          {item.timestamp || 'Just now'}
                        </td>
                        <td className="py-3.5 px-4">
                          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                            <span>Completed</span>
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right">
                          <button
                            onClick={() => onSelectHistoryItem(item)}
                            className="neo-btn neo-btn-purple neo-btn-sm text-xs font-bold"
                          >
                            <Play className="w-3 h-3" />
                            <span>REPLAY</span>
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

      </div>
    </section>
  );
}
