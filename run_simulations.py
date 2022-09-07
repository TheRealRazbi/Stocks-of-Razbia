import asyncio
from simulations import Watch
from setup_logging import setup_logging


async def main():
    setup_logging(level='INFO')
    watch = Watch()
    await watch.run()


if __name__ == '__main__':
    asyncio.run(main())
