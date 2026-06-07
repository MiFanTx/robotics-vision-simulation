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

## A Future is a claim ticket only the engine can stamp
`call_async()` / `compute_ik_async()` / `send_goal_async()` send a request and hand you a
**Future** — a coat-check ticket. It does *not* fill itself: it completes only when the executor
processes the response message and the **client** (which bound "request #N → this Future") calls
`set_result`. So **a Future completes only if someone is spinning the node that owns the client.**
`spin_once(node)` doesn't target your Future — it pumps the *whole* node; yours completes as a side
effect because that response happens to be ready. (That's why you loop: each `spin_once` handles one
ready item; you spin until *your* ticket is stamped.) Note **async never touches the executor** — only
the *sync* helpers self-spin. `sync = async + self-spin-to-wait`.

## How to do it right (CORRECTED 2026-06-08)
The earlier version of this note said *"never spin; poll the future and let a free thread service
it."* **That was wrong** — see the war story below. The real rule, for a **sequential blocking
callback** (a state machine like our pick-place):

1. **Self-spin to drive each future** (`while not fut.done(): rclpy.spin_once(self, timeout_sec=0.1)`),
   exactly like `compute_fk` / sync `compute_ik` do. Don't rely on the live MTE to complete a future
   *during* a callback — a library (pymoveit2) may have already evicted your node from it.
2. **Create clients eagerly** (`__init__`) so a self-spin can drive them; lazy mid-callback clients
   are the #18 hang case.
3. **Pick ONE model and don't mix.** Two coherent architectures: *event-driven async* (short
   callbacks, `add_done_callback`, never self-spin — the MTE completes futures) **or** *blocking
   self-spin* (sequential, you spin to drive each future). Our controller is the second. Mixing
   async-relying-on-the-MTE with self-spinning sync helpers is the oil/water that caused #18/#21.

> Why not "just poll and let the MTE do it"? Because the moment any pymoveit2 sync helper runs, your
> node is evicted from the MTE (the eviction trap above), so no MTE thread is left to complete the
> future. The passive poll then times out forever. Self-spinning is owner-independent — `spin_once`
> drives the node regardless of which executor "owns" it.

## How it showed up in my project
Two episodes of the **same** bug:
- **#18 (2026-06-05):** stage-5 `compute_ik` hung (5 s `future is not done`) — a lazily-created IK
  client orphaned by the executor corruption. Fixed by creating clients eagerly + sync `compute_ik`.
- **#21 (2026-06-08):** every gripper/attach stage cost ~10 s and `Attach result:` was `None`. The
  "fix" from #18 — a *non-spinning* `_wait_for_future` poll — never completed, because the node was
  already evicted from the MTE. Fixed by making `_wait_for_future` **self-spin** (`spin_once`),
  unifying every wait in the callback under one self-spin discipline. The 10 s timeouts vanished;
  `Attach result:` became a real `Response`.

Related: [[ROS2 Actions]] · [[MoveIt2 and Planning Pipelines]] · [[Inverse Kinematics]] ·
[[MoveIt Planning Scene and Collision Objects]] · [[ROS2 Workspaces and Sourcing]] ·
gotchas #16, #18, #21.
