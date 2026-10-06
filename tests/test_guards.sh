#!/usr/bin/env bash
# Failure paths and safety guards: verify must fail on a broken install, uninstall must refuse a tampered manifest,
# unsupported environments must stop with a clear message, per-distro hints must name the right packages.
set -uo pipefail
# shellcheck source=tests/lib.sh
source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# shellcheck source=tests/fixtures.sh
source "$TESTS_DIR/fixtures.sh"

t_setup
trap t_teardown EXIT
make_fixtures
INSTALL=(bash "$REPO/install.sh" --skip cursor)
VERIFY=(bash "$REPO/verify.sh" --skip cursor)

echo "== environment checks"
out="$(XDG_CURRENT_DESKTOP=KDE "${INSTALL[@]}" --dry-run 2>&1)"; rc=$?
check "non-GNOME session is refused" test "$rc" -ne 0
check "message says it is not GNOME" grep -q 'not a GNOME session' <<<"$out"
out="$(M3E_FAKE_GNOME_VERSION=48.1 "${INSTALL[@]}" --dry-run 2>&1)"; rc=$?
check "another GNOME major only warns" test "$rc" -eq 0
check "warning names the detected major" grep -q 'GNOME Shell 48 detected' <<<"$out"
out="$(XDG_CONFIG_HOME="$HOME/cfg" "${INSTALL[@]}" --dry-run 2>&1)"; rc=$?
check "custom XDG_CONFIG_HOME is refused" test "$rc" -ne 0
check "…with a reason" grep -q 'not supported' <<<"$out"
out="$(HOME="$T_ROOT/with space" "${INSTALL[@]}" --dry-run 2>&1)"; rc=$?
check "a HOME with whitespace is accepted (matugen hooks quote it)" test "$rc" -eq 0
out="$("${INSTALL[@]}" --skip nonsense 2>&1)"; rc=$?
check "unknown step is refused" test "$rc" -ne 0
out="$("${INSTALL[@]}" --bogus 2>&1)"; rc=$?
check "unknown option is refused" test "$rc" -ne 0
out="$(bash "$REPO/install.sh" --no-session-check --dry-run --version 2>&1)"
check "--version prints the version" grep -q '^m3e-gnome ' <<<"$out"
check "nothing was created by the refused runs" test -z "$(ls -A "$HOME")"

echo "== per-distro dependency hints"
# shellcheck source=lib/common.sh
source "$REPO/lib/common.sh"
for f in pins deps; do
    # shellcheck source=/dev/null
    source "$REPO/lib/$f.sh"
done
check "the running python3 satisfies the minimum" check_python_version
out="$(PYTHON_MIN=99.0; check_python_version 2>&1)"; rc=$?
check "a too-old python3 is refused" test "$rc" -ne 0
check "…naming the required version" grep -q 'Python 99.0 or newer is required' <<<"$out"
ASSUME_YES=0
declare -A SELECTED=([gtk-theme]=1 [icons]=1 [cursor]=1 [sounds]=1 [font]=1 [palette]=1 [extensions]=1)
step_enabled() { [[ -n "${SELECTED[$1]:-}" ]]; }
# shellcheck disable=SC2317,SC2329  # called by check_deps
have() { return 1; }
for pair in debian:ubuntu:'apt-get install' fedora:fedora:'dnf install' arch:arch:'pacman -S' suse:opensuse-tumbleweed:'zypper install'; do
    IFS=: read -r fam id want <<<"$pair"
    printf 'ID=%s\n' "$id" >"$T_ROOT/os-release"
    M3E_OS_RELEASE="$T_ROOT/os-release"
    out="$(check_deps 2>&1)"
    check "$fam: family detected" test "$(os_family)" = "$fam"
    check "$fam: prints the $want command" grep -q "$want" <<<"$out"
    check "$fam: names rsvg-convert's package" grep -qE 'librsvg2-bin|librsvg2-tools|librsvg|rsvg-convert' <<<"$out"
