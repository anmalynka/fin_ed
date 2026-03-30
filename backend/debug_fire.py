from services.fire_engine import FIREEngine, FIREInput

inputs = FIREInput(
    current_age=28,
    target_retire_age=45,
    current_portfolio=100000,
    target_monthly_spend=2500,
    swr=4.0,
    portfolio_mode='Simple',
    expected_return=7.0,
    monthly_deposit=2000,
    contribution_step_up=3.0,
    contribution_duration=17,
    inflation_rate=3.0,
    tax_rate=15.0,
    simulation_mode='Direct'
)

engine = FIREEngine(inputs)
res = engine.run_simulation()

standard = res['scenarios']['Standard']
print(f"Goal: {standard['fire_number_real']}")
print(f"Portfolio at Retire: {standard['portfolio_at_retire_real']}")
print(f"Reached FIRE Age: {standard['reached_fire_age']}")
print(f"Accumulation History Length: {len(standard['accumulation_history'])}")
print(f"Runway History Length: {len(standard['runway_history'])}")
