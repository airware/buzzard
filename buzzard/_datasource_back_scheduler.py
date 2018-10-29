import collections
import time
import threading

from buzzard._actors.top_level import ActorTopLevel
from buzzard._actors.message import Msg, DroppableMsg
from buzzard._debug_observers_manager import DebugObserversManager

VERBOSE = 0

class BackDataSourceSchedulerMixin(object):

    def __init__(self, ds_id, debug_observers, **kwargs):
        self._ext_message_to_scheduler_queue = []
        self._thread = None
        self._thread_exn = None
        self._ds_id = ds_id
        self._stop = False
        self._started = False
        self._debug_mngr = DebugObserversManager(debug_observers)
        super().__init__(**kwargs)

    # Public methods **************************************************************************** **
    def ensure_scheduler_living(self):
        if self._thread is None:
            self._thread = threading.Thread(
                target=self._exception_catcher,
                name='DataSource{:#x}Scheduler'.format(self._ds_id),
                daemon=True,
            )
            self._thread.start()
        else:
            self.ensure_scheduler_still_alive()

    def ensure_scheduler_still_alive(self):
        if not self._thread.isAlive():
            if isinstance(self._thread_exn, Exception):
                raise self._thread_exn
            else:
                raise RuntimeError(
                    "DataSource's scheduler crashed without exception. Did you call `exit()`?"
                )

    def put_message(self, msg, check_scheduler_status=True):
        if check_scheduler_status:
            self.ensure_scheduler_living()

        # a list is thread-safe: https://stackoverflow.com/a/6319267/4952173
        self._ext_message_to_scheduler_queue.append(msg)

    def stop_scheduler(self):
        self._stop = True

    # Private methods *************************************************************************** **
    def _exception_catcher(self):
        try:
            self._debug_mngr.event('scheduler_activity_update', True)
            self._scheduler_loop_until_datasource_close()
            self._debug_mngr.event('scheduler_activity_update', False)
        except Exception as e:
            self._thread_exn = e
            raise

    def _scheduler_loop_until_datasource_close(self):
        """This is the entry point of a DataSource's scheduler.
        The design of this method would be much better with recursive calls, but much slower too. (maybe)
        """

        def _register_actor(a):
            if hasattr(a, 'ext_receive_nothing'):
                keep_alive_actors.append(a)

            address = a.address
            # actors[address] = a

            _, grp_name, name = address.split('/')
            # print(f'+ {grp_name:30} {name:30}')
            assert name not in actors[grp_name]
            actors[grp_name][name] = a

        def _find_actors(address, relative_actor):
            names = address.split('/')
            if len(names) == 3:
                if names[1] == 'Pool*':
                    return [
                        v[names[2]]
                        for k, v in actors.items()
                        if k.startswith('Pool')
                    ]
                else:
                    return [actors[names[1]].get(names[2])]
            elif len(names) == 1:
                grp_name = relative_actor.address.split('/')[1]
                return [actors[grp_name].get(names[0])]
            else:
                assert False

        def _unregister_actor(a):
            address = a.address
            _, grp_name, name = address.split('/')
            # print(f'- {grp_name:30} {name:30}')
            del actors[grp_name][name]
            if not actors[grp_name]:
                del actors[grp_name]
            if hasattr(a, 'ext_receive_nothing'):
                keep_alive_actors.remove(a)


        # Dicts of actors
        actors = collections.defaultdict(dict) # type: Mapping[str, Mapping[str, Actor]]

        # List of actors that need to be kept alive with calls to `ext_receive_nothing`
        # `keep_alive_iterator` should never be iterated if `keep_alive_actors` is empty
        keep_alive_actors = []
        keep_alive_iterator = _cycle_list(keep_alive_actors)

        # Stack of pending messages
        piles_of_msgs = [] # type: List[Tuple[Actor, List[Union[Msg, Actor]]]]

        # Instanciate and register the top level actor
        top_level_actor = ActorTopLevel()
        _register_actor(top_level_actor)
        piles_of_msgs.append(
            (top_level_actor, 'ext_receive_', top_level_actor.ext_receive_prime()),
        )

        while True:
            # Step 1: Process all messages on flight
            while piles_of_msgs:
                src_actor, title_prefix, msgs = piles_of_msgs[-1]
                if not msgs:
                    del piles_of_msgs[-1]
                    continue
                msg = msgs.pop(0)
                if isinstance(msg, Msg):
                    if VERBOSE:
                        print('{} {}'.format(
                            ' '.join(['|'] * (len(piles_of_msgs))),
                            msg,
                        ))

                    for dst_actor in _find_actors(msg.address, src_actor): # TODO: make sure that it is enough
                        if dst_actor is None:
                            # This message may be discarted
                            assert isinstance(msg, DroppableMsg), '\n{}\n{}\n'.format(dst_actor, msg)
                        else:
                            new_msgs = getattr(dst_actor, title_prefix + msg.title)(*msg.args)
                            if self._stop:
                                # DataSource is closing. This is the same as `step 5`. (optimisation purposes)
                                return
                            if not dst_actor.alive:
                                # Actor is closing
                                _unregister_actor(dst_actor)
                            if new_msgs:
                                # Message need to be sent
                                piles_of_msgs.append((
                                    dst_actor, 'receive_', new_msgs
                                ))
                else:
                    _register_actor(msg)
                del msg
            src_actor = None
            msgs = None
            msg = None
            dst_actor = None
            new_msgs = None

            # Step 2: Receive external messages
            # a list is thread-safe: https://stackoverflow.com/a/6319267/4952173
            if self._ext_message_to_scheduler_queue:
                msg = self._ext_message_to_scheduler_queue.pop(0)
                dst_actor, = _find_actors(msg.address, None)
                piles_of_msgs.append((
                    dst_actor, 'ext_receive_', [msg]
                ))
                msg = None

            # Step 3: If no messages from phase 2 and some `keep_alive_actors`
            #   Find "keep alive" actors that need to be closed
            #   Find a "keep alive" actor that has messages to send
            if keep_alive_actors and not piles_of_msgs:
                actors_to_remove = []
                for actor, _ in zip(keep_alive_iterator, range(len(keep_alive_actors))):
                    # Iter at most once on each "keep alive" actor
                    new_msgs = actor.ext_receive_nothing()
                    if self._stop:
                        # DataSource is closing. This is the same as `step 5`. (optimisation purposes)
                        return
                    if not actor.alive:
                        # Actor is closing
                        actors_to_remove.append(actor)
                    if new_msgs:
                        # Messages need to be sent
                        if VERBOSE:
                            print(Msg(actor.address, 'receive_nothing'))

                        piles_of_msgs.append((
                            actor, 'receive_', new_msgs
                        ))
                        break
                for actor in actors_to_remove:
                    _unregister_actor(actor)
                actors_to_remove = None
                new_msgs = None
                actor = None

            # Step 4: If no messages from phase 2 nor from phase 3
            #   Sleep
            if not piles_of_msgs:
                self._debug_mngr.event('scheduler_activity_update', False)

                # print('DataSource', id(self), 'loop', len(actors))
                time.sleep(1 / 20)
                # print('++++++++++++++++++++')
                # for k, v in locals().items():
                #     if v is not None:
                #         print('   ', k, v)
                # print('++++++++++++++++++++')
                self._debug_mngr.event('scheduler_activity_update', True)


            # Step 5: Check if DataSource was collected
            if self._stop:
                return


def _cycle_list(l):
    """Loop in a list forever, even if its size changes. Error if empty."""
    i = -1
    while True:
        i = (i + 1) % len(l)
        yield l[i]
