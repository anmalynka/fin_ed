import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, Activity, History, Info, Loader2, BookOpen, ShieldCheck, ListOrdered } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, Cell, LabelList } from 'recharts';

import logoImg from './assets/FA_logo.png';

function App() {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [perfData, setPerfData] = useState<any>(null);
  const [forecastData, setForecastData] = useState<any[]>([]);
  const [period, setPeriod] = useState('5d');
  const [mode, setMode] = useState('perf');
  const [errorMessage, setErrorMessage] = useState('');

  const timeframes = [
    { label: '1D', value: '1d' }, { label: '1W', value: '5d' }, { label: '1M', value: '1mo' },
    { label: '3M', value: '3mo' }, { label: 'YTD', value: 'ytd' }, { label: '1Y', value: '1y' }, { label: '5Y', value: '5y' }
  ];

  const API_BASE = window.location.hostname === 'localhost' 
    ? 'http://localhost:8000/api'
    : window.location.hostname.includes('fin-advisor-ui')
      ? 'https://fin-ed.onrender.com/api' 
      : '/api';

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

  const updateChart = async (symbol: string, time: string) => {
    try {
      const res = await axios.get(`${API_BASE}/history/${symbol}?period=${time}`);
      if (res.data) {
        setHistory(res.data.data || []);
        setPerfData(res.data.performance);
      }
    } catch (err) { console.error("Chart load failed"); }
  };

  useEffect(() => { if (data?.ticker && mode === 'perf') updateChart(data.ticker, period); }, [period]);

  const formatPrice = (val: number) => typeof val === 'number' ? val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : 'N/A';
  const formatCompact = (val: number) => typeof val === 'number' ? new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(val) : 'N/A';

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

  return (
    <div className="min-h-screen bg-secondary text-grey-500 p-6 font-sans">
      <nav className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center mb-10 gap-8">
        <div className="flex items-center gap-3">
          <img src={logoImg} alt="FinAdvisor Logo" className="w-10 h-10 object-contain rounded-m border-2 border-tertiary shadow-[2px_2px_0px_0px_#15191d]" />
          <div><h1 className="text-lg font-extrabold uppercase tracking-tight text-tertiary">FinAdvisor</h1><p className="text-[10px] font-bold text-grey-300 uppercase italic mt-1 leading-none">Institutional Intelligence</p></div>
        </div>
        <form onSubmit={handleSearch} className="relative group w-full md:w-96">
          <input type="text" placeholder="Search Ticker..." className="w-full pl-12 pr-6 py-[17px] bg-white border border-[#6b7280] rounded-m focus:ring-4 focus:ring-primary/20 outline-none transition-all font-bold text-[16px] text-tertiary placeholder:text-[#cbd5e1]" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
          {loading ? <Loader2 className="absolute left-4 top-[18px] text-primary animate-spin w-5 h-5" /> : <Search className="absolute left-4 top-[18px] text-grey-300 w-5 h-5" />}
        </form>
      </nav>

      <main className="max-w-7xl mx-auto">
        {!data && !loading && !errorMessage && <EmptyState />}
        {errorMessage && <NotFoundState />}
        
        {data && (
          <div className="space-y-6 animate-in fade-in duration-700">
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className={`${data.type === 'ETF' ? 'lg:col-span-4' : 'lg:col-span-3'} bg-white p-8 rounded-m border border-grey-200 shadow-sm flex justify-between items-center relative overflow-hidden`}>
                <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl opacity-50 -mr-32 -mt-32"></div>
                <div className="relative z-10">
                  <div className="flex gap-2 mb-2">
                    <span className="px-3 py-1 bg-primary/20 text-tertiary border border-tertiary/10 rounded-m text-[10px] font-extrabold uppercase tracking-widest">{data.type}</span>
                    <span className="px-3 py-1 bg-secondary text-grey-300 border border-tertiary/10 rounded-m text-[10px] font-extrabold uppercase tracking-widest">{data.industry}</span>
                  </div>
                  <h2 className="text-6xl font-extrabold tracking-tighter leading-none text-tertiary">{data.ticker}</h2>
                  <p className="text-grey-300 font-bold text-lg mt-1 tracking-tight">{data.info?.name}</p>
                </div>
                <div className="text-right relative z-10">
                  <p className="text-[10px] font-bold text-grey-300 uppercase tracking-widest mb-1 text-right">Live Price</p>
                  <p className="text-6xl font-mono font-extrabold text-tertiary tracking-tighter">${formatPrice(data.metrics?.price)}</p>
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
                                `Undervalued by ${Math.abs(((data.metrics.intrinsic - data.metrics.price)/data.metrics.price)*100).toFixed(1)}%` : 
                                `Overvalued by ${Math.abs(((data.metrics.intrinsic - data.metrics.price)/data.metrics.price)*100).toFixed(1)}%`
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
               <div className="bg-[#efe9e980] content-stretch flex items-center justify-center p-[4px] relative rounded-m w-[342px] border border-grey-200">
                  <button onClick={() => setMode('perf')} className={`content-stretch flex flex-1 flex-col items-center justify-center px-4 py-2 relative rounded-m text-[12px] font-bold tracking-widest uppercase transition-all ${mode === 'perf' ? 'bg-white shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] text-tertiary border border-grey-100' : 'text-blue-400'}`}>Performance</button>
                  <button onClick={() => setMode('forecast')} className={`content-stretch flex flex-1 flex-col items-center justify-center px-4 py-2 relative rounded-m text-[12px] font-bold tracking-widest uppercase transition-all ${mode === 'forecast' ? 'bg-white shadow-[0px_1px_2px_0px_rgba(0,0,0,0.05)] text-tertiary border border-grey-100' : 'text-blue-400'}`}>AI Forecast</button>
               </div>
            </div>

            <div className="bg-white p-10 rounded-m border border-grey-200 shadow-sm">
               <div className="flex flex-col md:flex-row justify-between items-center mb-10 gap-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-secondary border border-grey-100 rounded-m"><Activity size={24} className="text-tertiary" /></div>
                    <div>
                      <h3 className="font-extrabold text-2xl tracking-tight uppercase text-tertiary">
                        {mode === 'perf' ? 'Performance' : 'AI FINANCIAL FORECAST'}
                      </h3>
                      {perfData && mode === 'perf' && <span className={`text-xs font-extrabold ${perfData.is_positive ? 'text-[#1E8257]' : 'text-[#A45951]'}`}>{perfData.pct}% trend</span>}
                    </div>
                  </div>

                  {mode === 'perf' ? (
                    <div className="flex bg-secondary p-1.5 rounded-m border border-grey-100">
                      {timeframes.map((tf) => (
                        <button key={tf.value} onClick={() => setPeriod(tf.value)} className={`px-4 py-1.5 rounded-m text-[10px] font-extrabold uppercase transition-all ${period === tf.value ? 'bg-white border border-grey-200 text-tertiary shadow-[1px_1px_0px_0px_#15191d]' : 'text-grey-300 hover:text-grey-500'}`}>{tf.label}</button>
                      ))}
                    </div>
                  ) : (
                    <div className="flex gap-6 text-[10px] font-extrabold uppercase tracking-widest text-grey-300">
                      <span className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#52525b]"></div> History</span>
                      <span className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#99b6d6]"></div> AI Hybrid</span>
                      <span className="flex items-center gap-2"><div className="w-3 h-3 rounded-full bg-[#0f172a]"></div> Baseline</span>
                    </div>
                  )}
               </div>
               
               <div className="h-[450px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  {mode === 'perf' ? (
                    <LineChart data={history}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: '900'}} minTickGap={30} />
                      <YAxis orientation="right" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                      <Tooltip contentStyle={{borderRadius: '12px', border: '2px solid #0f172a', boxShadow: '4px 4px 0px 0px #0f172a'}} labelClassName="font-extrabold text-grey-300 mb-2" />
                      <Line type="monotone" dataKey="price" stroke={perfData?.is_positive ? "#1E8257" : "#A45951"} strokeWidth={4} dot={false} animationDuration={1000} />
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
                  <div className="grid grid-cols-2 gap-4 h-full">
                     <a href={`https://www.sec.gov/edgar/search/#/q=${data.ticker}&forms=10-K,10-Q`} target="_blank" rel="noreferrer" className="p-8 bg-primary border-2 border-tertiary rounded-m flex flex-col justify-center text-center shadow-[4px_4px_0px_0px_#15191d] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] group transition-all">
                        <p className="text-[10px] font-extrabold text-tertiary uppercase mb-1 opacity-70">Institutional</p>
                        <p className="font-extrabold text-xl group-hover:underline text-tertiary uppercase">SEC Filings</p>
                     </a>
                     <a href={`https://finance.yahoo.com/quote/${data.ticker}/financials`} target="_blank" rel="noreferrer" className="p-8 bg-primary border-2 border-tertiary rounded-m flex flex-col justify-center text-center shadow-[4px_4px_0px_0px_#15191d] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] group transition-all">
                        <p className="text-[10px] font-extrabold text-tertiary uppercase mb-1 opacity-70">Shareholder</p>
                        <p className="font-extrabold text-xl group-hover:underline text-tertiary uppercase">Report</p>
                     </a>
                     <div className="col-span-2 p-6 bg-[#efe9e9] rounded-m border border-grey-200 flex items-center gap-4 shadow-sm">
                        <div className="p-3 bg-white border border-tertiary rounded-m shadow-[1px_1px_0px_0px_#15191d] text-tertiary"><ShieldCheck size={20}/></div>
                        <div>
                          <p className="text-[10px] font-extrabold text-tertiary uppercase mb-1 italic">Market Insight</p>
                          <p className="font-bold text-xs leading-tight text-tertiary line-clamp-2 italic">"{data.news?.[0]?.title}"</p>
                        </div>
                     </div>
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
      </main>
      
      <footer className="max-w-7xl mx-auto mt-12 pb-10 border-t border-grey-200 pt-8 flex justify-between items-center text-[10px] font-extrabold uppercase tracking-widest text-grey-300">
        <div>&copy; 2026 FINADVISOR</div>
      </footer>
    </div>
  );
}

export default App;
