MIN_AUTOFETCH_INTERVAL = 300  # seconds between cron autofetches

MAX_BYTES_FETCHES_PER_STEP = 1024 * 1024 * 1024
"""How much space can a Step's FetchResults consume?

When storing a new FetchResult, we delete old FetchResults that exceed this
limit.
"""

MAX_N_FETCHES_PER_STEP = 30
"""Maximum number of fetch outputs we'll store on a given Step.

When storing a new FetchResult, we delete old FetchResults that exceed this
limit.
"""

MAX_N_FILES_PER_STEP = 30
"""Maximum number of files we'll store on a given Step.

When storing a new File, we delete old Files that exceed this limit.
"""

MAX_BYTES_FILES_PER_STEP = 2 * 1024 * 1024 * 1024
"""How much space can a Step's Files consume?

When storing a new File, we delete old Files that exceed this limit.
"""
