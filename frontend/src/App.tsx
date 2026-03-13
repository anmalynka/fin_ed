import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, TrendingUp, Activity, BookOpen, BarChart3, ExternalLink, ArrowUpRight, ArrowDownRight, History, Info, Sparkles, AlertCircle, Loader2 } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea, BarChart, Bar, Legend } from 'recharts';

function App() {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [zones, setZones] = useState<any>(null);
  const [perf, setPerf] = useState<any>(null);
  const [period, setPeriod] = useState('5d'); // Default to 1 week (5 trading days)
  const [error, setError] = useState('');

  const timeframes = [
    { label: '1D', value: '1d' }, { label: '1W', value: '5d' }, { label: '1M', value: '1mo' },
    { label: '3M', value: '3mo' }, { label: 'YTD', value: 'ytd' }, { label: '1Y', value: '1y' }, { label: '5Y', value: '5y' }
  ];

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!ticker) return;
    
    setLoading(true);
    setError('');
    
    try {
      // 1. Fetch Core Metrics
      const res = await axios.get(`http://localhost:8000/analyze/${ticker}`);
      setData(res.data);
      
      // 2. Fetch Chart Data for the current period
      await updateChartData(ticker, period);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ticker not found or network error.');
      setData(null);
    } finally {
      setLoading(false);
    }
  };

  const updateChartData = async (symbol: string, time: string) => {
    try {
      const histRes = await axios.get(`http://localhost:8000/history/${symbol}?period=${time}`);
      if (histRes.data) {
        setHistory(histRes.data.data || []);
        setZones(histRes.data.zones);
        setPerf(histRes.data.performance);
      }
    } catch (err) {
      console.error("Chart data failed to load", err);
    }
  };

  // Update chart when period changes
  useEffect(() => {
    if (data?.ticker) {
      updateChartData(data.ticker, period);
    }
  }, [period]);

  const formatPrice = (val: number) => val ? val.toLocaleString(undefined, { minimumFractionDigits: 3, maximumFractionDigits: 3 }) : 'N/A';
  const formatCompact = (val: number) => val ? new Intl.NumberFormat('en-US', { notation: 'compact' }).format(val) : 'N/A';

  return (
    <div className="min-h-screen bg-[#fafafa] text-slate-900 p-6 font-sans">
      <nav className="max-w-7xl mx-auto flex justify-between items-center mb-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-rose-700 rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-lg">F</div>
          <h1 className="text-xl font-black uppercase tracking-tight">FinAdvisor</h1>
        </div>
        <form onSubmit={handleSearch} className="relative group">
          <input
            type="text" placeholder="Search Ticker (NVDA, TSLA, AAPL)"
            className="pl-12 pr-6 py-3 bg-white border border-slate-200 rounded-[20px] w-96 focus:ring-4 focus:ring-rose-500/10 transition-all outline-none shadow-sm font-medium"
            value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())}
          />
          {loading ? (
            <Loader2 className="absolute left-4 top-3.5 text-rose-700 animate-spin w-5 h-5" />
          ) : (
            <Search className="absolute left-4 top-3.5 text-slate-300 w-5 h-5 group-focus-within:text-rose-700 transition-colors" />
          )}
        </form>
      </nav>

      <main className="max-w-7xl mx-auto">
        {!data && !loading && (
          <div className="flex flex-col items-center justify-center py-40 opacity-40">
             <div className="w-40 h-40 bg-rose-50 rounded-[48px] flex items-center justify-center animate-bounce duration-[4000ms] shadow-inner"><Activity size={64} className="text-rose-700" /></div>
             <h3 className="text-3xl font-black mt-10 uppercase tracking-tighter">Institutional Intelligence</h3>
             <p className="text-slate-500 font-bold mt-2 italic">Enter a ticker to start analysis</p>
          </div>
        )}

        {loading && !data && (
          <div className="flex flex-col items-center justify-center py-40 space-y-4">
            <Loader2 className="w-12 h-12 text-rose-700 animate-spin" />
            <p className="font-black text-xs uppercase tracking-widest text-slate-400 animate-pulse">Processing Market Data...</p>
          </div>
        )}

        {error && <div className="max-w-md mx-auto bg-rose-100 text-rose-900 p-4 rounded-2xl border border-rose-200 mb-8 font-bold flex items-center gap-2 shadow-sm"><AlertCircle size={16}/>{error}</div>}

        {data && (
          <div className="space-y-8 animate-in fade-in duration-700">
            {/* Summary Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-3 bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm flex justify-between items-center relative overflow-hidden">
                <div className="relative z-10">
                  <h2 className="text-6xl font-black tracking-tighter">{data.ticker}</h2>
                  <p className="text-slate-400 font-bold text-lg uppercase mt-1 tracking-widest">{data.info.name}</p>
                  <div className="flex gap-2 mt-4">
                    <span className="px-4 py-1.5 bg-slate-50 text-slate-500 rounded-xl text-[10px] font-black uppercase tracking-widest">{data.info.industry}</span>
                    <span className="px-4 py-1.5 bg-rose-50 text-rose-700 rounded-xl text-[10px] font-black uppercase tracking-widest">MCap: {formatCompact(data.metrics.current.mkt_cap)}</span>
                  </div>
                </div>
                <div className="text-right relative z-10">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest">Live Price</p>
                  <p className="text-6xl font-mono font-black text-slate-800 tracking-tighter">${formatPrice(data.metrics.current.price)}</p>
                </div>
              </div>
              <div className={`p-10 rounded-[40px] text-white flex flex-col justify-center text-center shadow-xl transition-colors duration-500 ${data.metrics.is_undervalued ? 'bg-emerald-600 shadow-emerald-100' : 'bg-rose-600 shadow-rose-100'}`}>
                 <p className="text-[11px] font-black uppercase tracking-widest opacity-70 mb-1">Fair Value Estimate</p>
                 <p className="text-5xl font-mono font-black tracking-tighter">${formatPrice(data.metrics.intrinsic_price || data.metrics.current.price)}</p>
                 <p className="text-[10px] font-black uppercase mt-4 tracking-tight px-4 py-2 bg-white/10 rounded-2xl">{data.metrics.is_undervalued ? 'BUY SIGNAL' : 'NEUTRAL / HIGH'}</p>
              </div>
            </div>

            {/* Main Graph Card */}
            <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm">
               <div className="flex flex-col md:flex-row justify-between items-center mb-10 gap-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-rose-50 rounded-2xl text-rose-700 shadow-sm"><Activity size={24} /></div>
                    <div>
                      <h3 className="font-black text-2xl tracking-tight uppercase text-slate-800">Market Sentiment Zones</h3>
                      {perf && (
                        <div className={`flex items-center gap-2 text-xs font-black mt-1 ${perf.is_positive ? 'text-emerald-600' : 'text-rose-700'}`}>
                           {perf.is_positive ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                           {perf.change_pct.toFixed(2)}% <span className="text-slate-300 ml-1 font-bold italic lowercase">for this period</span>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex bg-slate-50 p-2 rounded-2xl border border-slate-100 items-center">
                    {timeframes.map((tf) => (
                      <button key={tf.value} onClick={() => setPeriod(tf.value)} className={`px-5 py-2 rounded-xl text-xs font-black uppercase transition-all ${period === tf.value ? 'bg-white text-rose-700 shadow-sm border border-slate-100' : 'text-gray-400 hover:text-gray-600'}`}>{tf.label}</button>
                    ))}
                  </div>
               </div>
               <div className="h-[450px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={history}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" hide />
                    <YAxis orientation="right" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 10, fontWeight: 'bold'}} domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                    <Tooltip contentStyle={{borderRadius: '24px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}} labelClassName="font-black text-slate-400 mb-2" formatter={(v: number) => [`$${formatPrice(v)}`, 'Price']} />
                    
                    {zones && (
                      <>
                        <ReferenceArea y1={zones.resistance.low} y2={zones.resistance.high} fill="#fee2e2" fillOpacity={0.6} label={{ position: 'left', value: 'RESISTANCE', fill: '#be123c', fontSize: 10, fontWeight: '900' }} />
                        <ReferenceArea y1={zones.support.low} y2={zones.support.high} fill="#d1fae5" fillOpacity={0.6} label={{ position: 'left', value: 'SUPPORT', fill: '#059669', fontSize: 10, fontWeight: '900' }} />
                      </>
                    )}
                    
                    <Line 
                      type="monotone" 
                      dataKey="price" 
                      stroke={perf?.is_positive ? "#10b981" : "#be123c"} 
                      strokeWidth={4} 
                      dot={false} 
                      animationDuration={1000} 
                    />
                  </LineChart>
                </ResponsiveContainer>
               </div>
            </div>

            {/* Metrics & Comparison Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm">
                 <h3 className="font-black text-xl tracking-tight mb-8 text-slate-400 uppercase flex items-center gap-3"><BarChart3 size={20} className="text-rose-700" /> Peer Rank Analysis</h3>
                 <div className="h-[300px]">
                   <ResponsiveContainer width="100%" height="100%">
                     <BarChart data={[...data.comparison, { ticker: data.ticker, pe: data.metrics.current.pe, eps: data.metrics.current.eps }]}>
                       <XAxis dataKey="ticker" axisLine={false} tickLine={false} tick={{fontSize: 12, fontWeight: '900'}} />
                       <YAxis axisLine={false} tickLine={false} tick={{fontSize: 10}} />
                       <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{borderRadius: '24px', border: 'none'}} />
                       <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '20px', fontSize: '10px', fontWeight: '900' }} />
                       <Bar dataKey="pe" name="P/E Ratio" fill="#f43f5e" radius={[8, 8, 0, 0]} />
                       <Bar dataKey="eps" name="EPS" fill="#94a3b8" radius={[8, 8, 0, 0]} />
                     </BarChart>
                   </ResponsiveContainer>
                 </div>
              </div>
              
              <div className="bg-white p-10 rounded-[40px] border border-slate-100 shadow-sm space-y-8 flex flex-col justify-center">
                <h3 className="font-black text-xl tracking-tight text-slate-400 uppercase flex items-center gap-3"><TrendingUp size={20} className="text-rose-700" /> Key Health Metrics</h3>
                <div className="grid grid-cols-2 gap-6">
                   <div className="p-8 bg-slate-50 rounded-3xl border border-slate-100 shadow-inner">
                      <p className="text-[10px] font-black text-slate-400 uppercase mb-1">P/E Ratio</p>
                      <p className="text-4xl font-black text-slate-800">{data.metrics.current.pe?.toFixed(2) || 'N/A'}</p>
                      <p className="text-[9px] font-bold text-slate-300 mt-2 uppercase tracking-tighter italic">Price to Earnings</p>
                   </div>
                   <div className="p-8 bg-slate-50 rounded-3xl border border-slate-100 shadow-inner">
                      <p className="text-[10px] font-black text-slate-400 uppercase mb-1">EPS (TTM)</p>
                      <p className="text-4xl font-black text-slate-800">{data.metrics.current.eps?.toFixed(2) || 'N/A'}</p>
                      <p className="text-[9px] font-bold text-slate-300 mt-2 uppercase tracking-tighter italic">Earnings Per Share</p>
                   </div>
                </div>
                <div className="bg-rose-50 p-6 rounded-3xl border border-rose-100">
                   <p className="text-[10px] font-black text-rose-700 uppercase mb-2">Market Insight</p>
                   <p className="font-bold text-sm leading-tight text-rose-900 line-clamp-2 italic">"{data.news[0]?.title}"</p>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
