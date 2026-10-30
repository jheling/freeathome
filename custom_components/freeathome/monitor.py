"""Record the update telegrams of a SysAP to a file."""
import logging

_LOGGER = logging.getLogger(__name__)


def start_monitor(sysap, host, f, filename, duration, call_later):
    """Monitor one SysAP.

    A function of its own on purpose. Written inside the loop over the SysAPs,
    the callbacks below would share the variables of the loop: every SysAP
    would write into the file opened last, and only the SysAP named last would
    get its handlers cleared.
    """
    def collect_msg(msg):
        try:
            f.write(msg)
            f.write("\n")
            f.flush()
        except (IOError, ValueError):
            # Handlers run before the devices are updated, so an exception here
            # stops every update of this SysAP until Home Assistant is
            # restarted. ValueError means the file is already closed, so this
            # handler is stale and removes itself.
            sysap.clear_update_handlers()
            _LOGGER.warning("Error while writing to %s, monitoring of host %s stopped", filename, host)

    sysap.add_update_handler(collect_msg)

    async def finish_dump(_):
        """Stop monitoring and write dump to file"""
        sysap.clear_update_handlers()
        f.close()
        _LOGGER.info("Finished monitoring for device updates at host %s, dumped to %s", host, filename)

    call_later(duration, finish_dump)
