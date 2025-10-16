from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio

scheduler = AsyncIOScheduler()



class JobManager:
    @staticmethod
    async def start():
        from capital_com.socket_manager import capital_socket, memory
        from settings import settings
        # Schedule periodic tasks
        scheduler.add_job(memory.update_auth_header, IntervalTrigger(minutes=7), id="update_auth_header")
        # scheduler.add_job(capital_socket.ping_all, IntervalTrigger(minutes=5), id="ping_socket")

        await memory.update_auth_header()
        
        # subscribe to capital list
        for epic in settings.capital_list:
            await asyncio.sleep(2)
            await memory.preload_history(epic, resolution="MINUTE_15", n=200)
            await memory.preload_history(epic, resolution="HOUR", n=200)
            await memory.preload_history(epic, resolution="HOUR_4", n=200)
            await memory.preload_history(epic, resolution="DAY", n=200)

            await capital_socket.subscribe(epic, timeframe="MINUTE_15")
            await capital_socket.subscribe(epic, timeframe="HOUR")
            await capital_socket.subscribe(epic, timeframe="HOUR_4")
            await capital_socket.subscribe(epic, timeframe="DAY")
        
        for key, bars in memory.ohlc_history.items():
            print(f"{key[0]} ({key[1]}): {len(bars)} bars")

        scheduler.start()
