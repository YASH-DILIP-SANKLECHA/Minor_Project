import React, { useState, useEffect } from 'react';
import confetti from 'canvas-confetti';
import Navbar from './components/Navbar';
import Hero from './components/Hero';
import ProcessingPipeline from './components/ProcessingPipeline';
import OptimizationWorkspace from './components/OptimizationWorkspace';
import AnalyticsDashboardSection from './components/AnalyticsDashboardSection';
import DatasetComparisonSection from './components/DatasetComparisonSection';
import ModelComparisonSection from './components/ModelComparisonSection';
import QueryHistorySection from './components/QueryHistorySection';
import DownloadSection from './components/DownloadSection';
import DownloadModal from './components/DownloadModal';
import DatasetComparisonModal from './components/DatasetComparisonModal';
import ErrorBanner from './components/ErrorBanner';
import ManualVerificationPanel from './components/ManualVerificationPanel';

// Import Service Layer & Fast Dynamic Reduction Engine
import { optimizeDataset, getModelComparison, getRefinementStatus, getManualVerification, getSavedDatasetsAndStats, submitManualVerification } from './services/api';
import { getPromptHistory, savePromptHistoryItem, clearPromptHistory } from './utils/storage';

export default function App() {
  // Navigation Scroll-Spy State
  const [activeSection, setActiveSection] = useState('overview');

  // Datasets State
  const [rawText, setRawText] = useState('');
  const [rawFile, setRawFile] = useState(null);
  const [optimizedText, setOptimizedText] = useState('');
  const [optimizationStats, setOptimizationStats] = useState(null);

  // Prompt & Comparison State
  const [prompt, setPrompt] = useState('');
  const [rawAnswer, setRawAnswer] = useState('');
  const [optimizedAnswer, setOptimizedAnswer] = useState('');
  const [comparison, setComparison] = useState(null);

  // History State
  const [promptHistory, setPromptHistory] = useState([]);
  const [activeHistoryId, setActiveHistoryId] = useState(null);

  // Processing & Job Status State
  const [isProcessing, setIsProcessing] = useState(false);
  const [refinementStatus, setRefinementStatus] = useState({ state: 'idle', message: '', progress: 0, error: null });
  const [currentStageIndex, setCurrentStageIndex] = useState(0);
  const [progressPercentage, setProgressPercentage] = useState(0);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [error, setError] = useState('');
  const [manualPairs, setManualPairs] = useState(null);
  const [manualLoading, setManualLoading] = useState(false);
  const [resolvingCase, setResolvingCase] = useState(null);

  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);

  // Define 8 Pipeline Stages
  const stagesList = [
    { id: 1, name: 'Raw dataset', description: 'User text received', status: currentStageIndex > 0 ? 'completed' : currentStageIndex === 0 && isProcessing ? 'processing' : 'idle' },
    { id: 2, name: 'Prepare content', description: 'Text is organized for review', status: currentStageIndex > 1 ? 'completed' : currentStageIndex === 1 ? 'processing' : 'idle' },
    { id: 3, name: 'Find similar content', description: 'Related statements identified', status: currentStageIndex > 2 ? 'completed' : currentStageIndex === 2 ? 'processing' : 'idle' },
    { id: 4, name: 'Duplicate decisions', description: 'Retain one semantic representative', status: currentStageIndex > 3 ? 'completed' : currentStageIndex === 3 ? 'processing' : 'idle' },
    { id: 5, name: 'Check conflicts', description: 'Conflicting statements reviewed', status: currentStageIndex > 4 ? 'completed' : currentStageIndex === 4 ? 'processing' : 'idle' },
    { id: 6, name: 'Verify decisions', description: 'Conflicts are assessed', status: currentStageIndex > 5 ? 'completed' : currentStageIndex === 5 ? 'processing' : 'idle' },
    { id: 7, name: 'Create refined dataset', description: 'A clean version is prepared', status: currentStageIndex > 6 ? 'completed' : currentStageIndex === 6 ? 'processing' : 'idle' },
    { id: 8, name: 'View results', description: 'Your report is ready', status: currentStageIndex >= 7 ? 'completed' : 'idle' },
  ];

  // Load initial prompt history
  useEffect(() => {
    const saved = getPromptHistory();
    setPromptHistory(saved);
  }, []);

  // The processing status belongs to the backend job, not to this browser
  // tab. Restore it if the user refreshes the page while a long refinement is
  // in progress.
  useEffect(() => {
    let active = true;
    getRefinementStatus()
      .then(async (status) => {
        if (!active || !status.refinement || status.refinement.state === 'idle') return;
        setRefinementStatus(status.refinement);
        setIsProcessing(['queued', 'running'].includes(status.refinement.state));
        setCurrentStageIndex(Math.min(7, Math.floor((status.refinement.progress || 0) / 13)));
        setProgressPercentage(status.refinement.progress || 0);
        if (status.refinement.state === 'complete') {
          const saved = await getSavedDatasetsAndStats();
          if (!active) return;
          setRawText(saved.rawText);
          setOptimizedText(saved.optimizedText);
          setOptimizationStats(saved.stats);
        }
      })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const handleRefinementStatus = (status) => {
    setRefinementStatus(status);
    const progress = Number(status.progress || 0);
    setProgressPercentage(progress);
    if (status.state === 'complete') {
      setCurrentStageIndex(7);
    } else if (status.state === 'queued' || status.state === 'running') {
      setCurrentStageIndex(Math.min(6, Math.floor(progress / 13)));
    }
  };

  // IntersectionObserver Scroll-Spy setup for section navigation
  useEffect(() => {
    const sectionIds = ['overview', 'process', 'upload', 'analytics', 'compare-models', 'history'];
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 200;
      for (const id of sectionIds) {
        const element = document.getElementById(id);
        if (element) {
          const top = element.offsetTop;
          const height = element.offsetHeight;
          if (scrollPosition >= top && scrollPosition < top + height) {
            setActiveSection(id);
            break;
          }
        }
      }
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Smooth scroll handler
  const handleNavigate = (sectionId) => {
    setActiveSection(sectionId);
    const element = document.getElementById(sectionId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  };

  // Run Optimization Workflow with stage progress simulation
  const handleRunOptimization = async () => {
    if (!rawText || !rawText.trim()) {
      setError('Please upload a .TXT file or paste raw dataset text first.');
      return;
    }

    setError('');
    setIsProcessing(true);
    setRefinementStatus({ state: 'queued', message: 'Dataset accepted. Starting refinement…', progress: 0, error: null });
    setCurrentStageIndex(0);
    setProgressPercentage(0);

    try {
      const result = await optimizeDataset(rawText, handleRefinementStatus);
      setCurrentStageIndex(7);
      setProgressPercentage(100);

      setOptimizedText(result.optimizedText);
      setRawText(result.rawText);
      setOptimizationStats(result.stats);
      setManualPairs(null);

      confetti({
        particleCount: 70,
        spread: 60,
        origin: { y: 0.6 }
      });

      setIsProcessing(false);
    } catch (err) {
      setIsProcessing(false);
      setRefinementStatus({ state: 'failed', message: 'Refinement could not be completed.', progress: 0, error: err.message || '' });
      setError(err.message || 'An error occurred during dataset optimization.');
    }
  };

  const handleOpenManualVerification = async () => {
    setError('');
    setManualLoading(true);
    try {
      const review = await getManualVerification();
      setManualPairs(review.pairs || []);
      setTimeout(() => document.getElementById('manual-verification')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0);
    } catch (err) {
      setError(err.message || 'Unable to load the statements for manual verification.');
    } finally {
      setManualLoading(false);
    }
  };

  const handleResolveManualVerification = async (pair, decision) => {
    setError('');
    setResolvingCase(pair.case_number);
    try {
      await submitManualVerification(pair.case_number, decision);
      const [review, saved] = await Promise.all([
        getManualVerification(),
        getSavedDatasetsAndStats(),
      ]);
      setManualPairs(review.pairs || []);
      setRawText(saved.rawText);
      setOptimizedText(saved.optimizedText);
      setOptimizationStats(saved.stats);
      setRefinementStatus(saved.status.refinement);
    } catch (err) {
      setError(err.message || 'Unable to save the manual verification choice.');
    } finally {
      setResolvingCase(null);
    }
  };

  // Run Model Comparison
  const handleRunComparison = async (promptQuery) => {
    const currentPrompt = promptQuery || prompt;

    if (!currentPrompt || !currentPrompt.trim()) {
      setError('Please enter a question to ask both AI models.');
      return;
    }
    if (!rawText || !optimizedText) {
      setError('Missing optimized dataset. Please click START OPTIMIZATION first.');
      return;
    }

    setError('');
    setComparisonLoading(true);

    try {
      const result = await getModelComparison(currentPrompt, rawText, optimizedText);
      setRawAnswer(result.rawModelResponse);
      setOptimizedAnswer(result.optimizedModelResponse);
      setComparison(result);

      const updatedHistory = savePromptHistoryItem({
        prompt: currentPrompt,
        rawAnswer: result.rawModelResponse,
        optimizedAnswer: result.optimizedModelResponse,
        comparison: result,
        rawText,
        optimizedText
      });
      setPromptHistory(updatedHistory);
      if (updatedHistory.length > 0) {
        setActiveHistoryId(updatedHistory[0].id);
      }
    } catch (err) {
      setError(err.message || 'An error occurred during dual AI model inference.');
    } finally {
      setComparisonLoading(false);
    }
  };

  // Replay history query
  const handleSelectHistoryItem = (item) => {
    setActiveHistoryId(item.id);
    setPrompt(item.prompt);
    setRawAnswer(item.rawAnswer);
    setOptimizedAnswer(item.optimizedAnswer);
    setComparison(item.comparison);
    if (item.rawText) {
      setRawText(item.rawText);
      setOptimizedText(item.optimizedText || '');
    }
    handleNavigate('compare-models');
  };

  const handleClearHistory = () => {
    clearPromptHistory();
    setPromptHistory([]);
    setActiveHistoryId(null);
  };

  return (
    <div className="min-h-screen bg-[#FAF9F5] text-slate-900 flex flex-col font-sans selection:bg-yellow-200">
      
      {/* 1. Minimalist Scroll-Spy Navbar */}
      <Navbar
        activeSection={activeSection}
        onNavigate={handleNavigate}
      />

      {/* Main SaaS Layout Flow */}
      <main className="flex-1 space-y-4">
        
        {/* 2. HERO / OVERVIEW SECTION */}
        <Hero
          onUploadClick={() => handleNavigate('upload')}
        />

        <ProcessingPipeline isProcessing={isProcessing} currentStageIndex={currentStageIndex} />

        {/* 4. OPTIMIZATION WORKSPACE & DATASET INPUT */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          {error && (
            <ErrorBanner
              message={error}
              onDismiss={() => setError('')}
              onRetry={handleRunOptimization}
            />
          )}

          <OptimizationWorkspace
            rawText={rawText}
            setRawText={(text) => {
            setRawText(text);
            setOptimizedText('');
            setOptimizationStats(null);
            setRawAnswer('');
            setOptimizedAnswer('');
            setComparison(null);
            }}
            rawFile={rawFile}
            setRawFile={setRawFile}
            onRunOptimization={handleRunOptimization}
            isProcessing={isProcessing}
            refinementStatus={refinementStatus}
            resultsReady={Boolean(optimizationStats)}
            processingStage={stagesList[currentStageIndex]}
            progressPercentage={progressPercentage}
            stagesList={stagesList}
            error={error}
            onError={(err) => setError(err)}
            manualReviewCount={optimizationStats?.manualReview || 0}
            onOpenManualVerification={handleOpenManualVerification}
            manualLoading={manualLoading}
          />
        </div>

        <div id="manual-verification">
          <ManualVerificationPanel
            pairs={manualPairs}
            loading={manualLoading}
            resolvingCase={resolvingCase}
            onResolve={handleResolveManualVerification}
            onClose={() => setManualPairs(null)}
          />
        </div>

        {/* 5. DATASET ANALYTICS DASHBOARD (EXACTLY 4 PRIMARY CHARTS) */}
        <AnalyticsDashboardSection
          stats={optimizationStats}
          comparison={comparison}
          rawText={rawText}
          optimizedText={optimizedText}
        />

        {/* 6. RAW VS OPTIMIZED COMPARISON */}
        <DatasetComparisonSection
          rawText={rawText}
          optimizedText={optimizedText}
          stats={optimizationStats}
          onOpenModal={() => setIsModalOpen(true)}
        />

        {/* 7. DUAL AI MODEL COMPARISON */}
        <ModelComparisonSection
          prompt={prompt}
          setPrompt={setPrompt}
          rawAnswer={rawAnswer}
          optimizedAnswer={optimizedAnswer}
          comparison={comparison}
          onRunComparison={handleRunComparison}
          loading={comparisonLoading}
          isDisabled={!rawText || !optimizedText}
          suggestedPrompts={[]}
        />

        {/* Prompt query history */}
        <QueryHistorySection
          historyItems={promptHistory}
          onSelectHistoryItem={handleSelectHistoryItem}
          onClearHistory={handleClearHistory}
          activeHistoryId={activeHistoryId}
        />

        {/* 10. DOWNLOAD CTA */}
        <DownloadSection ready={Boolean(optimizationStats)} onOpenDownloadModal={() => setIsDownloadModalOpen(true)} />

      </main>

      {/* Footer */}
      <footer className="bg-slate-950 text-white border-t border-slate-800 py-10 px-4">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4 text-center md:text-left">
          <div>
            <h3 className="font-heading font-black text-lg text-yellow-400">
              AI DATASET OPTIMIZER
            </h3>
            <p className="text-xs text-[#94A3B8] mt-0.5">
              Reduce the data. Preserve the intelligence.
            </p>
          </div>

          <div className="text-xs font-mono text-slate-500">
            Minor Project Platform • Built with React, Vite, Tailwind CSS & Recharts
          </div>
        </div>
      </footer>

      {/* Global Modals */}
      <DownloadModal
        isOpen={isDownloadModalOpen}
        onClose={() => setIsDownloadModalOpen(false)}
        rawText={rawText}
        optimizedText={optimizedText}
        stats={optimizationStats}
        prompt={prompt}
        rawAnswer={rawAnswer}
        optimizedAnswer={optimizedAnswer}
        comparison={comparison}
      />

      <DatasetComparisonModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        rawText={rawText}
        optimizedText={optimizedText}
      />

    </div>
  );
}
