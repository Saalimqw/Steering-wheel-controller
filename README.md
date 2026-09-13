# 🏎️ Steering-Wheel-Controller

### Turn your webcam into a touch-free virtual steering wheel with AI gesture tracking and DirectX input emulation.

[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-orange.svg)](https://developers.google.com/mediapipe)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer%20Vision-green.svg)](https://opencv.org/)
[![DirectInput](https://img.shields.io/badge/Windows-DirectInput-purple.svg)](https://github.com/learncodebygaming/pydirectinput)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

**Steering-Wheel-Controller** turns standard webcam video into low-latency gaming inputs using real-time hand tracking and computer vision heuristics. Designed specifically for PC racing and driving games, it requires no hardware steering wheel, no controllers, and zero setup hassle.

---

## 🧠 How the AI & Vision Pipeline Works

The system converts raw webcam video frames into analog driving physics and keyboard strokes through a multi-stage pipeline:

[Webcam Feed]
│
▼
[MediaPipe BlazePalm] ────────► Detects palms in 2D bounding space
│
▼
[Hand Landmark Subgraph] ─────► Predicts 21 3D landmarks per hand (X, Y, Z)
│
├───► [Landmark 5 Extraction] ──► Angle Estimation + EMA Filter ──► PWM Steer (A / D)
│
└───► [3D Gesture Engine] ──────► Euclidean Distance Checks ──────► Pedals & Cabin (W / S / H / E)


1. **Palm Detection (BlazePalm):** Evaluates entire video frames using an SSD-based detector optimized for low-latency edge inference.
2. **3D Landmark Regression:** Infers **21 distinct 3D landmarks** ($x, y, z$) per hand.
3. **Virtual Steering Geometry:** Anchors to **Landmark 5** (Index Finger MCP joint) on both hands. Real-time steering inclination angle ($\theta$) is derived using the 2D Cartesian arc tangent:
   $$\theta = \operatorname{atan2}(y_2 - y_1, x_2 - x_1)$$
4. **Exponential Moving Average (EMA) Filtering:** Mitigates sensor jitter and hand tremors to produce smooth steering tracking:
   $$\text{Angle}_t = 0.7 \cdot \text{Angle}_{t-1} + 0.3 \cdot \theta$$
5. **3D Rotation-Invariant Gesture Detection:** Distinguishes open vs. folded finger states using 3D Euclidean distances between the wrist (Landmark 0), PIP joints, and fingertips:
   $$\text{dist} = \sqrt{(x - x_0)^2 + (y - y_0)^2 + (z - z_0)^2}$$
   This ensures gesture accuracy regardless of hand angle or tilt toward the lens.

---

## ✨ Key Features

* **Progressive PWM Steering:** Overcomes binary on/off keyboard limits by applying a **100 ms Pulse-Width Modulation (PWM)** duty cycle to `A` and `D` keys, delivering smooth, proportional analog-like steering.
* **Deadzone & Max-Lock Handling:** Features an integrated $\pm 10^\circ$ center deadzone to prevent drift and holds full lock past $\pm 45^\circ$.
* **Natural Gesture Pedals:** Clench a fist to accelerate; open your palm to brake or reverse.
* **Smart Cabin Actions:**
  * **Horn (`H`):** Push an open right palm toward the center of the screen (virtual horn pad).
  * **Dipper / High-Beam Flash (`E`):** Raise your right index finger.
* **Minimalist HUD:** Features an always-on-top compact overlay window (`320x240`) complete with real-time angle gauges, pedal state indicators, and hand tracking visualizers.

---

## 🎮 Control Reference

| Action | Physical Gesture / Position | Emulated Key | Behavior |
| :--- | :--- | :---: | :--- |
| **Steer Left** | Tilt hands counter-clockwise ($<-10^\circ$) | `A` | PWM tapped duty cycle |
| **Steer Right** | Tilt hands clockwise ($>10^\circ$) | `D` | PWM tapped duty cycle |
| **Hard Lock** | Tilt beyond $\pm 45^\circ$ | `A` / `D` | Continuous key hold |
| **Gas / Accelerate** | Closed fist (either hand) | `W` | Continuous key hold |
| **Brake / Reverse** | Flat open palm (either hand) | `S` | Continuous key hold |
| **Horn** | Open right palm in screen center | `H` | Continuous key hold |
| **High-Beam Dipper** | Right index finger pointing up (`INDEX_UP`) | `E` | Continuous key hold |
| **Coast / Neutral** | Relaxed / neutral hand positions | *None* | Keys released |

---

## 📋 System Requirements

* **Operating System:** Windows 10 / 11 *(Required for `pydirectinput` DirectX scan-code emulation)*
* **Python:** `>= 3.11, < 3.12`
* **Package Manager:** [`uv`](https://github.com/astral-sh/uv) (recommended)
* **Camera:** Any standard USB webcam (720p 30 FPS or higher recommended)

---

## 🚀 Quickstart

### 1. Clone the Repository

```bash
git clone [https://github.com/Saalimqw/Steering-wheel-controller.git](https://github.com/Saalimqw/Steering-wheel-controller.git)
cd Steering-wheel-controller
2. Run the Controller
This project includes PEP 723 inline script metadata. Run it instantly using uv:

Bash
uv run main.py
Bash
python -m venv .venv
.venv\Scripts\activate
pip install "mediapipe==0.10.14" opencv-python numpy pydirectinput
python main.py
🕹️ In-Game Setup
Launch your favorite racing title (Forza Horizon, Euro Truck Simulator 2, Assetto Corsa, Need for Speed, City Car Driving).

Configure keyboard bindings to standard layout:

Steer Left: A

Steer Right: D

Throttle: W

Brake / Reverse: S

Horn: H

Headlight Flasher: E

Run uv run main.py.

Position your webcam so your chest and hands are clearly visible in the frame.

Lift both hands to take the wheel.

Press q while focused on the overlay window to close the application and cleanly release all active keys.

🛠️ Code Maintenance Note
In main.py, verify the cleanup function in reset_controls() properly releases the dipper key:

Python
# Ensure line 191 releases 'e' (matching the dipper key binding):
pydirectinput.keyUp('e')
