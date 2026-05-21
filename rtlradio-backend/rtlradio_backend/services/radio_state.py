import asyncio

radio_lock = asyncio.Lock()
active_mode = None
fm_service = None
dab_service = None
