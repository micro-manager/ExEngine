import queue
import threading
import warnings

# Abortable queue object used by the engine
# For Python 3.13, such an object is provided by the standard library
# For older versions, we provide a compatible implementation

if hasattr(queue, 'Shutdown'):
    PriorityQueue = queue.PriorityQueue
    Queue = queue.Queue
    Shutdown = queue.Shutdown
else:
    # Pre-Python 3.13 compatibility
    Shutdown = type('Shutdown', (BaseException,), {})
    class ShutdownMixin:
        def __init__(self):
            super().__init__()
            self._shutdown = threading.Event()

        def shutdown(self, immediately=False):
            """Shuts down the queue 'immediately' or after the current items are processed
            Does not wait for the shutdown to complete (see join).
            Note: this inserts 'None' sentinel values in the queue to signal termination.
            """
            already_shut_down = self._shutdown.is_set()
            if already_shut_down:
                warnings.warn("Queue already shut down", RuntimeWarning)

            self._shutdown.set()
            if immediately:
                # Clear the queue
                try:
                    while self.get(block=False):
                        self.task_done()
                except queue.Empty:
                    pass

            if not already_shut_down:
                super().put(None) # activate the worker thread if it is waiting at 'get'
                self.task_done() # don't count None as actual task, don't wait for it in 'join'

        def get(self, block=True, timeout=None):
            retval = super().get(block, timeout)
            if retval is None:
                super().put(None)  # activate the next worker thread if it is waiting at 'get'
                self.task_done()  # don't count None as actual task, don't wait for it in 'join'
                raise Shutdown
            else:
                return retval

        def put(self, item, block=True, timeout=None):
            if self._shutdown.is_set():
                raise Shutdown # thread is being shut down, cannot add more items
            return super().put(item, block, timeout)

    class PriorityQueue(ShutdownMixin, queue.PriorityQueue):
        pass

    class Queue(ShutdownMixin, queue.Queue):
        pass