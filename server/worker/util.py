import time


async def benchmark(logger, task, message, *args):
    t1 = time.time()
    logger.info(f'Start {message}', *args)
    try:
        await task
    finally:
        t2 = time.time()
        logger.info(f'End {message} (%dms)', *args, 1000 * (t2 - t1))
