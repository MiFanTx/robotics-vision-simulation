---
tags: [ros2, debugging, cli, tools]
---

# ROS2 Introspection and Debugging Tools

The CLI/GUI tools for seeing what's actually running — the heart of Socratic debugging: *check, don't
guess.* When something fails, these answer "is the node alive? is the topic publishing? is the data
right?"

## Nodes
```bash
ros2 node list                 # what nodes are running
ros2 node info /node_name      # its topics, services, actions (pubs/subs)
```

## Topics
```bash
ros2 topic list                # all topics
ros2 topic list | grep image   # filter
ros2 topic echo /vision/object_pose   # print the messages
ros2 topic hz /camera/image_raw       # publish rate — is it actually flowing?
ros2 topic info /topic -v             # types + publisher/subscriber counts
```

## Parameters (e.g. what a planner loaded)
```bash
ros2 param list /move_group
ros2 param get /move_group planning_pipelines
```

## Seeing images
```bash
ros2 run rqt_image_view rqt_image_view   # pick the topic in the dropdown
```
Used to confirm the camera actually sees the box + marker before blaming the
[[ArUco Marker Detection|detector]].

## TF (coordinate frames)
- Prefer the **single-call** transform API: `tf_buffer.transform(msg, 'base_link')` over manual
  `lookup_transform` + `do_transform_*` — fewer frame/timestamp mismatches.
- Inspect frames visually in RViz's TF display.

## Debugging mindset
1. What's the **exact** error / log line?
2. Which node/topic does it point at?
3. Confirm with an introspection command (don't assume).
4. Narrow to the smallest failing step.

A silent **hang** vs a **crash with traceback** point to very different causes — note which you see.

## Related
[[ROS2 Workspaces and Sourcing]] · [[ROS2 Actions]] · [[ArUco Marker Detection]] · back to [[ROS Knowledge Base]]
