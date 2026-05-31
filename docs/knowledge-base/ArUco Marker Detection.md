---
tags: [perception, opencv, computer-vision, aruco]
---

# ArUco Marker Detection

## What it is
ArUco markers are square black-and-white **fiducial markers** — each encodes a binary ID in an inner
grid. OpenCV's `cv2.aruco` detects them in an image and (with camera calibration) estimates their
6-DOF pose. They're a fast, reliable stand-in for full markerless object detection — a prototype
perception front-end.

## Why it exists (in this project)
The pick-and-place pipeline needs an object **pose** to plan toward. ArUco gives an unambiguous,
easy-to-detect target while the harder markerless detection stays on the backlog.

## How detection works — two stages
`cv2.aruco.detectMarkers(gray, dictionary, parameters=...)` returns `corners, ids, rejected`:
1. **Candidate detection** — find quad-shaped contours (4 corners, right size). Pure shape analysis.
2. **Identification (decode)** — warp each candidate flat, threshold it into a bit grid, and check it
   against the **dictionary** of valid codewords.

The three return values split by which stage they pass:
- **`ids` / `corners`** → passed both: a valid quad that decoded to a real marker ID.
- **`rejected`** → passed shape but **failed decode**: marker-*shaped* things (box edges, shadows)
  whose interior wasn't a valid code. Correctly discarded — **not an error**.

> So a log of `Detected: none, Rejected: 2` means "2 things looked marker-shaped but weren't valid
> codes." Only `Detected` matters.

## Pose estimation
`estimatePoseSingleMarkers(corners, marker_size, camera_matrix, dist_coeffs)` returns rotation
(`rvec`, a Rodrigues vector → rotation matrix → quaternion) and translation (`tvec`) of the marker in
the **camera frame**. That pose is then transformed into `base_link` (via [[ROS2 Introspection and Debugging Tools|TF2]])
for the planner.

## Gotchas
- The OpenCV ArUco API changed across versions — on 4.5.4 use `drawMarker` (not
  `generateImageMarker`) and pass `parameters=` as a keyword.
- A wrong **camera-pointing-down** quaternion is `x=1.0, w=0.0` (180° about X); the plausible-looking
  `[0,0.707,0,0.707]` points the camera sideways and silently corrupts every pose.

## Related
[[ROS2 Introspection and Debugging Tools]] (`rqt_image_view`, TF) · [[ROS2 Actions]] (the pose feeds the RunTask goal) · back to [[ROS Knowledge Base]]
