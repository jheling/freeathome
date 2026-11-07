"""Tell the SysAP regularly that an app is connected, so weather stations report live.

Without RemoteInterface.indicateConnectedApp a weather station sends its wind speed
only at a few fixed steps (about 1.6, 3.4 and 5.5 m/s), and the sensor stays frozen
in between. One call makes the station send at the send interval set for it in
the SysAP, for just under 10 minutes. Repeating it every 3 minutes means that one lost call does not end the
live data. The free@home web interface also sends a message every 3 minutes.
"""
import asyncio
import logging

LOG = logging.getLogger(__name__)

INTERVAL = 180


async def indicate_forever(send, interval=INTERVAL):
    """Call send() every interval seconds until cancelled. A failure never ends the loop."""
    failing = False
    while True:
        try:
            await send()
        except Exception as err:  # pylint: disable=broad-except
            # Warn once per outage: the call repeats every few minutes.
            if not failing:
                LOG.warning("indicateConnectedApp failed: %s", err)
            failing = True
        else:
            if failing:
                LOG.warning("indicateConnectedApp works again")
            failing = False
        await asyncio.sleep(interval)
