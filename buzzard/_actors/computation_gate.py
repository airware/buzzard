from buzzard._actors.message import Msg

class ComputationGate(object):
    """Actor that takes care of delaying the computation of a cache file until needed soon by
    the query.
    """

    def __init__(self, raster):
        self._raster = raster
        self._queries = {}
        self._alive = True

    @property
    def address(self):
        return '/Raster{}/ComputationGate'.format(self._raster.uid)

    @property
    def alive(self):
        return self._alive

    # ******************************************************************************************* **
    def receive_compute_those_cache_files(self, qi):
        """Receive message: The collection started for the computation of the missing cache files,
        allow computation as soon as the cache file is needed soon by query

        Parameters
        ----------
        qi: _actors.cached.query_infos.QueryInfos
        """
        msgs = []

        qicc = qi.cache_computation
        assert qicc is not None

        if qi in self._queries:
            # `receive_output_queue_update` happened before this call
            q = self._queries[qi]
        else:
            q = _Query()
            self._queries[qi] = q
        msgs += self._allow(qi, q)
        return msgs

    def receive_output_queue_update(self, qi, produced_count, queue_size):
        """Receive message: The output queue of a query changed in size.

        Parameters
        ----------
        qi: _actors.cached.query_infos.QueryInfos
        produced_count: int
            How many arrays were pushed in the output queue
        queue_size: int
            How many arrays are currently available in the output queue
        """
        msgs = []

        pulled_count = produced_count - queue_size
        qicc = qi.cache_computation

        if produced_count == qi.produce_count:
            # Query finished
            if qi in self._queries:
                assert (qicc is None) or (q.allowed_count == len(qicc.list_of_cache_fp))
                del self._queries[qi]
        else:
            if qicc is None:
                # this call happened before `receive_compute_those_cache_files`
                if qi in self._queries:
                    # this call already happened
                    q = self._queries[qi]
                else:
                    q = _Query()
                    self._queries[qi] = q
                q.pulled_count = pulled_count
            else:
                q = self._queries[qi]
                q.pulled_count = pulled_count
                msgs += self._allow(qi, q)

        return msgs

    def receive_cancel_this_query(self, qi):
        """Receive message: One query was dropped

        Parameters
        ----------
        qi: _actors.cached.query_infos.QueryInfos
        """
        if qi in self._queries:
            del self._queries[qi]
        return []

    def receive_die(self):
        """Receive message: The raster was killed"""
        assert self._alive
        self._alive = False
        self._queries.clear()
        return []

    # ******************************************************************************************* **
    @staticmethod
    def _allow(qi, q):
        msgs = []
        qicc = qi.cache_computation

        max_prod_idx_allowed = q.pulled_count + qi.max_queue_size
        i = q.allowed_count
        while True:
            if i == len(qicc.list_of_cache_fp):
                break
            cache_fp = qicc.list_of_cache_fp[i]

            prod_idx = qi.dict_of_min_prod_idx_per_cache_fp[cache_fp]
            # map(qi.dict_of_min_prod_idx_per_cache_fp.get, qicc.list_of_cache_fp) is increasing by design
            if prod_idx > max_prod_idx_allowed:
                break
            i += 1
            msgs += [Msg(
                'Computer', 'compute_this_array', cache_fp
            )]
        q.allowed_count = i

        return msgs

    # ******************************************************************************************* **

class _Query(object):

    def __init__(self):
        self.pulled_count = 0
        self.allowed_count = 0