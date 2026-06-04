---
tags: [ros2, executors, concurrency, rclpy, debugging]
---

# ROS2 Executors, Threads and Spinning

## What it is
An **executor** is the single loop that *watches* a node's mailboxes (subscriptions, service/
action responses, timers, guard conditions) and dispatches ready work to **threads**. A node
holds exactly one pointer to its owner: `node.executor`. Threads are just the workers the
executor hands callbacks to. **Executor ≠ threads.** You can have one executor with many
threads (`MultiThreadedExecutor(num_threads=4)`): one watcher, four workers.

## Why it exists
ROS2 separated *deciding what's ready* (the executor's wait-set loop) from *running it* (threads)
so a node can process callbacks concurrently without you managing the event loop. `rclpy.spin(node)`
is just "create/borrow an executor, add the node, loop forever."

## How it works (and how it bites)
The trap: helpers that **spin the node from inside a callback that's already being spun**.

- `rclpy.spin_until_future_complete(node, fut)` and `rclpy.spin_once(node)` (no `executor=` arg)
  grab a **global `SingleThreadedExecutor`**, call `executor.add_node(node)` — which **reassigns
  `node.executor` to that global executor** — spin, then `remove_node`, which **never restores
  the pointer**. (rclpy `__init__.py` `spin_*`, `executors.py` `add_node`.)
- Result: `node.executor` is left dangling at the idle global executor. Your real
  `MultiThreadedExecutor` still has the node in its `_nodes` set, so already-registered entities
  keep working — but the dangling pointer **breaks the *next* lazily-created client**: its wait-set
  registration (`node.executor.wake()`) goes to the dead executor, so your live executor never
  watches that mailbox. Its future **never completes** (silent hang, not a crash).

### The tells
- **Dormant damage:** the spin happens early (e.g. `wait_until_executed()` in stage 1), the symptom
  appears later (a `compute_ik` created in stage 5). Scene of the crime ≠ scene of the body.
- **Eager clients survive, lazy clients die:** anything created in `__init__` (before any spin) is
  already on the wait-set; only clients created *after* the first spin are orphaned.
- **Sync calls survive, async+passive-poll dies:** sync helpers (`compute_fk`, sync `compute_ik`)
  `spin_once` the node *themselves* to drive their own future — they don't depend on the live
  executor. An `*_async` call + `while not fut.done(): sleep` poll **does** depend on it.

## How to do it right
1. **Never spin the node from inside an executor-driven callback.** In a `MultiThreadedExecutor`
   app the executor owns spinning. To wait on a future, **poll it** (`while not fut.done(): sleep`)
   and let a *free thread* service it — needs ≥2 threads (we run 4; with 1 it deadlocks).
2. **Create clients eagerly** (in `__init__`), not lazily inside callbacks, so they register while
   `node.executor` is still correct.
3. If a library only offers a node-spinning sync call (pymoveit2 `wait_until_executed`), the clean
   fix is its **non-spinning** equivalent (e.g. poll `query_state()`), not the sync call.

## How it showed up in my project
Stage-5 `compute_ik` hung forever (5 s `future is not done`). Root cause: `wait_until_executed()`
(`rclpy.spin_once`) and four `spin_until_future_complete()` calls had corrupted `node.executor`
back in stage 1/3, so the **lazily-created** stage-5 IK client was never serviced. Proven by a
probe (an IK call at the very top, pre-corruption, worked). Fixed by (a) a non-spinning
`_wait_for_future()` poll for the gripper/attach futures and (b) switching stage-5 IK to **sync
`compute_ik`** (self-spins, immune). Proper root fix (replace `wait_until_executed` with a
`query_state()` poll) is backlogged.

Related: [[ROS2 Actions]] · [[MoveIt2 and Planning Pipelines]] · [[Inverse Kinematics]] ·
[[ROS2 Workspaces and Sourcing]] · gotchas #16, #18.
