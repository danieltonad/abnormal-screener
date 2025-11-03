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

        await JobManager.subscribe_capital_list(settings=settings, memory=memory, capital_socket=capital_socket, max_concurrent=5)

        for key, bars in memory.ohlc_history.items():
            print(f"{key[0]} ({key[1]}): {len(bars)} bars")

        scheduler.start()


    
    async def subscribe_epic(epic, memory, capital_socket):
        # preload history concurrently (these are REST calls, can overlap safely)
        await memory.preload_history(epic, resolution="MINUTE_30", n=200)
        await memory.preload_history(epic, resolution="HOUR", n=200)
        await memory.preload_history(epic, resolution="HOUR_4", n=200)
        await memory.preload_history(epic, resolution="DAY", n=200)

        # throttle socket subs — prevent flood disconnects
        for timeframe in ["MINUTE_30", "HOUR", "HOUR_4", "DAY"]:
            try:
                await capital_socket.subscribe(epic, timeframe=timeframe)
            except Exception as e:
                print(f"Socket subscription failed for {epic} {timeframe}: {e}")
            await asyncio.sleep(0.3)  # small delay per sub

    
    async def subscribe_capital_list(settings, memory, capital_socket, max_concurrent=7):

        sem = asyncio.Semaphore(max_concurrent)

        async def worker(epic):
            async with sem:
                try:
                    await JobManager.subscribe_epic(epic, memory, capital_socket)
                    await asyncio.sleep(0.5)  # small delay between tasks to avoid bursts
                except Exception as e:
                    print(f"Error subscribing {epic}: {e}")

        # schedule all concurrently
        await asyncio.gather(*(worker(epic) for epic in settings.capital_list))
