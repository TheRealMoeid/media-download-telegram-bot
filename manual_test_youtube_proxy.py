"""
manual_test_youtube_proxy.py

Throwaway diagnostic script for Issue #5 - NOT part of the pytest suite,
and intentionally hits the real network. Purpose: isolate whether
YouTube's anonymous "Sign in to confirm you're not a bot" rejection is
proxy/IP-related, independent of the bot/handlers/config stack.

Does NOT import any project code (config/settings.py, downloader/*), so
it has no BOT_TOKEN or other config dependency - it runs completely
standalone against yt-dlp directly.

Usage:
    1. Edit VIDEO_URL below - ideally to a URL that has already failed
       for you before (reusing one of the original 5 test videos would
       be ideal for a clean comparison, but any real public video works).

    2. Run #1 - baseline, with your normal VLESS proxy active:
           python manual_test_youtube_proxy.py

    3. Run #2 - same command, but forcing a direct (no-proxy) connection:
           python manual_test_youtube_proxy.py --direct

       IMPORTANT: unsetting $env:HTTP_PROXY / $env:HTTPS_PROXY is NOT
       enough on Windows - yt-dlp's urllib backend falls back to the
       Windows system-level proxy setting (registry-based) when the env
       vars are empty, so a VLESS client that configures the system
       proxy directly (rather than just env vars) stays active even
       with the env vars unset. This --direct flag instead passes
       proxy="" straight to yt-dlp, which yt-dlp documents as forcing a
       genuine direct connection, bypassing both env vars and the
       system setting.

    4. Compare the two outputs and paste both back. Check the "Proxy
       map" debug line in each - it should show the real proxy in run
       #1 and be empty/absent in run #2. If it's *not* empty in the
       --direct run too, something is intercepting the connection at a
       lower level (e.g. a TUN-mode VLESS client capturing all traffic
       regardless of application-level settings) and the phone-hotspot
       approach is the only way to get a clean comparison.

Note: if run #2 fails to even reach YouTube (a connection-level error,
not a bot-check rejection), that means the proxy is required just to
reach YouTube at all in this environment - in that case, use a phone
hotspot for that run instead, for a cleaner comparison.
"""

import argparse
import os

import yt_dlp

VIDEO_URL = "https://youtu.be/n3XTZde8ZvQ"  # <-- replace with a URL that has failed for you before, if you have one handy

# Same client list + order as downloader/youtube.py's fallback chain,
# plus a leading "no explicit client" attempt (yt-dlp's own default),
# mirroring get_available_qualities()'s real attempt order.
CLIENTS_TO_TRY = [None, "android", "ios", "tv"]


def attempt(client: str | None, direct: bool) -> None:
    label = client or "(yt-dlp default)"
    print(f"\n=== Attempting client: {label} ===")

    ydl_opts = {
        "quiet": False,
        "verbose": True,
        "skip_download": True,  # extraction only - we're testing whether YouTube serves formats at all, not downloading
        "noplaylist": True,
    }
    if direct:
        # yt-dlp treats an explicit empty string as "force a direct
        # connection" - this overrides both HTTP_PROXY/HTTPS_PROXY env
        # vars and the Windows system-level proxy setting, unlike
        # merely leaving the proxy option unset.
        ydl_opts["proxy"] = ""
    if client is not None:
        ydl_opts["extractor_args"] = {"youtube": {"player_client": [client]}}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(VIDEO_URL, download=False)
            formats = info.get("formats", [])
            print(f"RESULT: SUCCESS - client={label} - {len(formats)} formats returned")
    except Exception as exc:
        print(f"RESULT: FAILED - client={label} - {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Force yt-dlp to bypass any proxy (env var AND Windows system setting) via proxy=''.",
    )
    args = parser.parse_args()

    env_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or "(none set)"
    print(f"HTTP(S)_PROXY env var for this run: {env_proxy}")
    print(f"Mode: {'--direct (forcing proxy=\"\")' if args.direct else 'default (system/env proxy resolution, whatever that is)'}")
    print(f"Testing URL: {VIDEO_URL}")
    print("Check the 'Proxy map' line in each attempt's debug output below to confirm which mode actually took effect.")

    for client in CLIENTS_TO_TRY:
        attempt(client, args.direct)

    print("\n=== Done. Paste this entire output back for comparison. ===")