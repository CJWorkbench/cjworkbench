import contextlib
import time


@contextlib.contextmanager
def benchmark_sync(logger, message, *args):
    t1 = time.time()
    logger.info(f"Start {message}", *args)
    try:
        yield
    finally:
        t2 = time.time()
        logger.info(f"End {message} (%dms)", *args, 1000 * (t2 - t1))


async def benchmark(logger, task, message, *args):
    t1 = time.time()
    logger.info(f"Start {message}", *args)
    try:
        return await task
    finally:
        t2 = time.time()
        logger.info(f"End {message} (%dms)", *args, 1000 * (t2 - t1))
