# MindsOS Robot Demo — how to run & share (v0.10)

The dashboard is one web page, `presentation_v10.html`. It runs in two modes:

- **Demo mode (default)** — a scripted run that plays a fixed 7-beat story. Works anywhere,
  offline, no setup. This is what you show when there are no live brains.
- **Live mode** — the same dashboard connected to running brains over a network, so the panels
  reflect what the brains are actually doing. Turned on by adding `?live=…` to the address.

> The little tag in the top bar tells you which you're in: **"mock data · not wired to live
> brains"** (Demo) vs **"● live — connected to brains"** (Live).

---

## 1. Run it yourself — Demo mode (no setup)

Double-click **`presentation_v10.html`** (or open it in Chrome/Edge). That's it — it works
offline. Use the top-bar buttons: **▶ Play** runs the story, **‹ ›** step, **↺** reset.

> Keep the whole `demo_ui` folder together — the page needs the files next to it
> (`graph_v10.js`, `teach_v10.js`, `sections_v10.js`, `resolve_v10.js`, `datasource_v10.js`,
> and `vendor/three.min.js`). Moving the single HTML out on its own will break the 3D view.

---

## 2. Run it Live

Live mode needs something for the page to connect to. Until the real backend is ready, there's a
**practice server** that streams the same story as if it were live:

