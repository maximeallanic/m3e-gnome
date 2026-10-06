#!/usr/bin/env python3
"""Private audio server for the screenshot session: PipeWire + pipewire-pulse with one fake output (a null sink).

The nested Shell reaches the sound server of the host (nested.sh keeps PIPEWIRE_RUNTIME_DIR and PULSE_RUNTIME_PATH),
so the quick settings volume slider would show the real state (device, level, mute). PULSE_SERVER, which libpulse reads
before anything else, points the Shell at this server instead.

Usage: audio.py --dir DIR      (runs until SIGTERM/SIGINT; writes DIR/address once the server is up)
"""
import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

CONFIG = """context.objects = [
  # WirePlumber normally owns this object; without it pipewire-pulse has no default output.
  { factory = metadata
    args = {
      metadata.name = default
      metadata.values = [
        { key = default.audio.sink value = { name = demo_sink } }
        { key = default.configured.audio.sink value = { name = demo_sink } }
      ]
    }
  }
  { factory = adapter
    args = {
      factory.name = support.null-audio-sink
      node.name = demo_sink
      node.description = "Built-in Audio"
      media.class = Audio/Sink
      audio.position = [ FL FR ]
      object.linger = true
    }
  }
]
"""
CHANNEL_VOLUME = "0.25"      # cubic scale: about 62 % on the slider


def wait_for(predicate, what, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        value = predicate()
        if value:
            return value
        time.sleep(0.1)
    sys.exit(f"audio: {what} did not start")


def sink_id(env):
    dump = subprocess.run(["pw-dump"], env=env, capture_output=True, text=True).stdout
    for obj in json.loads(dump or "[]"):
        if obj.get("info", {}).get("props", {}).get("node.name") == "demo_sink":
            return obj["id"]
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--dir", required=True)
    work = Path(p.parse_args().dir).resolve()
    runtime = work / "rt"
    config = work / "config" / "pipewire" / "pipewire.conf.d"
    config.mkdir(parents=True, exist_ok=True)
    runtime.mkdir(mode=0o700, exist_ok=True)
    (config / "10-demo-sink.conf").write_text(CONFIG, encoding="utf-8")
    env = {**os.environ, "PIPEWIRE_RUNTIME_DIR": str(runtime), "XDG_RUNTIME_DIR": str(runtime),
           "XDG_CONFIG_HOME": str(work / "config"), "HOME": str(work)}
    env.pop("PULSE_SERVER", None)
    procs = [subprocess.Popen(["pipewire"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)]
    stop = []
    for s in (signal.SIGTERM, signal.SIGINT):
        signal.signal(s, lambda *_: stop.append(1))
    try:
        wait_for(lambda: (runtime / "pipewire-0").exists(), "pipewire")
        procs.append(subprocess.Popen(["pipewire-pulse"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT))
        node = wait_for(lambda: sink_id(env), "the demo sink")
        subprocess.run(["pw-cli", "set-param", str(node), "Props",
                        f"{{ channelVolumes: [{CHANNEL_VOLUME}, {CHANNEL_VOLUME}], mute: false }}"],
                       env=env, check=True, capture_output=True)
        pulse = runtime / "pulse" / "native"
        wait_for(pulse.exists, "pipewire-pulse")
        (work / "address").write_text(f"unix:{pulse}", encoding="utf-8")
        while not stop and all(q.poll() is None for q in procs):
            time.sleep(0.2)
    finally:
        for q in reversed(procs):
            q.terminate()
        for q in procs:
            q.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
