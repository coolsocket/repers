class BackendUnavailable(RuntimeError):
    pass


class ExecutorBackend:
    name = "base"

    def run_step(self, step, workspace_root, task_dir):
        raise NotImplementedError


class LocalBackend(ExecutorBackend):
    name = "local"

    def run_ready(self, plan, workspace_root, task_dir, max_workers=4, update_markdown=True):
        from plan_runner import run_local_ready

        return run_local_ready(plan, workspace_root, task_dir, max_workers=max_workers, update_markdown=update_markdown)


class OptionalBackend(ExecutorBackend):
    package_name = None

    def __init__(self):
        try:
            __import__(self.package_name)
        except Exception as exc:
            raise BackendUnavailable(f"{self.name} backend requires optional package '{self.package_name}': {exc}")


class OpenAIAgentsBackend(OptionalBackend):
    name = "openai-agents"
    package_name = "agents"

    def run_ready(self, plan, workspace_root, task_dir, max_workers=4, update_markdown=True):
        from plan_runner import run_openai_agents_ready

        return run_openai_agents_ready(plan, workspace_root, task_dir, max_workers=max_workers, update_markdown=update_markdown)


class LangGraphBackend(OptionalBackend):
    name = "langgraph"
    package_name = "langgraph"

    def run_ready(self, plan, workspace_root, task_dir, max_workers=4, update_markdown=True):
        from plan_runner import run_langgraph_ready

        return run_langgraph_ready(plan, workspace_root, task_dir, max_workers=max_workers, update_markdown=update_markdown)


class MCPBackend(OptionalBackend):
    name = "mcp"
    package_name = "mcp"


def get_backend(name):
    if name == "local":
        return LocalBackend()
    if name == "openai-agents":
        return OpenAIAgentsBackend()
    if name == "langgraph":
        return LangGraphBackend()
    if name == "mcp":
        return MCPBackend()
    raise BackendUnavailable(f"Unknown backend: {name}")
