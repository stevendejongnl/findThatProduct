import os
import aiohttp


class ChangeWatchClient:
    def __init__(self, base_url: str | None = None):
        self._base_url = base_url

    @classmethod
    def from_env(cls) -> "ChangeWatchClient":
        return cls(base_url=os.getenv("CHANGEWATCH_URL"))

    @property
    def enabled(self) -> bool:
        return self._base_url is not None

    async def save_monitor(self, name: str, source: str) -> None:
        if not self.enabled:
            return
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self._base_url}/api/monitors/{name}/save",
                json={"source": source},
                raise_for_status=True,
            )

    async def trigger_run(self, name: str) -> None:
        if not self.enabled:
            return
        async with aiohttp.ClientSession() as session:
            await session.post(
                f"{self._base_url}/monitors/{name}/run",
                raise_for_status=True,
            )

    async def list_monitors(self) -> list[dict]:
        if not self.enabled:
            return []
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self._base_url}/api/monitors", raise_for_status=True) as resp:
                return await resp.json()

    async def get_source(self, name: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/api/monitors/{name}/source", raise_for_status=True
            ) as resp:
                data = await resp.json()
                return data["source"]

    async def get_runs(self, name: str, limit: int = 2) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/api/monitors/{name}/runs",
                params={"limit": limit},
                raise_for_status=True,
            ) as resp:
                return await resp.json()

    async def get_metrics(self, name: str, hours: int = 720) -> list[dict]:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self._base_url}/api/monitors/{name}/metrics",
                params={"hours": hours},
                raise_for_status=True,
            ) as resp:
                return await resp.json()

    async def delete_monitor(self, name: str) -> None:
        if not self.enabled:
            return
        async with aiohttp.ClientSession() as session:
            await session.delete(
                f"{self._base_url}/api/monitors/{name}", raise_for_status=True
            )
