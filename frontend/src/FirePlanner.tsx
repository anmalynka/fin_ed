import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Flame, Target, TrendingUp, Loader2, Info, 
  Plus, Trash2, RotateCcw, Play, Briefcase, ToggleLeft, ToggleRight
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, 
  LineChart, Line, ReferenceLine
} from 'recharts';

interface AssetBucket {
  name: string;
  value: number;
  expected_return: number;
  type: 'percent' | 'amount';
}

interface Scenario {
  fire_number_real: number;
  reached_fire_age: number | null;
  on_track: boolean;
  is_depleted: boolean;
  extra_monthly_needed: number;
  accumulation_history: any[];
  runway_history: any[];
  full_history: any[];
  depletion_age: number;
  portfolio_at_retire_real: number;
}

interface FireResults {
  scenarios: {
    Lean: Scenario;
    Standard: Scenario;
    Fat: Scenario;
  };
  annual_return_used: number;
}

const DEFAULT_INPUTS = {
  current_age: 28,
  target_retire_age: 45,
  plan_until_age: 90,
  current_portfolio: 100000,
  target_monthly_spend: 2500,
  swr: 4.0,
  portfolio_mode: 'Simple',
  expected_return: 7.0,
  buckets: [
    { name: 'Stocks', value: 80, expected_return: 10, type: 'percent' },
    { name: 'Bonds', value: 20, expected_return: 4, type: 'percent' }
  ] as AssetBucket[],
  monthly_deposit: 2000,
  contribution_step_up: 3.0,
  contribution_duration: 17,
  inflation_rate: 3.0,
  tax_rate: 15.0,
  simulation_mode: 'Direct'
};

const formatPrice = (val: number | undefined) => 
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(val || 0);

const formatYAxis = (v: number) => {
  if (v >= 900000 || v <= -900000) return `$${(v/1000000).toFixed(1)}M`;
  return `$${(v/1000).toFixed(0)}k`;
};

const InputField = ({ label, name, value, onChange, type = "number", step = "1" }: any) => (
  <div className="space-y-1.5">
    <label className="text-[9px] font-black uppercase text-grey-400 ml-1 tracking-widest">{label}</label>
    <input 
      name={name} 
      type={type} 
      value={value} 
      onChange={onChange} 
      step={step}
      className="w-full pl-4 pr-4 py-3 bg-white border border-[#6b7280] rounded-m focus:ring-4 focus:ring-primary/20 outline-none transition-all font-bold text-[13px] text-tertiary placeholder:text-[#cbd5e1]"
    />
  </div>
);

