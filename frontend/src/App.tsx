import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Activity, History, Info, Loader2, BookOpen, ShieldCheck, ListOrdered, ChevronDown, Menu, X } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, LabelList, ReferenceArea } from 'recharts';

import logoImg from './assets/FA_logo.png';
import PositionsPage from './PositionsPage';
import FirePlanner from './FirePlanner';

function App() {
  const [currentPage, setCurrentPage] = useState<'find' | 'portfolio' | 'fire'>('find');
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [perfData, setPerfData] = useState<any>(null);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [period, setPeriod] = useState('5d');
  const [mode, setMode] = useState('perf');
  const [errorMessage, setErrorMessage] = useState('');
  const [indicators, setIndicators] = useState<string[]>([]);
  const [showIndicators, setShowIndicators] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const taOptions = [
    { label: 'SMA 20', value: 'sma20', color: '#D0BB78' },
    { label: 'SMA 50', value: 'sma50', color: '#365477' },
    { label: 'Bollinger Bands', value: 'bollinger', color: '#502068' },
    { label: 'RSI', value: 'rsi', color: '#99b6d6' },
    { label: 'MACD', value: 'macd', color: '#1E8257' }
  ];

  const timeframes = [
    { label: '1D', value: '1d' }, { label: '1W', value: '5d' }, { label: '1M', value: '1mo' },
    { label: '3M', value: '3mo' }, { label: 'YTD', value: 'ytd' }, { label: '1Y', value: '1y' }, { label: '5Y', value: '5y' }
  ];

  const API_BASE = '/api';

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!ticker) return;
    setLoading(true); setErrorMessage(''); setForecastData([]); setHistory([]); setData(null);
    try {
      const [res, histRes, foreRes] = await Promise.all([
        axios.get(`${API_BASE}/analyze/${ticker}`),
        axios.get(`${API_BASE}/history/${ticker}?period=${period}`),
        axios.get(`${API_BASE}/forecast/${ticker}`)
      ]);
      setData(res.data);
      setHistory(histRes.data?.data || []);
      setPerfData(histRes.data?.performance);
      
      const combined = [
        ...(foreRes.data.history || []).map((p: any) => ({ 
          date: p.date, 
          historyPrice: p.price 
        })),
        ...(foreRes.data.hybrid || []).map((p: any, i: number) => ({ 
          date: p.date, 
          hybridPrice: p.price, 
          baselinePrice: foreRes.data.baseline[i]?.price 
        }))
      ];
      setForecastData(combined);
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Ticker not found or data unavailable.';
      setErrorMessage(msg);
      setData(null);
    } finally { setLoading(false); }
  };

  const updateChart = async (symbol: string, time: string, selectedInds: string[] = indicators) => {
    try {
      const indsParam = selectedInds.length > 0 ? `&indicators=${selectedInds.join(',')}` : '';
      const res = await axios.get(`${API_BASE}/history/${symbol}?period=${time}${indsParam}`);
      if (res.data) {
        setHistory(res.data.data || []);
        setPerfData(res.data.performance);
      }
    } catch (err) { console.error("Chart load failed"); }
  };

  useEffect(() => { if (data?.ticker && mode === 'perf') updateChart(data.ticker, period, indicators); }, [period, indicators]);

  const formatPrice = (val: number) => typeof val === 'number' ? val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : 'N/A';
  const formatCompact = (val: number) => typeof val === 'number' ? new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(val) : 'N/A';

  const handleViewTicker = (t: string) => {
    setTicker(t);
    setCurrentPage('find');
    setTimeout(() => {
      const form = document.querySelector('form');
      if (form) {
        form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
      }
    }, 100);
  };

  const HealthCard = ({ label, value, avg }: { label: string, value: string, avg: any }) => (
    <div className="bg-white p-5 rounded-m border border-grey-200 shadow-sm flex flex-col justify-center h-full transition-all hover:translate-x-[1px] hover:translate-y-[1px] hover:shadow-none">
      <p className="text-[10px] font-bold text-grey-300 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-xl font-extrabold text-grey-900 leading-none">{value}</p>
      <div className="mt-3 pt-3 border-t border-grey-100">
        <p className="text-[9px] font-bold text-grey-300 uppercase tracking-tighter italic">Industry Avg: {typeof avg === 'number' ? avg.toFixed(2) : (avg || 'N/A')}</p>
      </div>
    </div>
  );

  const EmptyState = () => (
    <div className="flex flex-col items-center justify-center py-20 animate-in fade-in zoom-in duration-700">
      <div className="relative mb-12">
        <div className="absolute inset-0 bg-primary/30 rounded-full blur-3xl opacity-50 animate-pulse"></div>
        
        <div className="relative flex items-center justify-center">
          <div className="absolute w-32 h-32 bg-primary border-2 border-tertiary rounded-m translate-x-4 translate-y-4 shadow-[4px_4px_0px_0px_#0f172a]"></div>
          <div className="relative w-32 h-32 bg-white border-2 border-tertiary rounded-m flex items-center justify-center shadow-[4px_4px_0px_0px_#0f172a]">
            <Activity size={64} className="text-tertiary" strokeWidth={2.5} />
          </div>
          <div className="absolute -top-4 -right-4 w-12 h-12 bg-primary border-2 border-tertiary rounded-m flex items-center justify-center shadow-[2px_2px_0px_0px_#0f172a] animate-bounce">
            <Search size={20} className="text-tertiary" />
          </div>
        </div>
      </div>
      <h2 className="text-3xl font-extrabold text-tertiary tracking-tight mb-2 text-center uppercase">Institutional Intelligence</h2>
      <p className="text-grey-300 font-bold text-center max-w-sm">Search any stock or ETF to unlock real-time institutional-grade analysis.</p>
      <div className="mt-8 flex flex-wrap justify-center gap-3">
        {['AAPL', 'NVDA', 'TSLA', 'SPY', 'XOM', 'SCHD'].map(t => (
          <button key={t} onClick={() => { setTicker(t); }} className="px-6 py-2.5 bg-primary border-2 border-tertiary rounded-m text-[12px] font-bold uppercase text-tertiary shadow-[4px_4px_0px_0px_#15191d] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all">{t}</button>
        ))}
      </div>
    </div>
  );

  const NotFoundState = () => (
    <div className="flex flex-col items-center justify-center py-20 animate-in slide-in-from-bottom-10 duration-500">
      <div className="w-32 h-32 bg-[#e7dcdc] rounded-m flex items-center justify-center mb-8 border-2 border-tertiary shadow-[4px_4px_0px_0px_#15191d]">
        <Info size={48} className="text-tertiary opacity-50" />
      </div>
      <h2 className="text-3xl font-extrabold text-tertiary tracking-tight mb-2 uppercase italic text-center">Analysis Failed</h2>
      <p className="text-grey-300 font-bold text-center max-w-sm px-6">{errorMessage}</p>
      <button onClick={() => {setErrorMessage(''); setTicker('');}} className="mt-8 px-8 py-3 bg-primary border-2 border-tertiary text-tertiary rounded-m text-xs font-bold uppercase tracking-widest shadow-[4px_4px_0px_0px_#15191d] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all">Clear Search</button>
    </div>
  );

  const NavTabs = ({ isMobile = false }) => (
    <div className={`${isMobile ? 'flex flex-col space-y-4' : 'flex gap-8 border-b-2 border-grey-100'}`}>
      <button 
        onClick={() => { setCurrentPage('find'); if (isMobile) setIsMenuOpen(false); }}
        className={`${isMobile ? 'text-left px-4 py-2 text-lg' : 'pb-4 px-2 text-[12px]'} font-black uppercase transition-all relative ${
          currentPage === 'find' ? 'text-tertiary' : 'text-grey-300 hover:text-grey-500'
        }`}
      >
        Find
        {!isMobile && currentPage === 'find' && <div className="absolute bottom-[-2px] left-0 w-full h-[3px] bg-tertiary"></div>}
      </button>
      <button 
        onClick={() => { setCurrentPage('portfolio'); if (isMobile) setIsMenuOpen(false); }}
        className={`${isMobile ? 'text-left px-4 py-2 text-lg' : 'pb-4 px-2 text-[12px]'} font-black uppercase transition-all relative ${
          currentPage === 'portfolio' ? 'text-tertiary' : 'text-grey-300 hover:text-grey-500'
        }`}
      >
        Portfolio
        {!isMobile && currentPage === 'portfolio' && <div className="absolute bottom-[-2px] left-0 w-full h-[3px] bg-tertiary"></div>}
      </button>
      <button 
        onClick={() => { setCurrentPage('fire'); if (isMobile) setIsMenuOpen(false); }}
        className={`${isMobile ? 'text-left px-4 py-2 text-lg' : 'pb-4 px-2 text-[12px]'} font-black uppercase transition-all relative ${
          currentPage === 'fire' ? 'text-tertiary' : 'text-grey-300 hover:text-grey-500'
        }`}
      >
        FIRE
        {!isMobile && currentPage === 'fire' && <div className="absolute bottom-[-2px] left-0 w-full h-[3px] bg-tertiary"></div>}
      </button>
    </div>
  );

  return (
    <div className="min-h-screen bg-secondary text-grey-500 p-6 font-sans">
      <nav className="max-w-7xl mx-auto mb-10 h-16 md:h-20 flex items-center">
        <div className="w-full flex justify-between items-center gap-8">
          <div className="flex items-center gap-8 h-full">
            <div className="flex items-center gap-3 shrink-0">
              <img src={logoImg} alt="FinAdvisor Logo" className="w-10 h-10 object-contain rounded-m border-2 border-tertiary shadow-[2px_2px_0px_0px_#15191d]" />
              <div className="hidden sm:block"><h1 className="text-lg font-extrabold uppercase tracking-tight text-tertiary">FinAdvisor</h1><p className="text-[10px] font-bold text-grey-300 uppercase italic mt-1 leading-none">Institutional Intelligence</p></div>
            </div>
            
            <div className="hidden md:flex h-full items-center">
              <NavTabs />
            </div>
          </div>
          
          <div className="flex items-center gap-4 grow justify-end">
            <form onSubmit={handleSearch} className="relative group hidden md:block w-full max-w-xs">
              <input type="text" placeholder="Search Ticker..." className="w-full pl-10 pr-4 py-3 bg-white border border-[#6b7280] rounded-m focus:ring-4 focus:ring-primary/20 outline-none transition-all font-bold text-[14px] text-tertiary placeholder:text-[#cbd5e1]" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
              {loading ? <Loader2 className="absolute left-3 top-[14px] text-primary animate-spin w-4 h-4" /> : <Search className="absolute left-3 top-[14px] text-grey-300 w-4 h-4" />}
            </form>
            
            <button 
              className="md:hidden p-2 text-tertiary"
              onClick={() => setIsMenuOpen(!isMenuOpen)}
            >
              {isMenuOpen ? <X size={28} /> : <Menu size={28} />}
            </button>
          </div>
        </div>

        {/* Mobile Menu Overlay */}
        {isMenuOpen && (
          <div className="fixed inset-x-6 top-24 md:hidden bg-white border-2 border-tertiary p-6 rounded-m shadow-[4px_4px_0px_0px_#15191d] z-[90] animate-in slide-in-from-top-4">
            <NavTabs isMobile />
            <form onSubmit={handleSearch} className="relative group mt-6">
              <input type="text" placeholder="Search Ticker..." className="w-full pl-12 pr-6 py-[14px] bg-secondary border border-grey-200 rounded-m outline-none font-bold text-tertiary" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
              <Search className="absolute left-4 top-[15px] text-grey-300 w-5 h-5" />
            </form>
          </div>
        )}
      </nav>

      <main className="max-w-7xl mx-auto">
        {currentPage === 'portfolio' ? (
          <PositionsPage apiBase={API_BASE} onViewTicker={handleViewTicker} />
        ) : currentPage === 'fire' ? (
          <FirePlanner apiBase={API_BASE} />
        ) : (
          <>
            {!data && !loading && !errorMessage && <EmptyState />}
            {errorMessage && <NotFoundState />}
            
            {data && (
              <div className="space-y-6 animate-in fade-in duration-700">
                <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                  <div className={`${data.type === 'ETF' ? 'lg:col-span-4' : 'lg:col-span-3'} bg-white p-6 md:p-8 rounded-m border border-grey-200 shadow-sm flex justify-between items-center relative overflow-hidden gap-4`}>
                    <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl opacity-50 -mr-32 -mt-32"></div>
                    <div className="relative z-10 min-w-0">
                      <div className="flex flex-wrap gap-2 mb-2">
                        <span className="px-3 py-1 bg-primary/20 text-tertiary border border-tertiary/10 rounded-m text-[10px] font-extrabold uppercase tracking-widest">{data.type}</span>
                        <span className="px-3 py-1 bg-secondary text-grey-300 border border-tertiary/10 rounded-m text-[10px] font-extrabold uppercase tracking-widest">{data.industry}</span>
                      </div>
                      <h2 className="text-3xl md:text-6xl font-extrabold tracking-tighter leading-none text-tertiary truncate">{data.ticker}</h2>
                      <p className="text-grey-300 font-bold text-sm md:text-lg mt-1 tracking-tight truncate">{data.info?.name}</p>
                    </div>
                    <div className="text-right relative z-10 shrink-0">
                      <p className="text-[10px] font-bold text-grey-300 uppercase tracking-widest mb-1">Live Price</p>
                      <p className="text-3xl md:text-6xl font-mono font-extrabold text-tertiary tracking-tighter">${formatPrice(data.metrics?.price)}</p>
                    </div>
                  </div>
                  
                  {data.type !== 'ETF' && (
                    <div className={`p-8 rounded-m border-2 border-tertiary flex flex-col justify-center text-center shadow-[6px_6px_0px_0px_#15191d] transition-all duration-500 ${
                      data.metrics?.intrinsic > data.metrics?.price ? 'bg-[#1E8257] text-white' : 'bg-[#A45951] text-white'
                    }`}>

                       <p className="text-[11px] font-extrabold uppercase tracking-widest opacity-70 mb-1">Blended Target Price</p>
                       {data.metrics?.error ? (
                         <p className="text-xl font-extrabold px-4 leading-tight py-2 uppercase italic">{data.metrics.error}</p>
                       ) : (
                         <>
                          <p className="text-5xl font-mono font-black tracking-tighter text-white">${formatPrice(data.metrics?.intrinsic)}</p>
                          
                          <div className="mt-4">
                              <div className="bg-white/10 p-3 rounded-m text-[10px] font-extrabold leading-relaxed uppercase text-white border border-white/20">
                                  {data.metrics?.intrinsic > data.metrics?.price ? 
                                    `Undervalued by ${Math.abs(((data.metrics?.intrinsic - data.metrics?.price)/data.metrics?.price)*100).toFixed(1)}%` : 
                                    `Overvalued by ${Math.abs(((data.metrics?.intrinsic - data.metrics?.price)/data.metrics?.price)*100).toFixed(1)}%`
                                  }
                              </div>
                          </div>
                         </>
                       )}
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
                   <HealthCard label="Mkt Capital" value={formatCompact(data.metrics?.mkt_cap)} avg={formatCompact(data.averages?.mkt)} />
                   <HealthCard label="EPS (TTM)" value={data.metrics?.eps?.toFixed(2) || 'N/A'} avg={data.averages?.eps?.toFixed(2) || 'N/A'} />
                   <HealthCard label="P/E Ratio" value={data.metrics?.pe?.toFixed(2) || 'N/A'} avg={data.averages?.pe?.toFixed(2) || 'N/A'} />
                   <HealthCard label="Exp. Ratio" value={data.metrics?.expense_ratio ? `${data.metrics.expense_ratio.toFixed(2)}%` : '0.00%'} avg={`${data.averages?.exp?.toFixed(2) || '0.00'}%`} />
                   <HealthCard label="Risk (Beta)" value={data.metrics?.beta?.toFixed(2) || '1.00'} avg={data.averages?.risk?.toFixed(2) || '1.00'} />
                   <HealthCard label="Div / Year" value={typeof data.metrics?.div_annual === 'number' ? `$${data.metrics.div_annual.toFixed(2)}` : 'N/A'} avg={`$${data.averages?.div?.toFixed(2) || '0.00'}`} />
                </div>

                <div className="flex justify-center">
                   <div className="bg-[#efe9e980] content-stretch flex items-center justify-center p-[4px] relative rounded-m w-full max-w-[342px] border border-grey-200">
                      <button onClick={() => setMode('perf')} className={`content-stretch flex flex-1 flex-col items-center justify-center px-4 py-2 relative rounded-m text-[12px] font-bold tracking-widest uppercase transition-all ${mode === 'perf' ? 'bg-white shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] text-tertiary border border-grey-100' : 'text-grey-400 hover:text-tertiary'}`}>Performance</button>
                      <button onClick={() => setMode('forecast')} className={`content-stretch flex flex-1 flex-col items-center justify-center px-4 py-2 relative rounded-m text-[12px] font-bold tracking-widest uppercase transition-all ${mode === 'forecast' ? 'bg-white shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] text-tertiary border border-grey-100' : 'text-grey-400 hover:text-tertiary'}`}>AI Forecast</button>
                   </div>
                </div>

                <div className="bg-white p-6 md:p-10 rounded-m border border-grey-200 shadow-sm">
                   <div className="flex flex-col lg:flex-row justify-between items-center mb-8 md:mb-10 gap-6">
                      <div className="flex items-center gap-4 self-start">
                        <div className="p-3 bg-secondary border border-grey-100 rounded-m"><Activity size={24} className="text-tertiary" /></div>
                        <div>
                          <h3 className="font-extrabold text-xl md:text-2xl tracking-tight uppercase text-tertiary">
                            {mode === 'perf' ? 'Performance' : 'AI FINANCIAL FORECAST'}
                          </h3>
                          {perfData && mode === 'perf' && <span className={`text-xs font-extrabold ${perfData.is_positive ? 'text-[#1E8257]' : 'text-[#A45951]'}`}>{perfData.pct}% trend</span>}
                        </div>
                      </div>

                      {mode === 'perf' ? (
                        <div className="flex flex-wrap justify-end gap-3">
                          <div className="flex bg-secondary p-1.5 rounded-m border border-grey-100 gap-1">
                            {timeframes.map((tf) => (
                              <button key={tf.value} onClick={() => setPeriod(tf.value)} className={`px-3 md:px-4 py-1.5 rounded-m text-[10px] font-extrabold uppercase transition-all ${period === tf.value ? 'bg-white border border-grey-200 text-tertiary shadow-[1px_1px_0px_0px_#15191d]' : 'text-grey-300 hover:text-grey-500'}`}>{tf.label}</button>
                            ))}
                          </div>

                          <div className="relative">
                            <button 
                              onClick={() => setShowIndicators(!showIndicators)}
                              className="px-4 h-[43px] bg-white border border-grey-200 rounded-m text-tertiary text-[10px] font-extrabold uppercase shadow-[1px_1px_0px_0px_#15191d] flex items-center gap-2 hover:bg-secondary transition-all"
                            >
                              Technical Analysis <ChevronDown size={14} className={`transition-transform ${showIndicators ? 'rotate-180' : ''}`} />
                            </button>
                            
                            {showIndicators && (
                              <div className="absolute top-full right-0 mt-2 w-48 bg-white border border-grey-200 rounded-m shadow-[4px_4px_0px_0px_#15191d] z-50 overflow-hidden p-2 space-y-1">
                                {taOptions.map(opt => (
                                  <label 
                                    key={opt.value} 
                                    className="flex items-center gap-3 px-3 py-2 hover:bg-secondary rounded-m cursor-pointer transition-colors group"
                                    style={{ color: indicators.includes(opt.value) ? opt.color : '#404040' }}
                                  >
                                    <input 
                                      type="checkbox" 
                                      style={{ accentColor: opt.color }}
                                      checked={indicators.includes(opt.value)}
                                      onChange={() => {
                                        const next = indicators.includes(opt.value) ? indicators.filter(i => i !== opt.value) : [...indicators, opt.value];
                                        setIndicators(next);
                                      }}
                                    />
                                    <span className="text-[10px] font-black uppercase">
                                      {opt.label}
                                    </span>
                                  </label>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (

                        <div className="flex flex-wrap justify-center gap-4 md:gap-6 text-[10px] font-extrabold uppercase tracking-widest text-grey-300">
                          <span className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#52525b]"></div> History</span>
                          <span className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#99b6d6]"></div> AI Hybrid</span>
                          <span className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#0f172a]"></div> Baseline</span>
                        </div>
                      )}
                   </div>
                   
                   <div className={`${indicators.some(i => ['rsi', 'macd'].includes(i)) ? 'h-[600px]' : 'h-[300px] md:h-[450px]'} w-full space-y-4`}>
                    <div className={indicators.some(i => ['rsi', 'macd'].includes(i)) ? 'h-[60%]' : 'h-full'}>
                      <ResponsiveContainer width="100%" height="100%">
                        {mode === 'perf' ? (
                          <LineChart data={history} margin={{ left: -20, right: 0, top: 10, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                            <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: '900'}} minTickGap={30} padding={{ left: 0, right: 0 }} />
                            <YAxis orientation="right" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                            <Tooltip 
                              contentStyle={{borderRadius: '12px', border: '2px solid #0f172a', boxShadow: '4px 4px 0px 0px #0f172a'}} 
                              labelClassName="font-extrabold text-grey-300 mb-2"
                              formatter={(v: any) => [typeof v === 'number' ? v.toFixed(2) : v, '']}
                            />
                            <Line type="monotone" dataKey="price" stroke={perfData?.is_positive ? "#1E8257" : "#A45951"} strokeWidth={4} dot={false} animationDuration={1000} />
                            {/* Overlays with distinct colors */}
                            {indicators.includes('sma20') && <Line name="SMA 20" type="monotone" dataKey="sma20" stroke="#D0BB78" strokeWidth={2} dot={false} connectNulls />}
                            {indicators.includes('sma50') && <Line name="SMA 50" type="monotone" dataKey="sma50" stroke="#365477" strokeWidth={2} dot={false} connectNulls />}
                            {indicators.includes('bollinger') && (
                              <>
                                <Line name="BB Upper" type="monotone" dataKey="bb_upper" stroke="#502068" strokeWidth={1} dot={false} connectNulls opacity={0.6} />
                                <Line name="BB Lower" type="monotone" dataKey="bb_lower" stroke="#502068" strokeWidth={1} dot={false} connectNulls opacity={0.6} />
                              </>
                            )}

                          </LineChart>

                        ) : (
                        <LineChart data={forecastData}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                          <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} minTickGap={60} />
                          <YAxis orientation="right" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                          <Tooltip contentStyle={{backgroundColor: '#0f172a', borderRadius: '12px', border: 'none', color: '#fff'}} />
                          <Line name="History" type="monotone" dataKey="historyPrice" stroke="#52525b" strokeWidth={2} dot={false} strokeDasharray="5 5" connectNulls />
                          <Line name="AI Hybrid" type="monotone" dataKey="hybridPrice" stroke="#99b6d6" strokeWidth={4} dot={false} connectNulls />
                          <Line name="Baseline" type="monotone" dataKey="baselinePrice" stroke="#0f172a" strokeWidth={2} dot={false} opacity={0.5} connectNulls />
                        </LineChart>
                      )}
                    </ResponsiveContainer>
                    </div>

                    {/* RSI Sub-Chart */}
                    {mode === 'perf' && indicators.includes('rsi') && (
                      <div className="h-[15%] w-full border-t border-grey-100 pt-2">
                        <p className="text-[8px] font-black uppercase text-grey-300 mb-1">Relative Strength Index (14)</p>
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={history} margin={{ left: -20, right: 0, top: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                            <XAxis dataKey="date" hide />
                            <YAxis domain={[0, 100]} orientation="right" tick={{fontSize: 8}} ticks={[30, 70]} />
                            <Line type="monotone" dataKey="rsi" stroke="#99b6d6" strokeWidth={2} dot={false} />
                            <ReferenceArea y1={70} y2={100} fill="#A45951" fillOpacity={0.1} />
                            <ReferenceArea y1={0} y2={30} fill="#1E8257" fillOpacity={0.1} />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    {/* MACD Sub-Chart */}
                    {mode === 'perf' && indicators.includes('macd') && (
                      <div className="h-[20%] w-full border-t border-grey-100 pt-2">
                        <p className="text-[8px] font-black uppercase text-grey-300 mb-1">MACD (12, 26, 9)</p>
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={history} margin={{ left: -20, right: 0, top: 0, bottom: 0 }}>
                            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                            <XAxis dataKey="date" hide />
                            <YAxis orientation="right" tick={{fontSize: 8}} />
                            <Bar dataKey="macd_hist" radius={[2, 2, 0, 0]}>
                              {history.map((entry, index) => (
                                <Cell key={`cell-${index}`} fill={(entry?.macd_hist ?? 0) >= 0 ? "#1E8257" : "#A45951"} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}
                   </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                   <div className="bg-white p-8 rounded-m border border-grey-200 shadow-sm flex flex-col">
                      <h3 className="font-extrabold text-sm uppercase tracking-widest text-tertiary mb-8 flex items-center gap-2"><History size={18} className="text-[#1E8257]"/> Return History</h3>
                      <div className="flex-1 min-h-[300px]">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={Object.entries(data.performance || {}).map(([k, v]) => ({ name: k, val: v }))} layout="vertical">
                            <XAxis type="number" axisLine={false} tickLine={false} tick={{fontSize: 10, fill: '#889099'}} tickFormatter={(v) => `${v}%`} />
                            <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 'extrabold', fill: '#0f172a'}} width={40} />
                            <Tooltip cursor={{fill: '#f5f2ed'}} formatter={(v: any) => [`${v}%`, 'Return']} />
                            <Bar dataKey="val" radius={[0, 4, 4, 0]}>
                              <LabelList dataKey="val" position="right" formatter={(v: any) => `${v}%`} style={{ fontSize: '10px', fontWeight: 'bold', fill: '#0f172a' }} />
                              {Object.entries(data.performance || {}).map((entry: any, index) => (
                                <Cell key={`cell-${index}`} fill={entry[1] > 0 ? "#1E8257" : "#A45951"} stroke="#0f172a" strokeWidth={1} />
                              ))}
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                   </div>

                   <div className="bg-white p-8 rounded-m border border-grey-200 shadow-sm flex flex-col justify-between">
                      <h3 className="font-extrabold text-sm uppercase tracking-widest text-tertiary mb-6 flex items-center gap-2"><BookOpen size={18} className="text-[#1E8257]" /> Digital Library</h3>
                      <div className="grid grid-cols-2 gap-4 mb-6">
                         <a href={`https://www.sec.gov/edgar/search/#/q=${data.ticker}&forms=10-K,10-Q`} target="_blank" rel="noreferrer" className="p-6 bg-primary border-2 border-tertiary rounded-m flex flex-col justify-center text-center shadow-[2px_2px_0px_0px_#15191d] hover:shadow-none hover:translate-x-[1px] hover:translate-y-[1px] group transition-all">
                            <p className="text-[10px] font-extrabold text-tertiary uppercase mb-1 opacity-70 leading-none">SEC</p>
                            <p className="font-extrabold text-lg group-hover:underline text-tertiary uppercase leading-none">Filings</p>
                         </a>
                         <a href={`https://finance.yahoo.com/quote/${data.ticker}/financials`} target="_blank" rel="noreferrer" className="p-6 bg-primary border-2 border-tertiary rounded-m flex flex-col justify-center text-center shadow-[2px_2px_0px_0px_#15191d] hover:shadow-none hover:translate-x-[1px] hover:translate-y-[1px] group transition-all">
                            <p className="text-[10px] font-extrabold text-tertiary uppercase mb-1 opacity-70 leading-none">Annual</p>
                            <p className="font-extrabold text-lg group-hover:underline text-tertiary uppercase leading-none">Report</p>
                         </a>
                      </div>
                      <div className="flex-1 space-y-3 overflow-y-auto max-h-[200px] pr-2 custom-scrollbar">
                        <p className="text-[10px] font-black text-tertiary uppercase tracking-widest mb-2 flex items-center gap-2 italic"><ShieldCheck size={14} className="text-[#1E8257]"/> Latest Market News</p>
                        {data.news?.map((n: any, i: number) => (
                          <a key={i} href={n.link} target="_blank" rel="noreferrer" className="block p-3 bg-secondary hover:bg-primary/10 border border-grey-100 rounded-m transition-all group">
                            <p className="text-[8px] font-black text-primary uppercase mb-1">{n.publisher}</p>
                            <p className="text-[11px] font-bold text-tertiary leading-snug group-hover:text-[#1E8257] line-clamp-2 uppercase italic">"{n.title}"</p>
                          </a>
                        ))}
                      </div>
                   </div>
                </div>

                <div className="bg-[rgba(80,136,199,0.2)] border border-[#131416] p-10 rounded-m text-tertiary shadow-[4px_4px_0px_0px_#131416] relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-96 h-96 bg-primary/10 rounded-full blur-[120px] opacity-20 -mr-48 -mt-48"></div>
                    <h3 className="font-extrabold text-xl uppercase tracking-widest text-tertiary mb-6 flex items-center gap-3"><Info size={24}/> {data.type === 'ETF' ? 'Fund Intelligence' : 'Company Intelligence'}</h3>
                    <p className="text-sm font-bold text-grey-900 leading-relaxed italic line-clamp-6">{data.info?.summary}</p>
                    
                    {data.type === 'ETF' && data.holdings?.length > 0 && (
                      <div className="mt-6 bg-white/30 border border-[#131416]/20 p-6 rounded-m shadow-inner">
                         <h4 className="font-extrabold text-xs uppercase tracking-widest text-tertiary mb-4 flex items-center gap-2"><ListOrdered size={16}/> Top 10 Holdings</h4>
                         <div className="grid grid-cols-2 gap-x-10 gap-y-3">
                            {data.holdings.map((h: any, i: number) => (
                              <div key={i} className="flex justify-between items-center group">
                                 <div className="flex flex-col">
                                    <span className="text-[10px] font-extrabold text-tertiary">{h.symbol}</span>
                                    <span className="text-[8px] font-bold text-grey-500 uppercase truncate max-w-[140px]">{h.name}</span>
                                 </div>
                                 <span className="text-[10px] font-extrabold text-tertiary">{h.pct}%</span>
                              </div>
                            ))}
                         </div>
                      </div>
                    )}
                 </div>
              </div>
            )}
          </>
        )}
      </main>
      
      <footer className="max-w-7xl mx-auto mt-12 pb-10 border-t border-grey-200 pt-8 flex justify-between items-center text-[10px] font-extrabold uppercase tracking-widest text-grey-300">
        <div>&copy; 2026 FINADVISOR</div>
      </footer>
    </div>
  );
}

export default App;
