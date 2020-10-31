#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio

from fah.pfreeathome import FreeAtHomeSysApp

FAH_HOST = ""
FAH_USER = ""
FAH_PASSWORD = ""

LOG = logging.getLogger(__name__)

async def main():
    # set up logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)-8s %(message)s')
    
    sysap = FreeAtHomeSysApp(FAH_HOST, FAH_USER, FAH_PASSWORD)

    await sysap.connect()
    await sysap.wait_for_connection()
    xml = await sysap.get_all_xml()

    LOG.info(xml)


if __name__ == '__main__':
    asyncio.run(main())
