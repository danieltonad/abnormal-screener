from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import asyncio

scheduler = AsyncIOScheduler()



class JobManager:
    @staticmethod
    async def start():
        from capital_com.socket import capital_socket, memory
        from settings import settings
        # Schedule periodic tasks
        scheduler.add_job(memory.update_auth_header, IntervalTrigger(minutes=7), id="update_auth_header")
        scheduler.add_job(capital_socket.ping_socket, IntervalTrigger(minutes=5), id="ping_socket")

        await memory.update_auth_header()
        
        # subscribe to capital list
        for epic in settings.capital_list:
            await asyncio.sleep(1)
            await capital_socket.subscribe_to_epic(epic, timeframe="MINUTE")
            await capital_socket.subscribe_to_epic(epic, timeframe="MINUTE_15")
        scheduler.start()
