import ast, json, re
from datetime import datetime
import streamlit as st

st.set_page_config(page_title="AI-Infused Software Engineering Workbench", page_icon="🤖", layout="wide")

SAMPLE = """def calculate_total(items):
    total = 0
    for item in items:
        total += item["price"] * item["quantity"]
    print("Total:", total)
    return total
"""

def parse_code(code):
    try:
        return ast.parse(code), None
    except SyntaxError as e:
        return None, f"SyntaxError: {e.msg} at line {e.lineno}"

def inspect_repository(code):
    tree, err = parse_code(code)
    if err: return {"status":"error","error":err}
    return {"status":"ok","functions":[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)],
            "classes":[n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)],
            "lines":len(code.splitlines())}

def static_analyzer(code):
    tree, err = parse_code(code)
    if err: return {"status":"error","findings":[{"severity":"HIGH","issue":err}]}
    findings=[]
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            if n.func.id=="eval":
                findings.append({"severity":"HIGH","issue":"Use of eval() can execute untrusted input.","line":n.lineno})
            if n.func.id=="print":
                findings.append({"severity":"LOW","issue":"Debug print() found; consider structured logging.","line":n.lineno})
        if isinstance(n, ast.FunctionDef) and len(n.body)>12:
            findings.append({"severity":"MEDIUM","issue":f"Function '{n.name}' is long and may be difficult to maintain.","line":n.lineno})
        if isinstance(n, ast.ExceptHandler) and n.type is None:
            findings.append({"severity":"MEDIUM","issue":"Bare except can hide unexpected failures.","line":n.lineno})
        if isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name) and re.search(r"(password|secret|api_key|token)",t.id,re.I):
                    if isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):
                        findings.append({"severity":"HIGH","issue":f"Possible hard-coded secret in '{t.id}'.","line":n.lineno})
    if not findings: findings=[{"severity":"INFO","issue":"No issues detected by the current rule set.","line":"-"}]
    return {"status":"ok","findings":findings}

def test_generator(code):
    tree, err=parse_code(code)
    if err: return {"status":"error","tests":[]}
    funcs=[n.name for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)]
    tests=[f"def test_{f}_basic():\n    result = {f}(...)\n    assert result is not None" for f in funcs]
    return {"status":"ok","tests":tests or ["# No Python functions detected."]}

def sustainability(code):
    tree, err=parse_code(code)
    loops=sum(isinstance(n,(ast.For,ast.While)) for n in ast.walk(tree)) if tree else 0
    score=max(0,100-len(code.splitlines())//5-loops*5)
    return {"status":"ok","heuristic_efficiency_score":score,
            "note":"Heuristic only; not a real electricity or carbon measurement."}

TOOLS={"inspect_repository":inspect_repository,"static_analyzer":static_analyzer,
       "test_generator":test_generator,"sustainability_estimator":sustainability}

def plan_for(goal):
    g=goal.lower()
    plan=["inspect_repository","static_analyzer","test_generator"]
    if any(x in g for x in ["sustain","carbon","efficient","performance"]):
        plan.insert(2,"sustainability_estimator")
    return plan

st.title("AI-Infused Software Engineering Workbench")
st.caption("Goal → Plan → Tools → Evidence → Recommendation")

with st.sidebar:
    goal=st.text_area("Software-engineering goal",
        "Review this Python code for quality, security, tests, and maintainability.",height=120)
    approval=st.checkbox("Require human approval before tool execution",True)
    st.info("Reproducible local prototype: no paid LLM/API is required.")

code=st.text_area("Python source code",SAMPLE,height=280)
plan=plan_for(goal)

st.subheader("1. Agent Plan")
st.write("Goal:",goal)
st.write("Planned tool sequence:"," → ".join(plan))

approved=True
if approval:
    approved=st.checkbox("I approve execution of the planned tools.",False)

if st.button("Run Agent",type="primary"):
    if not approved:
        st.warning("Human approval is required.")
    else:
        trace=[]
        for i,name in enumerate(plan,1):
            trace.append({"step":i,"tool":name,"timestamp":datetime.now().isoformat(timespec="seconds"),
                          "result":TOOLS[name](code)})
        st.session_state.trace=trace
        st.success("Agent run completed.")

trace=st.session_state.get("trace",[])
if trace:
    st.subheader("2. Execution Trace")
    for item in trace:
        st.markdown(f"**Step {item['step']} — `{item['tool']}`**")
        st.json(item["result"])

    findings=[f for x in trace if x["tool"]=="static_analyzer" for f in x["result"].get("findings",[])]
    st.subheader("3. Agent Recommendation")
    high=[f for f in findings if f.get("severity")=="HIGH"]
    med=[f for f in findings if f.get("severity")=="MEDIUM"]
    if high: st.error(f"Prioritize {len(high)} high-severity finding(s).")
    elif med: st.warning(f"Address {len(med)} maintainability finding(s).")
    else: st.success("No high-priority findings from the current rule set.")
    st.download_button("Export agent trace as JSON",json.dumps(trace,indent=2),
                       "agent_trace.json","application/json")

with st.expander("Architecture"):
    st.code("""Developer Goal
      ↓
Agent Planner
      ↓
Tool Selection
      ↓
Repository Inspector / Static Analyzer / Test Generator / Sustainability Estimator
      ↓
Evidence + Execution Trace
      ↓
Recommendation
      ↓
Human Review / Approval""")

with st.expander("Ethics, Limitations & Future"):
    st.markdown("""**Ethics:** human approval, transparent evidence and explicit tool boundaries.

**Limitations:** deterministic prototype; no external LLM, arbitrary code execution or autonomous repository modification.

**Future:** LLM planning, repository retrieval, sandboxed execution, automated test repair, multi-agent review, reliability benchmarks and real energy/carbon measurement.""")