const FirePlanner: React.FC<{ apiBase: string }> = ({ apiBase }) => {
  const [inputs, setInputs] = useState(DEFAULT_INPUTS);
  const [results, setResults] = useState<FireResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [activeType, setActiveType] = useState<'Lean' | 'Standard' | 'Fat'>('Standard');
  const [isReal, setIsReal] = useState(true); // Toggle between Real (Inflation Adjusted) and Formal (Nominal)

  const [error, setError] = useState<string | null>(null);

  const fetchSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await axios.post(`${apiBase}/fire/simulate`, inputs);
      if (res.data && res.data.scenarios) {
        setResults(res.data);
      } else {
        throw new Error("Invalid response from server");
      }
    } catch (err: any) {
      console.error("FIRE simulation failed", err);
      const msg = err.response?.data?.detail || "Failed to calculate FIRE plan. Please try again.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSimulation();
    }, 600); // Debounce
    return () => clearTimeout(timer);
  }, [inputs]);

  const handleReset = () => setInputs(DEFAULT_INPUTS);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setInputs(prev => ({
      ...prev,
      [name]: type === 'number' ? parseFloat(value) : value
    }));
  };

  const handleBucketChange = (index: number, field: keyof AssetBucket, value: any) => {
    const next = [...inputs.buckets];
    next[index] = { ...next[index], [field]: value };
    setInputs(prev => ({ ...prev, buckets: next }));
  };

  const addBucket = () => {
    if (inputs.buckets.length >= 8) return;
    setInputs(prev => ({
      ...prev,
      buckets: [...prev.buckets, { name: 'New Asset', value: 0, expected_return: 5, type: 'percent' }]
    }));
  };

  const removeBucket = (index: number) => {
    setInputs(prev => ({
      ...prev,
      buckets: prev.buckets.filter((_, i) => i !== index)
    }));
  };

  const activeScenario = results?.scenarios?.[activeType];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 animate-in fade-in duration-700 pb-20">
      {/* LEFT: Inputs */}
      <div className="lg:col-span-4 space-y-6">
        <div className="bg-white p-6 rounded-m border-2 border-tertiary shadow-[4px_4px_0px_0px_#15191d]">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-2">
              <Flame className="text-primary fill-primary" size={24} />
              <h3 className="font-black text-xl text-tertiary uppercase tracking-tight">Strategy</h3>
            </div>
            <div className="flex gap-2">
              <button onClick={handleReset} className="p-2 text-grey-300 hover:text-tertiary transition-colors" title="Reset"><RotateCcw size={18} /></button>
              <button onClick={fetchSimulation} className="flex items-center gap-2 px-5 py-2.5 bg-tertiary text-white rounded-m text-[10px] font-black uppercase hover:bg-tertiary/90 transition-all shadow-[3px_3px_0px_0px_#D0BB78]">
                {loading ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} fill="currentColor" />} Run
              </button>
            </div>
          </div>

          <div className="mb-8 flex bg-secondary p-1 rounded-m border border-grey-100">
            <button 
              onClick={() => setInputs(p => ({...p, simulation_mode: 'Direct'}))}
              className={`flex-1 py-2.5 text-[9px] font-black uppercase rounded-m transition-all ${inputs.simulation_mode === 'Direct' ? 'bg-white text-tertiary shadow-sm' : 'text-grey-300'}`}
            >
              Accumulation
            </button>
            <button 
              onClick={() => setInputs(p => ({...p, simulation_mode: 'Reverse'}))}
              className={`flex-1 py-2.5 text-[9px] font-black uppercase rounded-m transition-all ${inputs.simulation_mode === 'Reverse' ? 'bg-white text-tertiary shadow-sm' : 'text-grey-300'}`}
            >
              Withdrawal
            </button>
          </div>

          <div className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-4">
              <InputField label="Current Age" name="current_age" value={inputs.current_age} onChange={handleChange} />
              {inputs.simulation_mode === 'Direct' && (
                <InputField label="Target Retire Age" name="target_retire_age" value={inputs.target_retire_age} onChange={handleChange} />
              )}
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-4">
              <InputField label="Target Monthly Spend ($)" name="target_monthly_spend" value={inputs.target_monthly_spend} onChange={handleChange} step="100" />
              <InputField label="Plan Until Age" name="plan_until_age" value={inputs.plan_until_age} onChange={handleChange} />
            </div>
            
            <div className="space-y-1.5">
              <label className="text-[9px] font-black uppercase text-grey-400 ml-1 tracking-widest">Withdrawal Rate (%)</label>
              <input name="swr" type="number" value={inputs.swr} onChange={handleChange} step="0.1" className="w-full pl-4 pr-4 py-3 bg-white border border-[#6b7280] rounded-m focus:ring-4 focus:ring-primary/20 outline-none transition-all font-bold text-[13px] text-tertiary" />
            </div>

            <div className="pt-4 border-t border-grey-100">
              <div className="mb-6">
                <InputField 
                  label={inputs.simulation_mode === 'Direct' ? "Current Balance ($)" : "Starting Capital ($)"} 
                  name="current_portfolio" 
                  value={inputs.current_portfolio} 
                  onChange={handleChange}
                  step="1000" 
                />
                {inputs.portfolio_mode === 'Granular' && (
                  <p className="text-[8px] font-bold text-grey-300 uppercase mt-1 italic leading-tight">
                    * This balance is used as the base for any percentage-based asset categories below.
                  </p>
                )}
              </div>

              <label className="text-[10px] font-black uppercase text-grey-300 tracking-widest mb-4 block">Portfolio Strategy</label>
              <div className="flex bg-secondary p-1 rounded-m border border-grey-100 mb-4">
                <button onClick={() => setInputs(p => ({...p, portfolio_mode: 'Simple'}))} className={`flex-1 py-2 text-[8px] font-black uppercase rounded-m ${inputs.portfolio_mode === 'Simple' ? 'bg-white text-tertiary shadow-sm' : 'text-grey-300'}`}>Simple</button>
                <button onClick={() => setInputs(p => ({...p, portfolio_mode: 'Granular'}))} className={`flex-1 py-2 text-[8px] font-black uppercase rounded-m ${inputs.portfolio_mode === 'Granular' ? 'bg-white text-tertiary shadow-sm' : 'text-grey-300'}`}>Granular</button>
              </div>

              {inputs.portfolio_mode === 'Simple' ? (
                <div className="grid grid-cols-1 gap-4">
                  <InputField label="Expected Annual Return (%)" name="expected_return" value={inputs.expected_return} onChange={handleChange} step="0.5" />
                </div>
              ) : (
                <div className="space-y-3">
                  {inputs.buckets.map((bucket, idx) => (
                    <div key={idx} className="bg-secondary/30 p-3 rounded-m border border-grey-100 relative group">
                      <div className="grid grid-cols-12 gap-2 items-center">
                        <input value={bucket.name} onChange={e => handleBucketChange(idx, 'name', e.target.value)} className="col-span-5 bg-white border border-grey-200 rounded-m px-2 py-1.5 text-[10px] font-bold" />
                        <div className="col-span-4 relative">
                          <input type="number" value={bucket.value} onChange={e => handleBucketChange(idx, 'value', parseFloat(e.target.value))} className="w-full bg-white border border-grey-200 rounded-m pl-2 pr-5 py-1.5 text-[10px] font-bold" />
                          <button onClick={() => handleBucketChange(idx, 'type', bucket.type === 'percent' ? 'amount' : 'percent')} className="absolute right-1 top-1/2 -translate-y-1/2 text-[8px] font-black text-primary bg-secondary px-1 rounded hover:bg-grey-100">{bucket.type === 'percent' ? '%' : '$'}</button>
                        </div>
                        <input type="number" value={bucket.expected_return} onChange={e => handleBucketChange(idx, 'expected_return', parseFloat(e.target.value))} className="col-span-2 bg-white border border-grey-200 rounded-m px-2 py-1.5 text-[10px] font-bold" />
                        <button onClick={() => removeBucket(idx)} className="col-span-1 text-grey-200 hover:text-red-400"><Trash2 size={12} /></button>
                      </div>
                    </div>
                  ))}
                  {inputs.buckets.length < 8 && (
                    <button onClick={addBucket} className="w-full py-2 border-2 border-dashed border-grey-200 rounded-m text-[9px] font-black uppercase text-grey-300 hover:border-tertiary hover:text-tertiary transition-all flex items-center justify-center gap-2">
                      <Plus size={12} /> Add Category
                    </button>
                  )}
                </div>
              )}
            </div>

            {inputs.simulation_mode === 'Direct' && (
              <div className="pt-4 border-t border-grey-100 space-y-4">
                <InputField label="Monthly Deposit ($)" name="monthly_deposit" value={inputs.monthly_deposit} onChange={handleChange} step="100" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-4">
                  <InputField label="Annual Step-up %" name="contribution_step_up" value={inputs.contribution_step_up} onChange={handleChange} step="0.1" />
                  <InputField label="Years Active" name="contribution_duration" value={inputs.contribution_duration} onChange={handleChange} />
                </div>
              </div>
            )}

            <div className="pt-4 border-t border-grey-100 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2 gap-4">
              <InputField label="Inflation %" name="inflation_rate" value={inputs.inflation_rate} onChange={handleChange} step="0.1" />
              <InputField label="Tax %" name="tax_rate" value={inputs.tax_rate} onChange={handleChange} step="1" />
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT: Results */}
      <div className="lg:col-span-8 space-y-6">
        {error && (
          <div className="bg-red-50 border-2 border-red-200 p-4 rounded-m flex items-center gap-3 text-red-700 font-bold uppercase text-[10px]">
            <Info size={16} /> {error}
          </div>
        )}

        <div className="flex flex-col sm:flex-row gap-4">
          {/* Scenario Selection Tabs */}
          <div className="flex-grow flex bg-white rounded-m border-2 border-tertiary p-1 shadow-[2px_2px_0px_0px_#15191d]">
            {['Lean', 'Standard', 'Fat'].map((type) => (
              <button 
                key={type}
                onClick={() => setActiveType(type as any)}
                className={`flex-1 py-3 text-[11px] font-black uppercase rounded-m transition-all ${activeType === type ? 'bg-tertiary text-white' : 'text-grey-300 hover:text-tertiary'}`}
              >
                {type} FIRE
              </button>
            ))}
          </div>

          {/* Real vs Formal Switcher */}
          <div className="flex items-center justify-between px-4 py-2 bg-white rounded-m border-2 border-tertiary shadow-[2px_2px_0px_0px_#15191d]">
             <span className="text-[10px] font-black uppercase text-tertiary mr-4">{isReal ? 'Real Dollars' : 'Formal Dollars'}</span>
             <button 
                onClick={() => setIsReal(!isReal)}
                className={`transition-colors ${isReal ? 'text-[#1E8257]' : 'text-grey-300'}`}
             >
                {isReal ? <ToggleRight size={32} /> : <ToggleLeft size={32} />}
             </button>
          </div>
        </div>

        {/* Header KPIs */}
        <div className="bg-tertiary text-white p-8 rounded-m shadow-[6px_6px_0px_0px_#D0BB78] relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-10"><Target size={120} /></div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative z-10">
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest opacity-60 mb-2">{activeType} Goal ({isReal ? 'Real' : 'Formal'} $)</p>
              <p className="text-4xl font-mono font-black">{activeScenario ? formatPrice(isReal ? activeScenario.fire_number_real : activeScenario.fire_number_real * Math.pow(1 + inputs.inflation_rate/100, (activeScenario.reached_fire_age || inputs.target_retire_age) - inputs.current_age)) : '$0'}</p>
              <p className="text-[10px] font-bold mt-2 uppercase italic text-primary">Monthly Spend: {formatPrice(activeType === 'Lean' ? inputs.target_monthly_spend * 0.7 : activeType === 'Fat' ? inputs.target_monthly_spend * 1.5 : inputs.target_monthly_spend)}</p>
            </div>
            <div>
              <p className="text-[10px] font-black uppercase tracking-widest opacity-60 mb-2">{inputs.simulation_mode === 'Direct' ? 'Projected at Retirement' : 'Initial Amount'}</p>
              <p className="text-4xl font-mono font-black">{activeScenario ? formatPrice(isReal ? activeScenario.portfolio_at_retire_real : activeScenario.portfolio_at_retire_real * Math.pow(1 + inputs.inflation_rate/100, (inputs.target_retire_age - inputs.current_age))) : '$0'}</p>
              <p className="text-[10px] font-bold mt-2 uppercase italic">Est. Return: {results?.annual_return_used}%</p>
            </div>
            <div className="flex flex-col justify-center">
              <div className="px-4 py-3 border-2 border-primary bg-primary/10 rounded-m text-center relative group">
                <p className="text-[10px] font-black uppercase tracking-widest mb-1">
                  {inputs.simulation_mode === 'Direct' ? 'FIRE Target' : 'Portfolio Lasts'}
                </p>
                <p className="text-xl font-black">
                  {inputs.simulation_mode === 'Direct' 
                    ? (activeScenario?.reached_fire_age ? `Age ${activeScenario.reached_fire_age}` : 'Never') 
                    : `Until Age ${activeScenario?.depletion_age}`}
                </p>

                {inputs.simulation_mode === 'Direct' && activeScenario?.reached_fire_age && activeScenario.reached_fire_age > inputs.target_retire_age && activeScenario.extra_monthly_needed && (
                  <div className="absolute -top-2 -right-2">
                    <div className="relative">
                      <div className="p-1 bg-red-400 text-white rounded-full cursor-help group-hover:bg-red-500"><Info size={12} /></div>
                      <div className="absolute bottom-full right-0 mb-2 w-48 bg-white border-2 border-tertiary p-3 rounded-m shadow-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-[100]">
                        <p className="text-[9px] font-black text-tertiary uppercase leading-tight">Effort needed: Add <span className="text-red-500">{formatPrice(activeScenario.extra_monthly_needed)}</span> more every month to reach {activeType} FIRE by age {inputs.target_retire_age}.</p>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>          </div>
        </div>

        {/* Charts */}
        <div className="space-y-6">
          {inputs.simulation_mode === 'Direct' && activeScenario && (
            <div className="bg-white p-8 rounded-m border-2 border-tertiary shadow-[4px_4px_0px_0px_#15191d]">
              <div className="flex justify-between items-center mb-8">
                <h3 className="font-black text-sm uppercase tracking-widest text-tertiary flex items-center gap-2">
                  <TrendingUp size={18} className="text-primary" /> Accumulation ({isReal ? 'Real' : 'Formal'} Dollars)
                </h3>
                <div className="flex gap-4 text-[9px] font-black uppercase">
                  <span className="flex items-center gap-1.5"><div className="w-2 h-2 bg-tertiary"></div> Principal</span>
                  <span className="flex items-center gap-1.5"><div className="w-2 h-2 bg-[#D0BB78]"></div> Compound</span>
                </div>
              </div>
              <div className="h-[350px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={activeScenario.accumulation_history} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                    <XAxis 
                      dataKey="age" 
                      type="number" 
                      domain={[inputs.current_age, inputs.target_retire_age]} 
                      allowDataOverflow={true}
                      axisLine={false} 
                      tickLine={false} 
                      tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} 
                      tickFormatter={(v) => Math.floor(v).toString()} 
                    />
                    <YAxis axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} tickFormatter={formatYAxis} />
                    <RechartsTooltip contentStyle={{borderRadius: '8px', border: '2px solid #0f172a', boxShadow: '4px 4px 0px 0px #0f172a'}} formatter={(v: any) => [formatPrice(v), '']} labelFormatter={(label) => `Age: ${label}`} />
                    <Area type="monotone" dataKey={isReal ? "real_principal" : "nominal_principal"} stackId="1" stroke="#0f172a" fill="#0f172a" fillOpacity={0.8} />
                    <Area type="monotone" dataKey={isReal ? "real_interest" : "nominal_interest"} stackId="1" stroke="#D0BB78" fill="#D0BB78" fillOpacity={0.8} />
                    <ReferenceLine y={isReal ? activeScenario.fire_number_real : activeScenario.fire_number_real * Math.pow(1 + inputs.inflation_rate/100, (activeScenario.reached_fire_age || inputs.target_retire_age) - inputs.current_age)} stroke="#D0BB78" strokeDasharray="5 5" label={{ value: 'FIRE GOAL', position: 'right', fill: '#D0BB78', fontSize: 10, fontWeight: 'bold' }} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="bg-white p-8 rounded-m border-2 border-tertiary shadow-[4px_4px_0px_0px_#15191d]">
            <div className="flex justify-between items-center mb-8">
              <h3 className="font-black text-sm uppercase tracking-widest text-tertiary flex items-center gap-2">
                <Briefcase size={18} className="text-primary" /> Retirement Runway ({isReal ? 'Real' : 'Formal'})
              </h3>
              <div className="text-right">
                <p className="text-[9px] font-black text-grey-300 uppercase">Depletion Age</p>
                <p className="text-lg font-black text-primary">Age {activeScenario?.depletion_age || inputs.plan_until_age}</p>
              </div>
            </div>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={activeScenario?.runway_history || []}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#efe9e9" />
                  <XAxis 
                    dataKey="age" 
                    type="number" 
                    domain={[inputs.simulation_mode === 'Direct' ? inputs.target_retire_age : inputs.current_age, Math.max(inputs.plan_until_age, activeScenario?.depletion_age || 0)]} 
                    allowDataOverflow={true}
                    axisLine={false} 
                    tickLine={false} 
                    tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} 
                    tickFormatter={(v) => Math.floor(v).toString()} 
                  />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#52525b', fontSize: 10, fontWeight: 'bold'}} tickFormatter={formatYAxis} />
                  <RechartsTooltip contentStyle={{borderRadius: '8px', border: '2px solid #0f172a', boxShadow: '4px 4px 0px 0px #0f172a'}} formatter={(v: any) => [formatPrice(v), 'Portfolio']} labelFormatter={(label) => `Age: ${label}`} />
                  <Line type="monotone" dataKey={isReal ? "real_portfolio" : "nominal_portfolio"} stroke="#A45951" strokeWidth={4} dot={false} />
                  <ReferenceLine y={0} stroke="#0f172a" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-6 flex items-center gap-4 p-4 bg-secondary rounded-m border-2 border-dashed border-grey-200">
              <Info className="text-tertiary shrink-0" size={24} />
              <p className="text-[11px] font-bold text-tertiary leading-relaxed uppercase italic">
                {activeScenario?.is_depleted 
                  ? `Sustainable until Age ${activeScenario.depletion_age}. At this point, spending outpaces growth.`
                  : `Portfolio remains positive through Age ${inputs.plan_until_age}. Your plan covers your full horizon!`}
              </p>
            </div>          </div>
        </div>
      </div>
    </div>
  );
};

export default FirePlanner;
