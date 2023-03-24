import psutil
from anyio import to_thread
from fastapi import APIRouter, Depends
from jupyverse_api.app import App
from jupyverse_api.auth import Auth, User
from jupyverse_api.resource_usage import ResourceUsage, ResourceUsageConfig


class _ResourceUsage(ResourceUsage):
    def __init__(
        self,
        app: App,
        auth: Auth,
        resource_usage_config: ResourceUsageConfig,
    ):
        super().__init__(app)

        router = APIRouter()

        @router.get("/api/metrics/v1")
        async def get_metrics(
            user: User = Depends(auth.current_user(permissions={"contents": ["read"]})),
        ):
            cur_process = psutil.Process()
            all_processes = [cur_process] + cur_process.children(recursive=True)

            # Get memory information
            rss = 0
            for p in all_processes:
                try:
                    rss += p.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            mem_limit = resource_usage_config.mem_limit

            limits = {"memory": {"rss": mem_limit}}
            if resource_usage_config.mem_limit and resource_usage_config.mem_warning_threshold:
                limits["memory"]["warn"] = (mem_limit - rss) < (
                    mem_limit * resource_usage_config.mem_warning_threshold
                )

            metrics = {"rss": rss, "limits": limits}

            # Optionally get CPU information
            if resource_usage_config.track_cpu_percent:
                cpu_count = psutil.cpu_count()
                cpu_percent = await to_thread.run_sync(_get_cpu_percent, all_processes)

                if resource_usage_config.cpu_limit:
                    limits["cpu"] = {"cpu": resource_usage_config.cpu_limit}
                    if resource_usage_config.cpu_warning_threshold:
                        limits["cpu"]["warn"] = (resource_usage_config.cpu_limit - cpu_percent) < (
                            resource_usage_config.cpu_limit
                            * resource_usage_config.cpu_warning_threshold
                        )

                metrics.update(cpu_percent=cpu_percent, cpu_count=cpu_count)

            return metrics

        self.include_router(router)


def _get_cpu_percent(all_processes):
    def get_cpu_percent(p):
        try:
            return p.cpu_percent(interval=0.05)
        # Avoid littering logs with stack traces complaining
        # about dead processes having no CPU usage
        except BaseException:
            return 0

    return sum([get_cpu_percent(p) for p in all_processes])
