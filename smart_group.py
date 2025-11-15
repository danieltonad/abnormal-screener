from leverage import get_instrument_type, EpicInstrument
import random
from collections import defaultdict

import random
from collections import defaultdict
import math


def conjured_epic_list(epics, block_size=40):
    buckets = defaultdict(list)

    # classify
    for epic in epics:
        buckets[get_instrument_type(epic)].append(epic)

    # shuffle inside each bucket
    for b in buckets.values():
        random.shuffle(b)

    cryptos = buckets[EpicInstrument.CRYPTO]
    indices = buckets[EpicInstrument.INDICES]
    stocks  = buckets[EpicInstrument.STOCKS]
    forex   = buckets[EpicInstrument.CURRENCIES]
    comms   = buckets[EpicInstrument.COMMODITIES]

    # ALL items must be used
    total_items = len(epics)
    num_blocks  = math.ceil(total_items / block_size)

    # prepare empty blocks
    blocks = [[] for _ in range(num_blocks)]

    # Distribute crypto cyclically
    for i, c in enumerate(cryptos):
        blocks[i % num_blocks].append(c)

    # Distribute indices cyclically
    for i, idx in enumerate(indices):
        blocks[i % num_blocks].append(idx)

    # Now fill the remaining slots with stocks → forex → comms
    fill_buckets = [stocks, forex, comms]

    for block in blocks:
        for bucket in fill_buckets:
            while len(block) < block_size and bucket:
                block.append(bucket.pop())

    # Final shuffle inside each block
    for block in blocks:
        random.shuffle(block)

    # Flatten into one conjured list
    final_list = [item for block in blocks for item in block]

    return final_list

