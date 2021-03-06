# -*- coding: utf-8 -*-
#
# Copyright 2017 René `reneVolution` Calles <info@renevolution.com>
#
# This file is part of Memory Task Queue.
#
# The Memory Task Queue is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# The Memory Task Queue is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along with
# the Memory Task Queue.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
import sys
import time
import threading

try:
    from Queue import Queue
except ImportError:  # Python 3
    from queue import Queue

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('MemoryTaskQueue')


class Task(object):
    """ Message object for the MemoryTaskQueue

    """
    def __init__(self, payload):
        """ Constructor

        Args:
            payload: A Message payload
        """
        self._payload = payload
        self.retries = 0
        self.last_run = None

    @property
    def payload(self):
        return self._payload

    def stamp(self):
        self.last_run = time.time()


class MemoryTaskQueue(threading.Thread):
    """ A Simple Task Queue to process data
    """

    def __init__(self, cb, on_max_retries=None, delay=None, max_retries=None):
        """ Constructor

        Args:
            cb: A callback method every message is called with
            on_max_retries: Provide a fallback method that is called when
                            max retries have been reached.
            delay: time between retries
            max_retries: max number of retries before calling a message
                         with the fallback
        """
        super(MemoryTaskQueue, self).__init__()
        self.__queue = Queue()

        self.__cb = cb
        self.__fb = on_max_retries

        self.delay = delay
        self.max_retries = max_retries

        self.setDaemon(True)
        self.start()

    def put(self, item):
        """ Put a Message to the Queue

        Args:
            item: Any Item the provided callback and fallback can read.

        """
        if isinstance(item, Task):
            self.__queue.put(item)
        else:
            msg = Task(item)
            logger.info('Creating Message for %s' % msg.payload)
            self.__queue.put(msg)

    def wait(self):
        """ Wait for all Messages being processed """
        self.__queue.join()

    def run(self):
        """ Main Logic to run every Message through provided methods """
        while True:
            msg = self.__queue.get(True)

            assert isinstance(msg, Task)

            if not msg.last_run:
                msg.stamp()

            elif self.delay and time.time() < msg.last_run + self.delay:
                self.__queue.put(msg)
                self.__queue.task_done()
                continue

            if self.max_retries:
                if msg.retries <= self.max_retries:
                    logger.info('Received Message %s' % msg.payload)
                    msg.retries += 1
                    msg.stamp()
                    try:
                        self.__cb(msg.payload)
                    except:
                        self.put(msg)
                else:
                    try:
                        self.__fb(msg.payload)
                    except TypeError:
                        # No fallback method set - skip message
                        pass
            else:
                try:
                    self.__cb(msg.payload)
                except:
                    pass

            self.__queue.task_done()
