import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Trash2, PieChart, TrendingUp, DollarSign, 
  Loader2, AlertCircle, ExternalLink, X, ShieldCheck, ChevronDown
} from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
  BarChart, Bar, Treemap, ResponsiveContainer as RespCont, Cell, ReferenceArea
} from 'recharts';

interface Position {
  ticker: string;
  avg_price: number;
  shares: number;
  category: string;
}

interface AnalysisResult {
  positions: any[];
  portfolio: {
    total_cost: number;
    total_value: number;
    total_delta: number;
    total_delta_pct: number;
    total_day_delta: number;
    total_day_delta_pct: number;
    total_div: number;
    div_score: number;
    alerts: string[];
    category_distribution: any[];
    sector_distribution: any[];
    dividend_distribution: any[];
    sparkline: number[];
  };
}

interface PositionsPageProps {
  apiBase: string;
  onViewTicker: (ticker: string) => void;
}

const PositionsPage: React.FC<PositionsPageProps> = ({ apiBase, onViewTicker }) => {
  const [positions, setPositions] = useState<Position[]>(() => {
    const saved = localStorage.getItem('fin_advisor_positions');
    return saved ? JSON.parse(saved) : [];
  });
  
  const [newPos, setNewPos] = useState({ ticker: '', avg_price: '', shares: '', category: 'Growth' });
  const [isValidating, setIsValidating] = useState(false);
  const [validationError, setValidationError] = useState('');
  const [validatedData, setValidatedData] = useState<any>(null);
  
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Chart States
  const [period, setPeriod] = useState('1y');
  const [indicators, setIndicators] = useState<string[]>([]);
  const [showIndicators, setShowIndicators] = useState(false);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [perfData, setPerfData] = useState<any>(null);
  const [chartLoading, setChartLoading] = useState(false);

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

  useEffect(() => {
    localStorage.setItem('fin_advisor_positions', JSON.stringify(positions));
    if (positions.length > 0) {
      fetchAnalysis();
    } else {
      setAnalysis(null);
      setHistoryData([]);
    }
  }, [positions]);

  useEffect(() => {
    if (positions.length > 0) {
      fetchPortfolioHistory();
    }
  }, [period, indicators, positions.length]);

  // Real-time validation
  useEffect(() => {
    const timer = setTimeout(async () => {
      if (newPos.ticker.length >= 2) {
        setIsValidating(true);
        setValidationError('');
        try {
          const res = await axios.get(`${apiBase}/validate/${newPos.ticker}`);
          if (res.data.valid) {
            setValidatedData(res.data);
          } else {
            setValidationError('Invalid ticker');
            setValidatedData(null);
          }
        } catch (err) {
          setValidationError('Validation failed');
        } finally {
          setIsValidating(false);
        }
      } else {
        setValidatedData(null);
        setValidationError('');
      }
    }, 600);
    return () => clearTimeout(timer);
  }, [newPos.ticker]);

  const fetchAnalysis = async () => {
    try {
      const res = await axios.post(`${apiBase}/positions/analyze`, positions);
      if (res.data) {
        setAnalysis(res.data);
      }
    } catch (err: any) {
      console.error('Portfolio analysis failed', err);
    }
  };

  const fetchPortfolioHistory = async () => {
    setChartLoading(true);
    try {
      const indsParam = indicators.length > 0 ? `&indicators=${indicators.join(',')}` : '';
      const res = await axios.post(`${apiBase}/portfolio/history?period=${period}${indsParam}`, positions);
      if (res.data) {
        setHistoryData(res.data.data || []);
        setPerfData(res.data.performance);
      }
    } catch (err) {
      console.error("Portfolio history failed");
    } finally {
      setChartLoading(false);
    }
  };

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPos.ticker || !newPos.avg_price || !newPos.shares || !validatedData) return;
    const p: Position = {
      ticker: newPos.ticker.toUpperCase().trim(),
      avg_price: parseFloat(newPos.avg_price),
      shares: parseFloat(newPos.shares),
      category: newPos.category
    };
    setPositions([...positions, p]);
    setNewPos({ ticker: '', avg_price: '', shares: '', category: 'Growth' });
    setValidatedData(null);
    setIsModalOpen(false);
  };

  const handleDelete = (index: number) => {
    const next = [...positions];
    next.splice(index, 1);
    setPositions(next);
  };

  const formatPrice = (val: number | null | undefined) => 
    (val !== null && val !== undefined) 
      ? val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) 
      : '0.00';
      
  const formatPct = (val: number | null | undefined) => 
    (val !== null && val !== undefined) 
      ? (val >= 0 ? '+' : '') + val.toFixed(2) + '%'
      : '0.00%';

  const renderSparkline = (data: number[]) => {
    if (!data || data.length < 2) return "Stable";
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min;
    const blocks = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
    return data.map(v => {
      const idx = range === 0 ? 0 : Math.floor(((v - min) / range) * 7);
      return blocks[idx];
    }).join('');
  };

  const renderAllocationBar = () => {
    if (!analysis || !analysis.portfolio.category_distribution || analysis.portfolio.category_distribution.length === 0) return null;
    const cats = analysis.portfolio.category_distribution;
    const total = analysis.portfolio.total_value || 1;
    const colors = ['bg-[#365477]', 'bg-[#D0BB78]', 'bg-[#502068]', 'bg-[#1E8257]', 'bg-[#A45951]'];
    
    return (
      <div className="space-y-2">
        <div className="flex h-4 w-full bg-secondary rounded-full overflow-hidden border border-tertiary/10">
          {cats.map((c, i) => (
            <div 
              key={c.name} 
              style={{ width: `${(c.value / total) * 100}%` }}
              className={`${colors[i % colors.length]} h-full`}
            />
          ))}
        </div>
        <div className="flex flex-wrap gap-4 text-[10px] font-black uppercase">
          {cats.map((c, i) => (
            <span key={c.name} className="flex items-center gap-1.5">
              <div className={`w-2 h-2 rounded-full ${colors[i % colors.length]}`}></div>
              {c.name}: {((c.value / total) * 100).toFixed(0)}%
            </span>
          ))}
        </div>
      </div>
    );
  };

  const sectorColors = ['#365477', '#D0BB78', '#502068', '#1E8257', '#A45951', '#738291', '#4a4e69', '#9a8c98'];

  const CustomTreemapContent = (props: any) => {
    const { x, y, width, height, name, index } = props;
    if (width < 40 || height < 20) return null;
    return (
      <g>
        <rect x={x} y={y} width={width} height={height} style={{ fill: sectorColors[index % sectorColors.length], stroke: '#fff', strokeWidth: 2 }} />
        <text x={x + width / 2} y={y + height / 2} textAnchor="middle" fill="#fff" fontSize={10} fontWeight="bold" className="uppercase">{name}</text>
      </g>
    );
  };

  const KPICard = ({ label, value, sub, isPos }: { label: string, value: string, sub?: string, isPos?: boolean }) => (
    <div className="bg-white p-6 rounded-m border-2 border-tertiary shadow-[4px_4px_0px_0px_#15191d]">
      <p className="text-[10px] font-black text-grey-300 uppercase tracking-widest mb-1">{label}</p>
      <p className="text-2xl font-black text-tertiary tracking-tight leading-none mb-2">{value}</p>
      {sub && <p className={`text-[10px] font-bold uppercase ${isPos ? 'text-[#1E8257]' : 'text-[#A45951]'}`}>{sub}</p>}
    </div>
  );

  const ReturnCell = ({ val }: { val: number }) => (
    <td className={`px-4 py-4 text-[10px] font-black text-center border-x border-grey-50 ${
      val > 0 ? 'text-[#1E8257]' : val < 0 ? 'text-[#A45951]' : 'text-grey-300'
    }`}>
      {val !== 0 ? (val > 0 ? '+' : '') + val.toFixed(1) + '%' : '-'}
    </td>
  );

  return (
    <div className="space-y-8 animate-in fade-in duration-700">
      {/* Portfolio Header KPIs */}
      {analysis && positions.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <KPICard label="Total Market Value" value={`$${formatPrice(analysis.portfolio.total_value)}`} sub={`XIRR: ~${(analysis.portfolio.total_delta_pct || 0).toFixed(1)}%`} isPos={analysis.portfolio.total_delta >= 0} />
          <KPICard label="Day Change" value={`${(analysis.portfolio.total_day_delta || 0) >= 0 ? '+' : ''}$${formatPrice(analysis.portfolio.total_day_delta)}`} sub={formatPct(analysis.portfolio.total_day_delta_pct)} isPos={analysis.portfolio.total_day_delta >= 0} />
          <KPICard label="Total P/L" value={`${(analysis.portfolio.total_delta || 0) >= 0 ? '+' : ''}$${formatPrice(analysis.portfolio.total_delta)}`} sub={formatPct(analysis.portfolio.total_delta_pct)} isPos={analysis.portfolio.total_delta >= 0} />
          <div className="bg-white p-6 rounded-m border-2 border-tertiary shadow-[4px_4px_0px_0px_#15191d] flex flex-col justify-between">
            <p className="text-[10px] font-black text-grey-300 uppercase tracking-widest mb-1">Diversification Score</p>
            <div className="flex items-center gap-3">
              <span className="text-3xl font-black text-tertiary">{analysis.portfolio.div_score || 0}</span>
              <div className="h-2 flex-grow bg-secondary rounded-full overflow-hidden">
                <div className="h-full bg-[#1E8257]" style={{ width: `${analysis.portfolio.div_score || 0}%` }}></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Risk Row */}
      {analysis && positions.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-m border border-grey-200">
            <h4 className="text-[10px] font-black uppercase text-grey-300 tracking-widest mb-4 flex justify-between items-center">
              Allocation Bar 
              <span className="font-mono text-tertiary text-xs">30D Trend: {renderSparkline(analysis.portfolio.sparkline)}</span>
            </h4>
            {renderAllocationBar()}
          </div>
          
          <div className="bg-white p-6 rounded-m border border-grey-200">
            <h4 className="text-[10px] font-black uppercase text-grey-300 tracking-widest mb-4">Risk & Concentration</h4>
            <div className="space-y-3">
              {analysis.portfolio.alerts && analysis.portfolio.alerts.length > 0 ? (
                analysis.portfolio.alerts.map((alert, i) => (
                  <div key={i} className="flex items-center gap-2 p-3 bg-[#A45951]/10 border border-[#A45951]/20 rounded-m text-[#A45951] text-[10px] font-black uppercase">
                    <AlertCircle size={14} /> {alert}
                  </div>
                ))
              ) : (
                <div className="flex items-center gap-2 p-3 bg-[#1E8257]/10 border border-[#1E8257]/20 rounded-m text-[#1E8257] text-[10px] font-black uppercase">
                  <ShieldCheck size={14} /> Portfolio Well Diversified
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Assets Table */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h3 className="font-black text-lg text-tertiary uppercase tracking-tight">Assets</h3>
          <button 
            onClick={() => setIsModalOpen(true)}
            className="px-6 py-2.5 bg-tertiary text-white rounded-m text-[10px] font-black uppercase shadow-[3px_3px_0px_0px_#D0BB78] hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px] transition-all"
          >
            Add Position
          </button>
        </div>

        {analysis && (
          <div className="bg-white rounded-m border-2 border-tertiary shadow-[4px_4px_0px_0px_#15191d] overflow-hidden">
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left border-collapse min-w-[1600px]">
                <thead className="bg-secondary">
                  <tr className="text-[10px] font-black uppercase text-grey-300">
                    <th className="px-6 py-4 sticky left-0 bg-secondary z-10 border-r border-grey-200">Asset</th>
                    <th className="px-6 py-4 text-center">Shares</th>
                    <th className="px-6 py-4 text-center">Avg Price</th>
                    <th className="px-6 py-4 text-center">Current Price</th>
                    <th className="px-6 py-4 text-center">Spent (Cost)</th>
                    <th className="px-6 py-4 text-center">Worth (Now)</th>
                    <th className="px-6 py-4">Total Delta</th>
                    {['1D', '1W', '1M', '3M', 'YTD', '1Y', '3Y', '5Y'].map(tf => (
                      <th key={tf} className="px-4 py-4 text-center">{tf}</th>
                    ))}
                    <th className="px-6 py-4 text-center">Div Yield</th>
                    <th className="px-6 py-4 text-center">Annual Div</th>
                    <th className="px-6 py-4">Weight%</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-grey-100 font-mono text-[11px]">
                  {analysis.positions.sort((a,b) => b.value - a.value).map((pos, idx) => (
                    <tr key={idx} className="hover:bg-secondary/30 transition-colors group">
                      <td className="px-6 py-4 sticky left-0 bg-white group-hover:bg-[#f9fbfd] transition-colors z-10 border-r border-grey-50">
                        <button onClick={() => onViewTicker(pos.ticker)} className="flex flex-col items-start hover:translate-x-1 transition-transform">
                          <div className="font-black text-tertiary flex items-center gap-1 group-hover:text-primary transition-colors uppercase">
                            {pos.ticker} <ExternalLink size={10} className="opacity-0 group-hover:opacity-100" />
                          </div>
                          <div className="text-[8px] font-bold text-grey-300 uppercase truncate max-w-[120px]">{pos.name || 'Unknown'}</div>
                          <div className="text-[7px] text-grey-200 uppercase mt-0.5">{pos.category}</div>
                        </button>
                      </td>
                      <td className="px-6 py-4 text-center font-black text-tertiary">{pos.shares}</td>
                      <td className="px-6 py-4 text-center text-grey-300 font-bold">${formatPrice(pos.avg_price)}</td>
                      <td className="px-6 py-4 text-center font-black text-tertiary">${formatPrice(pos.current_price)}</td>
                      <td className="px-6 py-4 text-center text-grey-300 font-bold">${formatPrice(pos.cost)}</td>
                      <td className="px-6 py-4 text-center font-black text-tertiary">${formatPrice(pos.value)}</td>
                      <td className="px-6 py-4">
                        <div className={`font-black ${pos.delta >= 0 ? 'text-[#1E8257]' : 'text-[#A45951]'}`}>
                          {pos.delta >= 0 ? '+' : ''}${formatPrice(pos.delta)}
                        </div>
                        <div className={`text-[8px] font-black uppercase ${pos.delta >= 0 ? 'text-[#1E8257]' : 'text-[#A45951]'}`}>{formatPct(pos.delta_pct)}</div>
                      </td>
                      {['1D', '1W', '1M', '3M', 'YTD', '1Y', '3Y', '5Y'].map(tf => (
                        <ReturnCell key={tf} val={pos.returns?.[tf] || 0} />
                      ))}
                      <td className="px-6 py-4 text-center">
                        <div className="font-bold text-tertiary">{pos.div_yield?.toFixed(2) || '0.00'}%</div>
                      </td>
                      <td className="px-6 py-4 text-center">
                        <div className="font-bold text-[#1E8257]">${formatPrice(pos.div_annual_total)}</div>
                        <div className="text-[8px] font-black text-grey-300 uppercase italic">Rate: ${pos.div_rate?.toFixed(2) || '0.00'}</div>
                      </td>
                      <td className="px-6 py-4 font-black">{pos.weight_pct?.toFixed(1)}%</td>
                      <td className="px-6 py-4 text-right">
                        <button onClick={() => handleDelete(idx)} className="text-grey-200 hover:text-[#A45951] transition-colors"><Trash2 size={16}/></button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Analytics Charts */}
      {analysis && positions.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
          {/* Equity Curve with Controls */}
          <div className="bg-white p-8 rounded-m border border-grey-200 shadow-sm col-span-1 lg:col-span-2">
            <div className="flex flex-col lg:flex-row justify-between items-center mb-8 gap-6">
              <div className="flex items-center gap-4 self-start">
                <div className="p-3 bg-secondary border border-grey-100 rounded-m"><TrendingUp size={24} className="text-tertiary" /></div>
                <div>
                  <h3 className="font-black text-[10px] uppercase tracking-widest text-grey-300">Portfolio Performance</h3>
                  {perfData && <span className={`text-[10px] font-extrabold ${perfData.is_positive ? 'text-[#1E8257]' : 'text-[#A45951]'}`}>{perfData.pct}% trend</span>}
                </div>
              </div>

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
                          <span className="text-[10px] font-black uppercase">{opt.label}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className={`${indicators.some(i => ['rsi', 'macd'].includes(i)) ? 'h-[600px]' : 'h-[300px] md:h-[450px]'} w-full space-y-4`}>
              {chartLoading ? (
                <div className="h-full w-full flex items-center justify-center bg-secondary/20 rounded-m">
                  <Loader2 size={48} className="text-primary animate-spin" />
                </div>
              ) : (
                <>
                  <div className={indicators.some(i => ['rsi', 'macd'].includes(i)) ? 'h-[60%]' : 'h-full'}>
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={historyData} margin={{ left: -20, right: 0, top: 10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                        <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: '900'}} minTickGap={30} />
                        <YAxis orientation="right" axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} domain={['auto', 'auto']} tickFormatter={(v) => `$${v.toLocaleString()}`} />
                        <Tooltip 
                          contentStyle={{borderRadius: '12px', border: '2px solid #0f172a', boxShadow: '4px 4px 0px 0px #0f172a'}} 
                          labelClassName="font-extrabold text-grey-300 mb-2"
                          formatter={(v: any) => [typeof v === 'number' ? v.toFixed(2) : v, '']}
                        />
                        <Line type="monotone" dataKey="price" stroke={perfData?.is_positive ? "#1E8257" : "#A45951"} strokeWidth={4} dot={false} animationDuration={1000} />
                        {indicators.includes('sma20') && <Line name="SMA 20" type="monotone" dataKey="sma20" stroke="#D0BB78" strokeWidth={2} dot={false} connectNulls />}
                        {indicators.includes('sma50') && <Line name="SMA 50" type="monotone" dataKey="sma50" stroke="#365477" strokeWidth={2} dot={false} connectNulls />}
                        {indicators.includes('bollinger') && (
                          <>
                            <Line name="BB Upper" type="monotone" dataKey="bb_upper" stroke="#502068" strokeWidth={1} dot={false} connectNulls opacity={0.6} />
                            <Line name="BB Lower" type="monotone" dataKey="bb_lower" stroke="#502068" strokeWidth={1} dot={false} connectNulls opacity={0.6} />
                          </>
                        )}
                      </LineChart>
                    </ResponsiveContainer>
                  </div>

                  {indicators.includes('rsi') && (
                    <div className="h-[15%] w-full border-t border-grey-100 pt-2">
                      <p className="text-[8px] font-black uppercase text-grey-300 mb-1">RSI (14)</p>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={historyData} margin={{ left: -20, right: 0, top: 0, bottom: 0 }}>
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

                  {indicators.includes('macd') && (
                    <div className="h-[20%] w-full border-t border-grey-100 pt-2">
                      <p className="text-[8px] font-black uppercase text-grey-300 mb-1">MACD (12, 26, 9)</p>
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={historyData} margin={{ left: -20, right: 0, top: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                          <XAxis dataKey="date" hide />
                          <YAxis orientation="right" tick={{fontSize: 8}} />
                          <Bar dataKey="macd_hist" radius={[2, 2, 0, 0]}>
                            {historyData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={(entry?.macd_hist ?? 0) >= 0 ? "#1E8257" : "#A45951"} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
           
           <div className="bg-white p-8 rounded-m border border-grey-200 shadow-sm">
              <div className="flex justify-between items-center mb-8">
                <h3 className="font-black text-[10px] uppercase tracking-widest text-grey-300 flex items-center gap-2"><DollarSign size={18} className="text-[#1E8257]" /> Annual Dividends</h3>
                <div className="text-right">
                  <p className="text-[8px] font-black text-grey-300 uppercase">Est. Annual Total</p>
                  <p className="text-lg font-black text-[#1E8257]">${formatPrice(analysis?.portfolio.total_div)}</p>
                </div>
              </div>
              <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={analysis?.portfolio.dividend_distribution}>
                     <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                     <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fontSize: 10, fill: '#889099', fontWeight: 'bold'}} />
                     <YAxis orientation="right" axisLine={false} tickLine={false} tick={{fontSize: 10, fill: '#889099'}} />
                     <Tooltip cursor={{fill: '#f5f2ed'}} />
                     <Bar dataKey="div" fill="#1E8257" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
           </div>

           <div className="bg-white p-8 rounded-m border border-grey-200 shadow-sm">
              <h3 className="font-black text-[10px] uppercase tracking-widest text-grey-300 mb-8 flex items-center gap-2"><PieChart size={18} className="text-[#1E8257]" /> Sector Allocation</h3>
              <div className="h-[300px] w-full">
                <RespCont width="100%" height="100%">
                  <Treemap data={analysis?.portfolio.sector_distribution} dataKey="value" aspectRatio={4 / 3} stroke="#fff" fill="#8884d8" content={<CustomTreemapContent />} />
                </RespCont>
              </div>
           </div>
        </div>
      )}

      {/* Add Position Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-tertiary/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4">
          <div className="bg-white w-full max-w-lg rounded-m border-4 border-tertiary shadow-[8px_8px_0px_0px_#15191d] p-8 relative animate-in zoom-in-95">
            <button onClick={() => setIsModalOpen(false)} className="absolute top-4 right-4 text-grey-300 hover:text-tertiary"><X size={24}/></button>
            <h3 className="text-xl font-black uppercase text-tertiary mb-6 flex items-center gap-2">Add New Position</h3>
            
            <form onSubmit={handleAdd} className="space-y-6">
              <div className="relative">
                <label className="text-[10px] font-black uppercase text-grey-300 mb-2 block">Ticker Symbol</label>
                <input autoFocus type="text" value={newPos.ticker} onChange={e => setNewPos({...newPos, ticker: e.target.value.toUpperCase()})} placeholder="e.g. AAPL" className={`w-full px-4 py-4 bg-secondary border-2 ${validationError ? 'border-[#A45951]' : 'border-grey-200'} rounded-m outline-none font-black text-tertiary uppercase focus:border-tertiary`} />
                {isValidating && <Loader2 className="absolute right-4 top-10 animate-spin text-primary" size={20} />}
                {validationError && <p className="text-[9px] font-black text-[#A45951] uppercase mt-1">{validationError}</p>}
                {validatedData && <p className="text-[9px] font-black text-[#1E8257] uppercase mt-1">{validatedData.name} (${validatedData.price})</p>}
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-[10px] font-black uppercase text-grey-300 mb-2 block">Avg Price</label>
                  <input type="number" step="0.01" value={newPos.avg_price} onChange={e => setNewPos({...newPos, avg_price: e.target.value})} className="w-full px-4 py-4 bg-secondary border-2 border-grey-200 rounded-m outline-none font-black text-tertiary" />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase text-grey-300 mb-2 block">Shares</label>
                  <input type="number" step="0.01" value={newPos.shares} onChange={e => setNewPos({...newPos, shares: e.target.value})} className="w-full px-4 py-4 bg-secondary border-2 border-grey-200 rounded-m outline-none font-black text-tertiary" />
                </div>
              </div>

              <div>
                <label className="text-[10px] font-black uppercase text-grey-300 mb-2 block">Category</label>
                <select value={newPos.category} onChange={e => setNewPos({...newPos, category: e.target.value})} className="w-full px-4 py-4 bg-secondary border-2 border-grey-200 rounded-m outline-none font-black text-tertiary uppercase">
                  <option value="Growth">Growth</option>
                  <option value="Value">Value</option>
                  <option value="Dividend">Dividend</option>
                  <option value="ETF">ETF</option>
                  <option value="Crypto">Crypto</option>
                </select>
              </div>

              <button type="submit" disabled={!validatedData} className={`w-full py-4 rounded-m text-xs font-black uppercase tracking-widest shadow-[4px_4px_0px_0px_#D0BB78] transition-all ${validatedData ? 'bg-tertiary text-white hover:shadow-none hover:translate-x-[2px] hover:translate-y-[2px]' : 'bg-grey-100 text-grey-300 cursor-not-allowed'}`}>Confirm Position</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default PositionsPage;
