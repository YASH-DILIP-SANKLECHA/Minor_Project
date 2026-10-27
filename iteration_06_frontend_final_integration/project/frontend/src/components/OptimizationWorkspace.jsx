import React, { useState } from 'react';
import { 
  Upload, 
  FileText, 
  Sparkles, 
  Zap, 
  Check, 
  RotateCcw, 
  Database, 
  Layers, 
  AlertCircle,
  FileCheck,
  BarChart2
} from 'lucide-react';
import { analyzeDatasetText } from '../utils/fileReader';

export default function OptimizationWorkspace({
  rawText,
  setRawText,
  rawFile,
  setRawFile,
  onRunOptimization,
  isProcessing,
  refinementStatus,
  resultsReady,
  processingStage,
  progressPercentage,
  stagesList,
  error,
  onError,
  manualReviewCount,
  onOpenManualVerification,
  manualLoading
}) {
  const [inputTab, setInputTab] = useState('upload');
  const [dragActive, setDragActive] = useState(false);

  // Compute live dataset text metadata
  const textAnalysis = analyzeDatasetText(rawText);

  // Handle Drag & Drop
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    if (!file.name.endsWith('.txt') && file.type !== 'text/plain') {
      if (onError) onError('Invalid file format. Please upload a standard .TXT dataset file.');
      return;
    }
    setRawFile(file);
    const reader = new FileReader();
    reader.onload = (evt) => {
      setRawText(evt.target.result || '');
    };
    reader.readAsText(file);
  };

  return (
    <section id="upload" className="py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 space-y-8">
        
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto space-y-2">
          <span className="text-xs font-mono font-bold tracking-widest text-purple-700 uppercase bg-purple-50 px-3 py-1 rounded-full border border-purple-100">
            DATASET INPUT
          </span>
          <h2 className="text-3xl sm:text-4xl font-black font-heading text-slate-950 tracking-tight">
            REFINE YOUR DATASET
          </h2>
          <p className="text-sm font-medium text-slate-600">
            Upload a text file or paste your dataset. We will prepare a refined version and a clear results report.
          </p>
        </div>

        {/* Input Option Selector Tabs */}
        <div className="flex items-center justify-center gap-2 max-w-md mx-auto bg-slate-200/60 p-1 rounded-xl border border-slate-300/40">
          <button
            onClick={() => setInputTab('upload')}
            disabled={isProcessing}
            className={`flex-1 py-2 text-xs font-heading font-extrabold rounded-lg transition-all flex items-center justify-center gap-2 ${
              inputTab === 'upload' ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload File</span>
          </button>

          <button
            onClick={() => setInputTab('paste')}
            disabled={isProcessing}
            className={`flex-1 py-2 text-xs font-heading font-extrabold rounded-lg transition-all flex items-center justify-center gap-2 ${
              inputTab === 'paste' ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Paste Text</span>
          </button>

        </div>

        {/* Tab 1: Upload File Drag & Drop */}
        {inputTab === 'upload' && (
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`saas-card p-8 text-center transition-all border-2 border-dashed ${
              dragActive ? 'border-purple-500 bg-purple-50/50' : 'border-slate-300 bg-white hover:border-slate-400'
            }`}
          >
            <div className="max-w-md mx-auto space-y-4">
              <div className="w-14 h-14 mx-auto rounded-2xl bg-purple-50 border border-purple-200 text-purple-600 flex items-center justify-center shadow-sm">
                <Upload className="w-7 h-7" />
              </div>

              <div>
                <h3 className="font-heading font-extrabold text-base text-slate-900">
                  {rawFile ? rawFile.name : 'Drag & drop your .TXT dataset here'}
                </h3>
                <p className="text-xs font-medium text-slate-500 mt-1">
                  Choose a plain-text dataset up to 50 MB.
                </p>
              </div>

              <div className="flex items-center justify-center gap-3">
                <label className="neo-btn neo-btn-white neo-btn-sm text-xs font-bold cursor-pointer">
                  <span>SELECT FILE</span>
                  <input
                    type="file"
                    accept=".txt,text/plain"
                    onChange={handleFileInputChange}
                    disabled={isProcessing}
                    className="hidden"
                  />
                </label>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Paste Raw Text */}
        {inputTab === 'paste' && (
          <div className="saas-card p-4 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-bold text-slate-600">
                PASTE YOUR DATASET
              </span>
              <span className="text-xs font-mono text-slate-400">
                {textAnalysis.lineCount} lines • {textAnalysis.formattedSize}
              </span>
            </div>

            <textarea
              rows={8}
              value={rawText}
              onChange={(e) => setRawText(e.target.value)}
              disabled={isProcessing}
              placeholder="Paste your dataset here..."
              className="w-full p-4 rounded-xl border border-slate-200 font-mono text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-500 bg-slate-50/50"
            />
          </div>
        )}


        {/* Active Dataset Metadata Badges */}
        {rawText && rawText.trim() && (
          <div className="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm space-y-4 animate-fadeIn">
            
            {/* Badges Bar */}
            <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <FileCheck className="w-5 h-5 text-emerald-600" />
                <div>
                  <h4 className="font-heading font-extrabold text-sm text-slate-900">
                    DATASET READY
                  </h4>
                  <p className="text-xs text-slate-500 font-mono">
                    {rawFile ? rawFile.name : 'pasted_dataset.txt'}
                  </p>
                </div>
              </div>

              {/* Metadata Badges Grid */}
              <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
                <span className="bg-slate-100 text-slate-700 px-3 py-1 rounded-lg border border-slate-200">
                  Size: <b>{textAnalysis.formattedSize}</b>
                </span>
                <span className="bg-slate-100 text-slate-700 px-3 py-1 rounded-lg border border-slate-200">
                  Chars: <b>{textAnalysis.charCount.toLocaleString()}</b>
                </span>
                <span className="bg-slate-100 text-slate-700 px-3 py-1 rounded-lg border border-slate-200">
                  Words: <b>{textAnalysis.wordCount.toLocaleString()}</b>
                </span>
                <span className="bg-slate-100 text-slate-700 px-3 py-1 rounded-lg border border-slate-200">
                  Sentences: <b>{textAnalysis.sentenceCount.toLocaleString()}</b>
                </span>
                <span className="bg-purple-50 text-purple-700 px-3 py-1 rounded-lg border border-purple-200 font-bold">
                  Lines: <b>{textAnalysis.lineCount.toLocaleString()}</b>
                </span>
              </div>
            </div>

            {/* Main Primary Trigger Button (Preserved Neo-Brutalist Style) */}
            <div className="text-center py-2">
              <button
                onClick={onRunOptimization}
                disabled={isProcessing}
                className="neo-btn neo-btn-purple neo-btn-lg text-lg font-black px-10 py-4 shadow-[8px_8px_0_#111111]"
              >
                <Zap className="w-6 h-6 text-[#111111]" />
                <span>{isProcessing ? 'REFINING DATASET...' : 'REFINE DATASET'}</span>
                <Sparkles className="w-5 h-5 text-[#111111]" />
              </button>
            </div>

          </div>
        )}

        {refinementStatus.state !== 'idle' && (
          <div className={`text-white rounded-2xl p-6 shadow-xl space-y-5 animate-fadeIn border ${
            refinementStatus.state === 'complete' ? 'bg-emerald-950 border-emerald-700' : refinementStatus.state === 'failed' ? 'bg-rose-950 border-rose-700' : 'bg-slate-900 border-slate-800'
          }`}>
            
            {/* Stage Progress Header */}
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
              <div>
                <span className="text-xs font-mono font-bold text-yellow-400 tracking-wider uppercase">
                  DATASET STATUS
                </span>
                <h3 className="font-heading font-black text-xl text-white mt-0.5">
                  {refinementStatus.state === 'complete' ? 'Your refined dataset is ready' : refinementStatus.state === 'failed' ? 'Refinement could not be completed' : 'Refining your dataset'}
                </h3>
              </div>

              {/* Progress Percentage Badge */}
              <div className="text-right">
                <span className={`text-sm font-black font-heading ${refinementStatus.state === 'complete' ? 'text-emerald-300' : refinementStatus.state === 'failed' ? 'text-rose-300' : 'text-yellow-400'}`}>{refinementStatus.state === 'complete' ? 'COMPLETE' : refinementStatus.state === 'failed' ? 'ACTION NEEDED' : 'IN PROGRESS'}</span>
                <span className="block text-[11px] font-mono text-slate-400">{refinementStatus.state === 'complete' ? 'Results are available below' : 'This can take a few minutes for large datasets'}</span>
              </div>
            </div>

            {/* Visual Progress Bar */}
            <div className="space-y-1.5">
              <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden border border-slate-700 p-0.5">
                <div className={`h-full rounded-full transition-all duration-500 ${refinementStatus.state === 'complete' ? 'bg-emerald-500' : refinementStatus.state === 'failed' ? 'bg-rose-500' : 'bg-gradient-to-r from-purple-500 via-indigo-500 to-emerald-400'}`} style={{ width: `${refinementStatus.progress || (refinementStatus.state === 'failed' ? 100 : 5)}%` }} />
              </div>
              <div className="flex justify-between text-[11px] font-mono text-slate-400">
                <span>{refinementStatus.error || refinementStatus.message}</span>
                <span>{refinementStatus.state === 'complete' ? 'Scroll down to view results' : 'Please keep this page open'}</span>
              </div>
            </div>

            {refinementStatus.state === 'complete' && (
              <div className="flex flex-wrap gap-3 pt-1">
                <a href="/api/datasets/refined" target="_blank" rel="noreferrer" className="neo-btn neo-btn-white neo-btn-sm text-xs font-bold">
                  VIEW REFINED DATASET
                </a>
                <a href="/api/datasets/refined/download" className="neo-btn neo-btn-primary neo-btn-sm text-xs font-bold">
                  DOWNLOAD REFINED DATASET
                </a>
                <button
                  onClick={onOpenManualVerification}
                  disabled={manualLoading || manualReviewCount === 0}
                  className="neo-btn neo-btn-white neo-btn-sm text-xs font-bold"
                >
                  {manualLoading ? 'LOADING REVIEW…' : `MANUAL REVIEW PAIRS (${manualReviewCount})`}
                </button>
              </div>
            )}

          </div>
        )}

      </div>
    </section>
  );
}
