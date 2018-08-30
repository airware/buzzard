import logging

from buzzard._actors.message import Msg
from buzzard._actors.cached.query_infos import CachedQueryInfos

LOGGER = logging.getLogger(__name__)

class ActorQueriesHandler(object):
    """Actor that takes care of the lifetime of a raster's queries"""

    def __init__(self, raster):
        """
        Parameter
        ---------
        raster: _a_recipe_raster.ABackRecipeRaster
        """
        self._raster = raster
        self._queries = {}
        self._alive = True

    @property
    def address(self):
        return '/Raster{}/QueriesHandler'.format(self._raster.uid)

    @property
    def alive(self):
        return self._alive

    # ******************************************************************************************* **
    def ext_receive_new_query(self, queue_wref, max_queue_size, produce_fps,
                              band_ids, dst_nodata, interpolation):
        """Receive message sent by something else than an actor, still treated synchronously: There
        is a new query.

        Parameters
        ----------
        queue_wref: weakref.ref of queue.Queue
           Queue returned by the underlying `queue_data` (or behind a `(get|iter)_data`).
        max_queue_size: int
           Max queue size of the queue returned by the underlying `queue_data`
           (or behind a `(get|iter)_data`).
        produce_fps: sequence of Footprint
           Parameter of the underlying `(get|iter|queue)_data`
        band_ids: sequence of int
           Parameter of the underlying `(get|iter|queue)_data`
        dst_nodata: nbr
           Parameter of the underlying `(get|iter|queue)_data`
        interpolation: str
           Parameter of the underlying `(get|iter|queue)_data`
        """
        msgs = []

        qi = CachedQueryInfos(
            self._raster, produce_fps,
            band_ids, dst_nodata, interpolation,
            max_queue_size
        )
        q = _Query(queue_wref)
        self._queries[qi] = q
        msgs += [
            Msg('/GlobalPrioritiesWatcher', 'new_query', qi),
            Msg('ProductionGate', 'make_those_arrays', qi),
        ]
        if len(qi.list_of_cache_fp) > 0:
            msgs += [Msg('CacheSupervisor', 'make_those_cache_tiles_available', qi)]

        return msgs

    def ext_receive_nothing(self):
        """Receive message sent by something else than an actor, still treated synchronously: What's
        up?
        Was an output queue sinked?
        Was an output queue collected by gc?
        """
        msgs = []

        killed_queries = []
        for qi, q in self._queries.items():
            queue = q.queue_wref()
            if q is None:
                killed_queries.append(qi)
            else:
                new_queue_size = queue.qsize()
                assert new_queue_size <= q.queue_size
                if new_queue_size != q.queue_size:
                    q.queue_size = new_queue_size
                    args = qi, q.produced_count, q.queue_size
                    msgs += [
                        Msg('/GlobalPrioritiesWatcher', 'output_queue_update', self._raster.uid, *args),
                        Msg('ProductionGate', 'output_queue_update', *args),
                        Msg('ComputationGate', 'output_queue_update', *args),
                    ]
            del q

        for qi in killed_queries:
            msgs += self._cancel_query(qi)

        return msgs

    def receive_made_this_array(self, qi, prod_id, array):
        """Receive message: This array is ready to be sent to the output queue. Just do it in the
        righ order.

        Parameters
        ----------
        qi: _actors.cached.query_infos.QueryInfos
        prod_id: int
        array: np.ndarray
        """
        msgs = []
        q = self._queries[qi]
        assert prod_id not in q.produce_arrays_dict, 'This array was already computed'
        assert prod_id <= q.produced_count, 'This array was already sent'
        q.produce_arrays_dict[prod_id] = array

        # Send arrays ready ****************************************************
        prod_id = q.produced_count
        queue = q.queue_wref()
        if queue is None:
            # Queue is None (Queue was collected upstream by gc) -> Ignore the problem,
            # `ext_receive_nothing` will be called soon
            pass
        else:
            # Put arrays in queue in the right order
            while True:
                if prod_id not in q.produce_arrays_dict:
                    # Next array is not ready yet
                    break
                array = q.produce_arrays_dict.pop(prod_id)

                # The way this is all designed, the system does not start to work on a `prod_id` if
                # it cannot be inserted in the output queue. It means that the `queue.Full`
                # exception cannot be raised by the following `put_nowait`.
                queue.put_nowait(array)

                q.queue_size += 1
                q.produced_count += 1
                prod_id  = q.produced_count
                args = qi, q.produced_count, q.queue_size
                msgs += [
                    Msg('/GlobalPrioritiesWatcher', 'output_queue_update', *args),
                    Msg('ProductionGate', 'output_queue_update', *args),
                    Msg('ComputationGate', 'output_queue_update', *args),
                ]
            if q.produced_count == qi.produce_count:
                del self._queries[qi]
        del queue

        return []

    def receive_die(self):
        """Receive message: The raster was killed"""
        assert self._alive
        self._alive = False

        msgs = []
        for qi in list(self._queries.keys()):
            msgs += self._cancel_query(qi)

        self._queries.clear()
        return msgs

    # ******************************************************************************************* **
    def _cancel_query(self, qi):
        q = self._queries.pop(qi)
        assert q.produced_count != qi.produce_count, "This query finished and can't be cancelled"
        LOGGER.warn('Dropping a query with {}/{} arrays produced.'.format(
            q.produced_count,
            qi.produce_count,
        ))
        return [
            Msg('/GlobalPrioritiesWatcher', 'cancel_this_query', qi),

            Msg('ProductionGate', 'cancel_this_query', qi),
            Msg('Producer', 'cancel_this_query', qi),
            Msg('Resampler', 'cancel_this_query', qi),
            Msg('CacheExtractor', 'cancel_this_query', qi),
            Msg('Reader', 'cancel_this_query', qi),

            Msg('CacheSupervisor', 'cancel_this_query', qi),
            Msg('ComputationGate', 'cancel_this_query', qi),
            Msg('Computer', 'cancel_this_query', qi),
        ]

    # ******************************************************************************************* **

class _Query(object):
    def __init__(self, queue_wref):
        self.queue_wref = queue_wref
        self.produce_arrays_dict = {}
        self.produced_count = 0
        self.queue_size = 0
