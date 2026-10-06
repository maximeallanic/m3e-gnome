## Tested on

- Debian (testing) with GNOME Shell 50.5, on the author's machine, plus installer round trips in a temporary home with
  fake GNOME tools and nested headless Shells. Nothing else has been tried: other distributions, GNOME versions, X11
  and non-x86_64 machines are untested. The GDM login-screen step was verified in a fake root and a nested Shell only.
- The `.deb` was verified by unpacking it and running the installer from the unpacked, read-only tree, not by
  installing it with `dpkg` on a live system.

## Install

- Debian/Ubuntu: `sudo apt install ./m3e-gnome_VERSION_all.deb`, then, as your own user in your GNOME session,
  `m3e-gnome-install`. The package changes nothing in your home directory; the installer downloads pinned sources
  (themes, icons, font) when you run it, so it needs network access.
- Any distribution: unpack `m3e-gnome-VERSION.tar.gz`, then `./install.sh --dry-run` and `./install.sh`.

## Verify the download

```sh
sha256sum -c SHA256SUMS
gh attestation verify <file> --repo maximeallanic/m3e-gnome
```
