import asyncio
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class AsyncTask:
    """Tasks that have to be fed into AsyncScheduler"""
    func: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    call_each_seconds: int = 0
    call_before_sleep: bool = False


class AsyncScheduler:
    """Let's you schedule AsyncTasks and run them concurrently"""
    def __init__(self, loop=False):
        self.tasks = []
        if loop is None:
            loop = asyncio.get_event_loop()
        self.loop = loop

    def add_task(self, task: AsyncTask):
        if task.call_each_seconds > 0:
            task = self.loop_to_once(task)

        self.tasks.append(task)
        return self

    def run(self, forever=False):
        async def _run():
            return await asyncio.gather(*(task.func(*task.args, **task.kwargs) for task in self.tasks),
                                        asyncio.sleep(60 * 60 * 365 * 100) if forever else asyncio.sleep(0))

        self.loop.run_until_complete(_run())

    @staticmethod
    def loop_to_once(task: AsyncTask):
        reusable_task = task.func

        async def inner():
            while True:
                if task.call_before_sleep:
                    await reusable_task()
                await asyncio.sleep(task.call_each_seconds)
                if not task.call_before_sleep:
                    await reusable_task()

        task.func = inner
        return task


if __name__ == '__main__':
    def main():
        async def say_hi_after_2():
            await asyncio.sleep(2)
            print("hi after 2")

        async def say_hi_after_3():
            await asyncio.sleep(2.5)
            print("hi after 2.5")

        async def say_hi_every_1():
            print("hi every 1")

        async def say_hi_every_2():
            print("hi every 2")

        s = AsyncScheduler()
        s.add_task(AsyncTask(func=say_hi_after_2)) \
            .add_task(AsyncTask(func=say_hi_after_3)) \
            # .add_task(AsyncTask(func=say_hi_every_1, call_each_seconds=1))\
        # .add_task(AsyncTask(func=say_hi_every_2, call_each_seconds=2))
        s.run()


    main()
