# Workshop patterns (source: Workshop Studio 083b80d7, read 2026-11-04)

Env: us-east-1, Python 3.13, strands-agents>=1.42.0, bedrock-agentcore,
strands-agents-evals, boto3>=1.35.0. Default model = Claude on Bedrock.

## M1 Agent loop + tools
from strands import Agent, tool
@tool def f(x: str) -> str: """Docstring = model's manual. Args: x: ..."""
agent = Agent(tools=[...], system_prompt=...); result = agent(prompt)
Inspect: agent.messages, result.metrics.get_summary()['total_cycles'],
result.metrics.accumulated_usage['totalTokens']. chat.py reuses one Agent.

## M2 Hooks
from strands.hooks import HookProvider, HookRegistry, BeforeInvocationEvent, BeforeToolCallEvent
class X(HookProvider): register_hooks(self, registry): registry.add_callback(Event, fn)
BeforeToolCallEvent: event.tool_use["name"]; event.cancel_tool = "message to model"
Agent(..., hooks=[X()])

## M3 Skills + steering (both are plugins)
from strands import Agent, AgentSkills
AgentSkills(skills=["./skills"])  # skills/<name>/SKILL.md with frontmatter name, description
from strands.vended_plugins.steering import SteeringHandler, Proceed, Guide, ToolSteeringAction, LedgerProvider, LLMSteeringHandler
class H(SteeringHandler):
    name = "..."; __init__: super().__init__(context_providers=[LedgerProvider()])
    async def steer_before_tool(self, *, agent, tool_use, **kwargs) -> ToolSteeringAction:
        ledger = self.steering_context.data.get("ledger", {}); calls = ledger.get("tool_calls", [])
        # c["tool_name"], c["status"] == "success"
        return Proceed(reason=...) | Guide(reason=...)
class T(LLMSteeringHandler): __init__: super().__init__(system_prompt="...")  # steer_after_model
Agent(..., plugins=[AgentSkills(...), H(), T()])

## M4 Session managers
from strands.agent.conversation_manager import SlidingWindowConversationManager
from strands.session.file_session_manager import FileSessionManager   # S3SessionManager for prod
FileSessionManager(session_id="...", storage_dir="./sessions")
Agent(..., conversation_manager=SlidingWindowConversationManager(window_size=20), session_manager=sm)

## M5 Deploy (AgentCore Runtime, Direct Code Deploy)
from bedrock_agentcore.runtime import BedrockAgentCoreApp
app = BedrockAgentCoreApp()
@app.entrypoint
def invoke(payload, context): prompt = payload.get("prompt"); ...; return str(agent(prompt)).strip()
if __name__ == "__main__": app.run()
CLI: sudo npm install -g @aws/agentcore (Node 20+); pip uninstall bedrock-agentcore-starter-toolkit
agentcore create (Skip) -> cd <proj> -> agentcore add (agent, Bring my own code, app/MyAgent/,
main.py, Direct Code Deploy, Amazon Bedrock) -> copy code into app/MyAgent/ ->
cd app/MyAgent && uv init --bare --python 3.13 && uv add strands-agents bedrock-agentcore aws-opentelemetry-distro boto3
-> agentcore dev (local inspector :8081) -> agentcore deploy -> agentcore invoke "..." [--session-id >=33 chars]
boto3: client("bedrock-agentcore").invoke_agent_runtime(agentRuntimeArn, runtimeSessionId(33+), payload=json bytes, qualifier="DEFAULT")
Region from agentcore/aws-targets.json. Logs: agentcore logs / traces; CloudWatch Transaction Search.
Cleanup: agentcore remove all -y && agentcore deploy

## M6 Multi-agent (agents-as-tools)
@tool def specialist(issue: str) -> str: """Docstring = routing logic."""
    return str(Agent(tools=[...], system_prompt=..., callback_handler=None)(issue))
orchestrator = Agent(tools=[..., specialist], system_prompt=...)

## M7 Evals (strands_evals)
from strands_evals import eval_task, Case, Experiment
from strands_evals.evaluators import OutputEvaluator, TrajectoryEvaluator
from strands_evals.extractors import tools_use_extractor
from strands_evals.types import TaskOutput
Case[str, str](name, input, expected_output | expected_trajectory=[...])
OutputEvaluator(rubric=..., include_inputs=True); TrajectoryEvaluator(rubric=..., include_inputs=True)
trajectory = tools_use_extractor.extract_agent_tools_used_from_messages(agent.messages)
Experiment[str,str](cases=..., evaluators=[...]).run_evaluations(task_fn).display()