1. Open a terminal in the `demo_ui` folder.
2. First time only: `npm install ws`
3. Start it: `node mock_ws_server.js 8765`
   (you'll see `mock brains WS listening on ws://localhost:8765`)
4. Open the page pointing at it:
   **`presentation_v10.html?live=ws://localhost:8765`**
5. The tag turns green (**● live — connected to brains**). Click **▶ Play** or **Submit** an
   order — the beats now arrive as live frames.

When the real backend exists, nothing about the page changes — you just point `?live=` at the
real server's address instead of the practice one.

---

## 3. Share it with someone else

### A. Share Demo mode (easiest — works offline)
Zip the **entire `demo_ui` folder** and send it. The other person unzips it and double-clicks
`presentation_v10.html`. No internet, no server, nothing to install. Best for "have a look at the
interface."

### B. Share Live mode on the same network (same office / Wi-Fi)
The other person's browser has to be able to reach your live server.

1. Start the server (step 2 above). Find your machine's local IP (e.g. `192.168.1.50`).
2. Serve the folder so others can open the page (in `demo_ui`): `python3 -m http.server 8000`
3. Send them this one link:
   `http://192.168.1.50:8000/presentation_v10.html?live=ws://192.168.1.50:8765`
4. They open it and see the live run. (If it won't connect, it's almost always a **firewall**
   blocking ports 8000/8765 — allow them, or see C.)

### C. Share Live mode over the internet (remote viewer / video call) — with cloudflared

A tunnel makes your local servers reachable from anywhere through public secure addresses, with
no warning page (unlike some alternatives) and full WebSocket support. You expose two things — the
**page** and the **brains socket** — each on its own hostname. The viewer just opens one link.

> **Reference setup (this project):** page → `https://demo.sanmyaku.com`, brains →
> `wss://brains.sanmyaku.com`, so the link to share is
> **`https://demo.sanmyaku.com/presentation_v10.html?live=wss://brains.sanmyaku.com`**.
> Substitute your own hostnames below.

#### C-1. Named tunnel — stable hostnames (recommended; needs a domain on Cloudflare)

This is the durable setup: the hostnames don't change between sessions. It requires a domain whose
DNS is managed in your Cloudflare account.

**One-time setup**
1. Install: `brew install cloudflared`
2. Log in and **authorize your domain** (this writes `~/.cloudflared/cert.pem` — if no cert
   appears, you didn't pick a domain, or the account has none):
   ```
   cloudflared tunnel login
   ls -l ~/.cloudflared/cert.pem        # confirm it exists
   ```
3. Create the tunnel (note the printed **Tunnel ID** + credentials json):
   ```
   cloudflared tunnel create mindsos-demo
   ```
4. Point two hostnames at it (use your own domain):
   ```
   cloudflared tunnel route dns mindsos-demo demo.sanmyaku.com
   cloudflared tunnel route dns mindsos-demo brains.sanmyaku.com
   ```
5. Write `~/.cloudflared/config.yml` (one tunnel serves both):
   ```yaml
   tunnel: mindsos-demo
   credentials-file: /Users/YOURNAME/.cloudflared/<TUNNEL-ID>.json
   ingress:
     - hostname: brains.sanmyaku.com
       service: http://localhost:8765      # the WS brains server
     - hostname: demo.sanmyaku.com
       service: http://localhost:8000      # the page
     - service: http_status:404
   ```

**Each time you present** (three terminals, from `demo_ui`)
```
node mock_ws_server.js 8765        # 1 — brains server (real backend later)
python3 -m http.server 8000        # 2 — page server
cloudflared tunnel run mindsos-demo # 3 — the tunnel (serves both hostnames)
```
Then share the single stable link:
```
https://demo.sanmyaku.com/presentation_v10.html?live=wss://brains.sanmyaku.com
```
Page from `demo.…`, socket from `brains.…` (note **`wss://`**). The viewer's status tag goes green.

#### C-2. Quick tunnel — no domain, no account (one-off, random hostnames)

If you don't have a domain on Cloudflare, use throwaway tunnels (no login, no cert). Four terminals:
```
cd demo_ui && node mock_ws_server.js 8765
cloudflared tunnel --url http://localhost:8765     # → https://AAAA.trycloudflare.com  (socket)
cd demo_ui && python3 -m http.server 8000
cloudflared tunnel --url http://localhost:8000     # → https://BBBB.trycloudflare.com  (page)
```
Share: `https://BBBB.trycloudflare.com/presentation_v10.html?live=wss://AAAA.trycloudflare.com`
(page = BBBB, socket = AAAA with `wss://`). These hostnames change every restart — re-send the link.

> Always use **`wss://`** (secure) for the `?live=` part on a public link — a hosted https page
> refuses a plain `ws://`. And keep the brains server running the whole time, or the tag shows
> "disconnected."

---

## 4. Controls at a glance

| Where | Control | Does |
|---|---|---|
| Top bar | ▶ Play / ‹ › / ↺ | run / step / reset the run |
| User card | **Submit** | send the composed order (Live: to the brains) |
| User card | Order / Sort / **Teach** | place a task, or teach a new term/skill |
| Any brain card | **Task · Plan · Pipeline · Capabilities** | switch what that brain shows |
| Any brain card | panel / graph icons | table view vs reasoning-graph view |
| Any card | **⌃⌄ maximize** (header) | grow the card to full screen height; Esc restores |
| Physical cell | **2D / 3D** | top-down schematic vs 3D view |

---

## 5. If something looks off

- **An amber bar appears** ("2D fallback" / "older browser") — the page detected a limitation and
  switched to a safe display. Nothing is broken; for the best look use a current Chrome/Edge on a
  machine with normal graphics. **Tip:** always open the page once on the actual presentation
  computer beforehand to confirm no bar appears.
- **Live tag says "disconnected" or "connection error"** — the server isn't running or isn't
  reachable. Check the server is started, the address/port in the link is right, and firewalls
  allow it.
- **3D view is missing** — that machine can't do 3D (common over screen-share); the 2D view shows
  the same scene and is fine to present.

---

## 6. Honesty note for presenting

In Demo mode, be upfront that it's the **planned interface over a scripted story** — the reasoning
shown is choreographed, not computed live. In Live mode it's real brain activity, but two panels
(the reasoning **graph** and **Plan ▸ Resolve**) stay blank with a "feed not yet emitted" note
until the backend produces that data. See `confirmation_docs/ROBOT_DEMO_WS_CONTRACT.md` for the
technical details.