done
printf 'ID=linuxmint\nID_LIKE="ubuntu debian"\n' >"$T_ROOT/os-release"
check "ID_LIKE is used (Linux Mint -> debian)" test "$(os_family)" = debian
printf 'ID=nixos\n' >"$T_ROOT/os-release"
out="$(check_deps 2>&1)"
check "unknown distribution falls back to a generic message" grep -q 'unrecognised distribution' <<<"$out"
unset -f have
M3E_OS_RELEASE=''

echo "== --install-deps runs the printed command through sudo, after confirmation"
printf '#!/bin/sh\necho "$@" >> "%s/sudo.log"\n' "$T_ROOT" >"$T_ROOT/realbin/sudo"
chmod +x "$T_ROOT/realbin/sudo"
printf 'ID=debian\n' >"$T_ROOT/os-release"
M3E_OS_RELEASE="$T_ROOT/os-release"
DEPS_PACKAGES=(git rsync)
ASSUME_YES=1
install_deps >/dev/null 2>&1
check "sudo received the apt-get command with -y" grep -qx 'apt-get install --no-install-recommends -y git rsync' "$T_ROOT/sudo.log"
ASSUME_YES=0
rm -f "$T_ROOT/sudo.log"
out="$(install_deps </dev/null 2>&1)"; rc=$?
check "without --yes and without a terminal nothing is run" test "$rc" -ne 0
check_not "…sudo was not called" test -e "$T_ROOT/sudo.log"
M3E_OS_RELEASE=''

echo "== tampering"
"${INSTALL[@]}" >"$T_ROOT/install.out" 2>&1 || { fail "setup install failed"; cat "$T_ROOT/install.out"; }
check "verify passes on a fresh install" "${VERIFY[@]}"
echo '/* changed */' >>"$HOME/.config/m3e-gnome/overrides/m3e-gtk4.css"
check_not "verify fails when an installed file differs from the repo" "${VERIFY[@]}"
bash "$REPO/install.sh" --skip cursor >/dev/null 2>&1
check "reinstall repairs it" "${VERIFY[@]}"
rm -f "$HOME/.themes/M3E-Shell/gnome-shell/gnome-shell.css"
check_not "verify fails when a rendered output is missing" "${VERIFY[@]}"
bash "$REPO/install.sh" --skip cursor >/dev/null 2>&1
fake_set /org/gnome/desktop/interface/icon-theme "'Adwaita'"
check_not "verify fails on a wrong gsettings value" "${VERIFY[@]}"
bash "$REPO/install.sh" --skip cursor >/dev/null 2>&1
rm -f "$M3E_FAKE_DIR/services.json"
check_not "verify fails when the service is not active" "${VERIFY[@]}"
check "…unless --no-service" bash "$REPO/verify.sh" --skip cursor --no-service

echo "== uninstall guards"
cp "$HOME/.local/share/m3e-gnome/manifest" "$T_ROOT/manifest.ok"
victim="$T_ROOT/outside-home.txt"; echo keep >"$victim"
printf 'F\t%s\n' "$victim" >>"$HOME/.local/share/m3e-gnome/manifest"
out="$(bash "$REPO/uninstall.sh" --yes 2>&1)"; rc=$?
check "uninstall refuses a manifest path outside HOME" test "$rc" -ne 0
check "…and removes nothing outside HOME" test -f "$victim"
printf 'T\t%s/../../etc\n' "$HOME" >"$HOME/.local/share/m3e-gnome/manifest"
out="$(bash "$REPO/uninstall.sh" --yes 2>&1)"; rc=$?
check "uninstall refuses a path with .." test "$rc" -ne 0
printf 'T\t%s\n' "$HOME" >"$HOME/.local/share/m3e-gnome/manifest"
out="$(bash "$REPO/uninstall.sh" --yes 2>&1)"; rc=$?
check "uninstall refuses HOME itself" test "$rc" -ne 0
check "HOME still exists" test -d "$HOME/.config"
cp "$T_ROOT/manifest.ok" "$HOME/.local/share/m3e-gnome/manifest"
out="$(bash "$REPO/uninstall.sh" --yes 2>&1)"; rc=$?
check "uninstall works with the good manifest" test "$rc" -eq 0
check "a fresh HOME is empty again after uninstall" test -z "$(ls -A "$HOME")"
check "uninstall without install is a no-op" bash "$REPO/uninstall.sh" --yes

