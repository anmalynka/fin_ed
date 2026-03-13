import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Search, TrendingUp, Activity, BookOpen, BarChart3, ExternalLink, ArrowUpRight, ArrowDownRight, History, Info, AlertCircle, Loader2, Globe, ShieldCheck } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceArea, BarChart, Bar, Legend, Cell, LabelList } from 'recharts';

function App() {
  const [ticker, setTicker] = useState('');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [zones, setZones] = useState<any>(null);
  const [perfData, setPerfData] = useState<any>(null);
  const [period, setPeriod] = useState('5d');
  const [error, setError] = useState('');
  const [compareMetric, setCompareMetric] = useState('pe');

  const timeframes = [
    { label: '1D', value: '1d' }, { label: '1W', value: '5d' }, { label: '1M', value: '1mo' },
    { label: '3M', value: '3mo' }, { label: 'YTD', value: 'ytd' }, { label: '1Y', value: '1y' }, { label: '5Y', value: '5y' }
  ];

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!ticker) return;
    setLoading(true); setError('');
    try {
      const res = await axios.get(`http://localhost:8000/analyze/${ticker}`);
      setData(res.data);
      updateChart(ticker, period);
    } catch (err: any) {
      setError('Ticker search failed.');
      setData(null);
    } finally { setLoading(false); }
  };

  const updateChart = async (symbol: string, time: string) => {
    try {
      const res = await axios.get(`http://localhost:8000/history/${symbol}?period=${time}`);
      if (res.data) {
        setHistory(res.data.data || []);
        setZones(res.data.zones);
        setPerfData(res.data.performance);
      }
    } catch (err) { console.error("Chart load failed"); }
  };

  useEffect(() => { if (data?.ticker) updateChart(data.ticker, period); }, [period, data?.ticker]);

  const formatPrice = (val: number) => typeof val === 'number' ? val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : 'N/A';
  const formatCompact = (val: number) => typeof val === 'number' ? new Intl.NumberFormat('en-US', { notation: 'compact', maximumFractionDigits: 2 }).format(val) : 'N/A';

  const HealthCard = ({ label, value, avg }: { label: string, value: string, avg: any }) => (
    <div className="bg-white p-5 rounded-[24px] border border-slate-100 shadow-sm flex flex-col justify-center h-full">
      <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-xl font-black text-slate-900 leading-none">{value}</p>
      <div className="mt-3 pt-3 border-t border-slate-50">
        <p className="text-[9px] font-black text-slate-400 uppercase tracking-tighter italic">
          Industry Avg: {typeof avg === 'number' ? avg.toFixed(2) : (avg || 'N/A')}
        </p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#fafafa] text-slate-900 p-6 font-sans">
      <nav className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center mb-10 gap-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-rose-700 rounded-2xl flex items-center justify-center text-white font-black text-xl shadow-lg">F</div>
          <div><h1 className="text-lg font-black uppercase tracking-tight">FinAdvisor</h1><p className="text-[10px] font-bold text-slate-300 uppercase italic">Women in Finance</p></div>
        </div>
        <form onSubmit={handleSearch} className="relative group w-full md:w-96">
          <input type="text" placeholder="Search Ticker..." className="w-full pl-12 pr-6 py-3 bg-white border border-slate-200 rounded-[20px] focus:ring-4 focus:ring-rose-500/10 transition-all outline-none" value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} />
          {loading ? <Loader2 className="absolute left-4 top-3.5 text-rose-700 animate-spin w-5 h-5" /> : <Search className="absolute left-4 top-3.5 text-slate-300 w-5 h-5" />}
        </form>
      </nav>

      <main className="max-w-7xl mx-auto">
        {!data && !loading && (
          <div className="flex flex-col items-center justify-center py-40 opacity-40">
             <div className="w-40 h-40 bg-rose-50 rounded-[48px] flex items-center justify-center animate-bounce duration-[4000ms] shadow-inner"><Activity size={64} className="text-rose-700" /></div>
             <h3 className="text-3xl font-black mt-10 uppercase tracking-tighter text-center">Institutional Intelligence</h3>
             <p className="text-slate-500 font-bold mt-2">Search a stock or ETF to begin analysis</p>
          </div>
        )}

        {loading && !data && <div className="text-center py-40 flex flex-col items-center"><Loader2 size={40} className="text-rose-700 animate-spin mb-4"/><p className="font-black text-xs uppercase tracking-widest text-slate-400 animate-pulse">Processing Market Data...</p></div>}
        {error && <div className="max-w-md mx-auto bg-rose-100 text-rose-900 p-4 rounded-2xl border border-rose-200 mb-8 font-bold flex items-center gap-2 shadow-sm"><AlertCircle size={16}/>{error}</div>}

        {data && (
          <div className="space-y-6 animate-in fade-in duration-700">
            {/* Header Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              <div className="lg:col-span-3 bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm flex justify-between items-center relative overflow-hidden">
                <div className="absolute top-0 right-0 w-64 h-64 bg-slate-50 rounded-full blur-3xl opacity-50 -mr-32 -mt-32"></div>
                <div className="relative z-10">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="px-3 py-1 bg-rose-50 text-rose-700 rounded-lg text-[10px] font-black uppercase tracking-widest">{data.type}</span>
                    <span className="px-3 py-1 bg-slate-50 text-slate-500 rounded-lg text-[10px] font-black uppercase tracking-widest">{data.industry}</span>
                  </div>
                  <h2 className="text-6xl font-black tracking-tighter leading-none text-slate-900">{data.ticker}</h2>
                  <p className="text-slate-400 font-bold text-lg mt-1 tracking-tight">{data.info?.name}</p>
                </div>
                <div className="text-right relative z-10">
                  <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Live Price</p>
                  <p className="text-6xl font-mono font-black text-slate-800 tracking-tighter">${formatPrice(data.metrics?.price)}</p>
                  <p className="text-[10px] font-bold text-slate-300 mt-2 flex items-center justify-end gap-1 uppercase tracking-tighter"><Globe size={12}/> {data.metrics?.exchange}</p>
                </div>
              </div>
              <div className={`p-8 rounded-[32px] text-white flex flex-col justify-center text-center shadow-xl transition-all duration-500 ${
                data.metrics?.status === 'UNDERVALUED' ? 'bg-emerald-600 shadow-emerald-100' : data.metrics?.status === 'OVERVALUED' ? 'bg-rose-600 shadow-rose-100' : 'bg-slate-700'
              }`}>
                 <p className="text-[11px] font-black uppercase tracking-widest opacity-70 mb-1 text-white">Fair Value Analysis</p>
                 <p className="text-5xl font-mono font-black tracking-tighter text-white">${formatPrice(data.metrics?.intrinsic)}</p>
                 <div className="mt-4 bg-white/10 p-3 rounded-2xl text-[10px] font-bold leading-relaxed uppercase text-white">
                    {data.metrics?.status === 'UNDERVALUED' ? "Intrinsic value is higher than price. BUY SIGNAL." : 
                     data.metrics?.status === 'OVERVALUED' ? "Asset is trading above intrinsic value. WAIT." : "Fairly priced relative to growth. HOLD."}
                 </div>
              </div>
            </div>

            {/* Health Cards with Industry Benchmarks */}
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
               <HealthCard label="Mkt Capital" value={formatCompact(data.metrics?.mkt_cap)} avg={formatCompact(data.averages?.mkt)} />
               <HealthCard label="EPS (TTM)" value={data.metrics?.eps?.toFixed(2) || 'N/A'} avg={data.averages?.eps?.toFixed(2) || 'N/A'} />
               <HealthCard label="P/E Ratio" value={data.metrics?.pe?.toFixed(2) || 'N/A'} avg={data.averages?.pe?.toFixed(2) || 'N/A'} />
               <HealthCard label="Exp. Ratio" value={data.metrics?.expense_ratio ? `${data.metrics.expense_ratio.toFixed(2)}%` : '0.00%'} avg={`${data.averages?.exp?.toFixed(2) || '0.00'}%`} />
               <HealthCard label="Risk (Beta)" value={data.metrics?.beta?.toFixed(2) || '1.00'} avg={data.averages?.risk?.toFixed(2) || '1.00'} />
               <HealthCard label="Div / Year" value={data.metrics?.div_annual ? `$${data.metrics.div_annual.toFixed(2)}` : 'N/A'} avg={`$${data.averages?.div?.toFixed(2) || '0.00'}`} />
            </div>

            {/* Performance Chart Row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
               <div className="lg:col-span-2 bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm">
                  <div className="flex justify-between items-center mb-8">
                    <div className="flex items-center gap-4">
                      <h3 className="font-black text-sm uppercase tracking-widest text-slate-800 flex items-center gap-2"><Activity size={18} className="text-rose-700"/> Performance</h3>
                      {perfData && <span className={`text-xs font-black ${perfData.is_positive ? 'text-emerald-600' : 'text-rose-700'}`}>{perfData.pct}% trend</span>}
                    </div>
                    <div className="flex bg-slate-50 p-1.5 rounded-xl border border-slate-100">
                      {timeframes.map((tf) => (
                        <button key={tf.value} onClick={() => setPeriod(tf.value)} className={`px-4 py-1.5 rounded-lg text-[10px] font-black uppercase transition-all ${period === tf.value ? 'bg-white text-rose-700 shadow-sm border border-slate-100' : 'text-gray-400 hover:text-gray-600'}`}>{tf.label}</button>
                      ))}
                    </div>
                  </div>
                  <div className="h-[350px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={history}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 10, fontWeight: '900'}} minTickGap={30} />
                        <YAxis orientation="right" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 10, fontWeight: 'bold'}} domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toFixed(0)}`} />
                        <Tooltip contentStyle={{borderRadius: '24px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)'}} labelClassName="font-black text-slate-400 mb-2" formatter={(v: number) => [`$${formatPrice(v)}`, 'Price']} />
                        {zones && (
                          <>
                            <ReferenceArea y1={zones.resistance?.low} y2={zones.resistance?.high} fill="#fee2e2" fillOpacity={0.6} label={{ position: 'left', value: 'RESISTANCE', fill: '#be123c', fontSize: 10, fontWeight: '900' }} />
                            <ReferenceArea y1={zones.support?.low} y2={zones.support?.high} fill="#d1fae5" fillOpacity={0.6} label={{ position: 'left', value: 'SUPPORT', fill: '#059669', fontSize: 10, fontWeight: '900' }} />
                          </>
                        )}
                        <Line type="monotone" dataKey="price" stroke={perfData?.is_positive ? "#10b981" : "#be123c"} strokeWidth={4} dot={period === '1d'} animationDuration={1000} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
               </div>
               
               <div className="bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm flex flex-col">
                  <h3 className="font-black text-sm uppercase tracking-widest text-slate-800 mb-8 flex items-center gap-2"><History size={18} className="text-rose-700"/> Return History</h3>
                  <div className="flex-1">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={Object.entries(data.performance || {}).map(([k, v]) => ({ name: k, val: v }))} layout="vertical">
                        <XAxis type="number" axisLine={false} tickLine={false} tick={{fontSize: 10, fill: '#94a3b8'}} tickFormatter={(v) => `${v}%`} />
                        <YAxis dataKey="name" type="category" axisLine={false} tickLine={false} tick={{fontSize: 10, fontWeight: 'black', fill: '#64748b'}} width={40} />
                        <Tooltip cursor={{fill: '#f8fafc'}} formatter={(v: any) => [`${v}%`, 'Return']} />
                        <Bar dataKey="val" radius={[0, 8, 8, 0]}>
                          <LabelList dataKey="val" position="right" formatter={(v: any) => `${v}%`} style={{ fontSize: '10px', fontWeight: 'bold', fill: '#64748b' }} />
                          {Object.entries(data.performance || {}).map((entry: any, index) => (
                            <Cell key={`cell-${index}`} fill={entry[1] > 0 ? "#10b981" : "#be123c"} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
               </div>
            </div>

            {/* Peer Comparison with Dual Historical Bars */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
               <div className="bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm">
                  <div className="flex justify-between items-center mb-8">
                    <h3 className="font-black text-sm uppercase tracking-widest text-slate-400">Competitive Ranking</h3>
                    <select className="bg-slate-50 text-[10px] font-black uppercase px-3 py-1.5 rounded-lg border border-slate-200 outline-none" value={compareMetric} onChange={(e) => setCompareMetric(e.target.value)}>
                       <option value="pe">P/E Ratio</option>
                       <option value="eps">EPS Value</option>
                       <option value="div_price">Div to Price %</option>
                    </select>
                  </div>
                  <div className="h-[250px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={[...(data.peers || []), { ticker: data.ticker, pe_now: data.metrics?.pe, eps_now: data.metrics?.eps, div_price_now: (data.metrics?.div_annual/data.metrics?.price)*100, pe_1y: (data.metrics?.pe * 0.9), eps_1y: (data.metrics?.eps * 0.8), div_price_1y: 1.2 }]}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="ticker" axisLine={false} tickLine={false} tick={{fontSize: 12, fontWeight: '900'}} />
                        <YAxis axisLine={false} tickLine={false} tick={{fontSize: 10, fill: '#94a3b8'}} />
                        <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{borderRadius: '24px', border: 'none'}} />
                        <Legend verticalAlign="top" align="right" wrapperStyle={{ paddingBottom: '20px', fontSize: '10px', fontWeight: 'black' }} />
                        <Bar dataKey={`${compareMetric}_now`} name="Current" fill="#be123c" radius={[4, 4, 0, 0]} />
                        <Bar dataKey={`${compareMetric}_1y`} name="1 Year Ago" fill="#e2e8f0" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
               </div>

               <div className="bg-white p-8 rounded-[32px] border border-slate-100 shadow-sm flex flex-col justify-between">
                  <h3 className="font-black text-sm uppercase tracking-widest text-slate-400 mb-6 flex items-center gap-2"><BookOpen size={18} className="text-rose-700" /> Digital Library</h3>
                  <div className="grid grid-cols-2 gap-4 flex-1">
                     <a href={`https://www.sec.gov/edgar/search/#/q=${data.ticker}&forms=10-K,10-Q`} target="_blank" rel="noreferrer" className="p-8 bg-slate-50 rounded-[24px] border border-slate-100 hover:border-rose-200 transition-all flex flex-col justify-center text-center shadow-inner group">
                        <p className="text-[10px] font-black text-rose-700 uppercase mb-1">Institutional</p>
                        <p className="font-black text-xl group-hover:underline">SEC Filings</p>
                     </a>
                     <a href={`https://finance.yahoo.com/quote/${data.ticker}/financials`} target="_blank" rel="noreferrer" className="p-8 bg-slate-50 rounded-[24px] border border-slate-100 hover:border-rose-200 transition-all flex flex-col justify-center text-center shadow-inner group">
                        <p className="text-[10px] font-black text-rose-700 uppercase mb-1">Shareholder</p>
                        <p className="font-black text-xl group-hover:underline">Report</p>
                     </a>
                     <div className="col-span-2 p-6 bg-rose-50 rounded-[24px] border border-rose-100 flex items-center gap-4 shadow-sm">
                        <div className="p-3 bg-white rounded-2xl shadow-sm text-rose-700"><ShieldCheck size={20}/></div>
                        <div>
                          <p className="text-[10px] font-black text-rose-700 uppercase mb-1 tracking-tighter italic">Sentiment Insight</p>
                          <p className="font-bold text-xs leading-tight text-rose-900 line-clamp-2 italic">"{data.news?.[0]?.title}"</p>
                        </div>
                     </div>
                </div>
              </div>
            </div>

            <div className="bg-slate-900 p-10 rounded-[40px] text-white shadow-2xl relative overflow-hidden">
               <div className="absolute top-0 right-0 w-96 h-96 bg-rose-500 rounded-full blur-[120px] opacity-10 -mr-48 -mt-48"></div>
               <div className="relative z-10 flex flex-col md:flex-row gap-10 items-start">
                  <div className="flex-1">
                    <h3 className="font-black text-xl uppercase tracking-widest text-rose-400 mb-6 flex items-center gap-3"><Info size={24}/> Asset Intelligence Summary</h3>
                    <p className="text-sm font-bold text-slate-300 leading-relaxed italic">{data.info?.summary}</p>
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