echo "== User Themes extension missing"
grep -vx org.gnome.shell.extensions.user-theme "$M3E_FAKE_DIR/schemas.txt" >"$T_ROOT/schemas.new" && mv "$T_ROOT/schemas.new" "$M3E_FAKE_DIR/schemas.txt"
out="$("${INSTALL[@]}" 2>&1)"; rc=$?
check "install still succeeds" test "$rc" -eq 0
check "it explains how to install User Themes" grep -q "User Themes' extension is not installed" <<<"$out"
check_not "verify reports it as a failure" "${VERIFY[@]}"
bash "$REPO/uninstall.sh" --yes >/dev/null 2>&1

echo "== system-wide extensions (gnome-shell-extension-m3e package)"
echo org.gnome.shell.extensions.user-theme >>"$M3E_FAKE_DIR/schemas.txt"   # undo the previous section
sysext="$T_ROOT/sysext"
for u in m3e-motion m3e-extensions status-bar; do
    mkdir -p "$sysext/$u@maximeallanic.github.io"
    printf '{"uuid": "%s@maximeallanic.github.io"}\n' "$u" >"$sysext/$u@maximeallanic.github.io/metadata.json"
    printf '// %s\n' "$u" >"$sysext/$u@maximeallanic.github.io/extension.js"
done
# The pinned extensions repository is made unreachable: a clone attempt would fail the install.
{ cat "$M3E_PINS_FILE"; echo 'EXT_URL=file:///nonexistent/m3e-gnome-extensions'; } >"$T_ROOT/pins-noext.sh"
snapshot "$HOME" >"$T_ROOT/sys-before.snap"
out="$(M3E_SYSTEM_EXT_DIRS="$sysext" M3E_PINS_FILE="$T_ROOT/pins-noext.sh" "${INSTALL[@]}" 2>&1)"; rc=$?
check "install succeeds without fetching the extensions repository" test "$rc" -eq 0
check "it says it uses the system-wide extensions" grep -q 'using the system-wide extensions' <<<"$out"
check_not "no extension was copied into the user directory" test -e "$HOME/.local/share/gnome-shell/extensions/status-bar@maximeallanic.github.io"
for u in m3e-motion m3e-extensions status-bar; do
    check "$u is enabled" grep -q "$u@maximeallanic.github.io" "$M3E_FAKE_DIR/dconf.json"
done
check "verify accepts the system-wide extensions" env M3E_SYSTEM_EXT_DIRS="$sysext" "${VERIFY[@]}"
check_not "verify still fails when they are neither installed for the user nor system-wide" "${VERIFY[@]}"
out="$(M3E_SYSTEM_EXT_DIRS="$sysext" "${INSTALL[@]}" --extensions-dir "$T_ROOT/fix/extensions" 2>&1)"; rc=$?
check "--extensions-dir wins over the system-wide copies" test "$rc" -eq 0
check "…and installs them for the user" test -f "$HOME/.local/share/gnome-shell/extensions/status-bar@maximeallanic.github.io/extension.js"
bash "$REPO/uninstall.sh" --yes >/dev/null 2>&1
snapshot "$HOME" >"$T_ROOT/sys-after.snap"
check "uninstall leaves HOME as it was" cmp -s "$T_ROOT/sys-before.snap" "$T_ROOT/sys-after.snap"

echo
if ((FAILS)); then echo "guards: $FAILS failure(s)"; exit 1; fi
echo "guards: all checks passed"
